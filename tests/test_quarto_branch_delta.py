# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.3 branch-delta tests: all fixtures fictitious, no real external remote."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quarto_branch_delta import DeltaError, compare

REF = "refs/remotes/origin/experiment/historique-quarto"
SOURCE = "activite.qmd"


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], stderr=subprocess.PIPE, text=True
    ).strip()


class BranchDeltaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "clone"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        (self.repo / SOURCE).write_text(
            "---\ntitle: Fictif\n---\n\n## Consigne\nVersion initiale.\n",
            encoding="utf-8",
        )
        (self.repo / "styles.css").write_text("h2 {color: blue;}\n", encoding="utf-8")
        self.commit("révision initiale")
        self.initial = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", REF, self.initial)

    def commit(self, message):
        git(self.repo, "add", "-A")
        git(self.repo, "-c", "user.name=Fiction",
            "-c", "user.email=fiction@example.test", "commit", "-qm", message)

    def observe(self, baseline=None, ref=REF, source=SOURCE):
        return compare(self.repo, "fiction/laboratoire", source,
                       ref, baseline or self.initial)

    def test_no_network_implicit_and_css_only_commit_detected(self):
        baseline = self.observe()
        self.assertEqual(baseline["relation"], "UNCHANGED")
        self.assertFalse(baseline["new_commit_observed"])
        self.assertFalse(baseline["project_tree_changed"])
        (self.repo / "styles.css").write_text("h2 {color: red;}\n", encoding="utf-8")
        self.commit("nouveau CSS sans modifier le QMD")
        second = git(self.repo, "rev-parse", "HEAD")
        # HEAD moves, but the explicitly named remote-tracking ref does not.
        old = self.observe()
        self.assertEqual(old["observed_commit"], self.initial)
        self.assertFalse(old["new_commit_observed"])
        git(self.repo, "update-ref", REF, second)  # simulates an explicit fetch
        current = self.observe()
        self.assertEqual(current["relation"], "FAST_FORWARD")
        self.assertEqual(current["observed_commit"], second)
        self.assertTrue(current["project_tree_changed"])
        self.assertFalse(current["source_blob_changed"])
        self.assertEqual(current["baseline"]["git_blob"], current["observed"]["git_blob"])
        self.assertEqual(current["baseline"]["sha256"], current["observed"]["sha256"])
        self.assertFalse(current["remote_freshness_verified"])
        self.assertFalse(current["fetch_performed_by_alliage"])
        self.assertFalse(current["deployment_verified"])
        self.assertEqual(current["publication_status"], "NOT_VERIFIED")
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), second)

    def test_modified_qmd_detected_without_touching_dirty_worktree(self):
        (self.repo / SOURCE).write_text("---\ntitle: Démo\n---\nTexte changé\n")
        self.commit("révision texte")
        second = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", REF, second)
        # A dirty local workspace must not masquerade as a commit.
        (self.repo / SOURCE).write_text("DIRTY NON COMMITÉ")
        result = self.observe()
        self.assertTrue(result["new_commit_observed"])
        self.assertTrue(result["source_blob_changed"])
        self.assertEqual(result["relation"], "FAST_FORWARD")
        self.assertNotEqual(result["observed"]["sha256"],
                            hashlib.sha256((self.repo / SOURCE).read_bytes()).hexdigest())
        self.assertEqual((self.repo / SOURCE).read_text(), "DIRTY NON COMMITÉ")

    def test_rewinds_and_divergences_are_not_called_fast_forward(self):
        (self.repo / SOURCE).write_text("Avancement sur branche A\n")
        self.commit("branche A")
        a = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", REF, self.initial)
        rewound = self.observe(a)
        self.assertEqual(rewound["relation"], "REWOUND")
        self.assertTrue(rewound["ref_changed"])
        git(self.repo, "reset", "--hard", self.initial)
        (self.repo / SOURCE).write_text("Branche alternative B\n")
        self.commit("branche B")
        b = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", REF, b)
        divergent = self.observe(a)
        self.assertEqual(divergent["relation"], "DIVERGED")
        self.assertTrue(divergent["ref_changed"])
        self.assertNotEqual(divergent["observed_commit"], a)

    def test_fail_closed_on_nonexistent_refs_sha_and_sources(self):
        for ref in ("HEAD", "main", "refs/heads/experiment/historique-quarto",
                    "refs/remotes/origin/main", "refs/remotes/origin/experiment/../bad",
                    "refs/remotes/origin/experiment/a//b", "refs/tags/demo"):
            with self.subTest(ref=ref), self.assertRaises(DeltaError):
                self.observe(ref=ref)
        for bad_sha in ("main", "0" * 40, self.initial[:9], self.initial.upper()):
            with self.subTest(sha=bad_sha), self.assertRaises(DeltaError):
                self.observe(baseline=bad_sha)
        for source in ("../private.qmd", "activite.html", "./activite.qmd",
                       "ressources//activite.qmd"):
            with self.subTest(source=source), self.assertRaises(DeltaError):
                self.observe(source=source)

    def test_git_replace_objects_cannot_falsify_commits(self):
        (self.repo / SOURCE).write_text("Autre texte")
        self.commit("second")
        newer = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "replace", self.initial, newer)
        report = self.observe()
        self.assertEqual(report["observed_commit"], self.initial)
        self.assertEqual(report["baseline_commit"], self.initial)
        self.assertFalse(report["source_blob_changed"])

    def _bare_fixture(self):
        """A file:// Git server, entirely within a disposable temp directory."""
        remote = self.root / "remote-for-security.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        git(self.repo, "remote", "add", "origin", str(remote))
        git(self.repo, "push", "origin", "HEAD:refs/heads/experiment/historique-quarto")
        git(remote, "symbolic-ref", "HEAD", "refs/heads/experiment/historique-quarto")
        return remote

    def test_partial_clone_refuses_missing_blob_without_lazy_fetch(self):
        remote = self._bare_fixture()
        # A genuine filtered clone: the commit and tree exist but the QMD
        # blob is absent. file:// is needed for --filter to take effect.
        git(remote, "config", "uploadpack.allowFilter", "true")
        partial = self.root / "partial"
        subprocess.run(
            ["git", "clone", "-q", "--filter=blob:none", "--no-checkout",
             remote.as_uri(), str(partial)],
            check=True, capture_output=True,
        )
        sha = git(partial, "rev-parse", REF)
        self.assertEqual(sha, self.initial)
        blob = git(partial, "rev-parse", self.initial + ":" + SOURCE)
        env = os.environ.copy()
        env["GIT_NO_LAZY_FETCH"] = "1"
        absent = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(partial),
             "cat-file", "-e", blob],
            capture_output=True, env=env,
        )
        self.assertNotEqual(absent.returncode, 0, "Fixture must omit the source blob")
        before = git(partial, "count-objects", "-v")
        trace = self.root / "trace-no-network.json"
        # Even an inherited explicitly permissive setting must be overridden
        # by the shared P3.0 and P3.3 Git helpers.
        with patch.dict(os.environ, {"GIT_NO_LAZY_FETCH": "0",
                                     "GIT_TRACE2_EVENT": str(trace)}):
            with self.assertRaisesRegex(DeltaError, "Git|objet|inspection"):
                compare(partial, "fiction/laboratoire", SOURCE, REF, self.initial)
        self.assertEqual(git(partial, "count-objects", "-v"), before)
        self.assertNotEqual(subprocess.run(
            ["git", "-C", str(partial), "cat-file", "-e", blob],
            capture_output=True, env=env,
        ).returncode, 0, "Missing object must stay missing after observation")
        events = [json.loads(line) for line in trace.read_text().splitlines()]
        children = [e for e in events if e.get("event") == "child_start"]
        self.assertEqual(children, [], "No child Git process may contact the remote")

    def test_local_grafts_are_refused_even_with_no_replace_objects(self):
        (self.repo / SOURCE).write_text("Chemin A\n")
        self.commit("fictitious A")
        a = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "reset", "--hard", self.initial)
        (self.repo / SOURCE).write_text("Chemin B\n")
        self.commit("fictitious B")
        b = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", REF, b)
        self.assertEqual(self.observe(a)["relation"], "DIVERGED")
        grafts = Path(git(self.repo, "rev-parse", "--path-format=absolute",
                          "--git-path", "info/grafts"))
        # Forge B's first parent as A without changing either commit SHA.
        grafts.write_text(f"{b} {a}\n", encoding="ascii")
        faked = subprocess.run(["git", "--no-replace-objects", "-C", str(self.repo),
                                "merge-base", "--is-ancestor", a, b],
                               capture_output=True)
        self.assertEqual(faked.returncode, 0, "Fixture must actually forge ancestry")
        with self.assertRaisesRegex(DeltaError, "Greffes Git"):
            self.observe(a)
        # A linked worktree has a .git FILE and must consult the common
        # info/grafts, not its own administrative worktree directory.
        wt = self.root / "linked-worktree"
        git(self.repo, "worktree", "add", "--detach", str(wt), b)
        with self.assertRaisesRegex(DeltaError, "Greffes Git"):
            compare(wt, "fiction/laboratoire", SOURCE, REF, a)

    def test_shallow_clone_is_refused_instead_of_claiming_divergence(self):
        remote = self._bare_fixture()
        shallow = self.root / "shallow"
        subprocess.run(
            ["git", "clone", "-q", "--depth=1", "--no-checkout",
             remote.as_uri(), str(shallow)],
            check=True, capture_output=True,
        )
        self.assertEqual(git(shallow, "rev-parse", "--is-shallow-repository"), "true")
        with self.assertRaisesRegex(DeltaError, "superficiel"):
            compare(shallow, "fiction/laboratoire", SOURCE, REF, self.initial)

    def test_explicit_local_fetch_required_to_advance_observation(self):
        # A real local bare remote and two separate clones: only the test
        # commands fetch; the comparison module never contacts the remote.
        remote = self.root / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        git(self.repo, "remote", "add", "origin", str(remote))
        git(self.repo, "push", "origin", "HEAD:refs/heads/experiment/historique-quarto")
        observer = self.root / "observer"
        subprocess.run(["git", "clone", "-q", "--no-checkout", str(remote), str(observer)],
                       check=True, capture_output=True)
        git(observer, "fetch", "origin",
            "refs/heads/experiment/historique-quarto:" + REF)
        before = compare(observer, "fiction/laboratoire", SOURCE, REF, self.initial)
        self.assertEqual(before["relation"], "UNCHANGED")

        (self.repo / "styles.css").write_text("h2 {color: red;}\n", encoding="utf-8")
        self.commit("mise à jour distante CSS")
        newest = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "push", "origin", "HEAD:refs/heads/experiment/historique-quarto")
        stale = compare(observer, "fiction/laboratoire", SOURCE, REF, self.initial)
        self.assertEqual(stale["observed_commit"], self.initial)
        self.assertFalse(stale["new_commit_observed"])
        git(observer, "fetch", "origin",
            "refs/heads/experiment/historique-quarto:" + REF)
        updated = compare(observer, "fiction/laboratoire", SOURCE, REF, self.initial)
        self.assertEqual(updated["observed_commit"], newest)
        self.assertEqual(updated["relation"], "FAST_FORWARD")
        self.assertTrue(updated["project_tree_changed"])
        self.assertFalse(updated["source_blob_changed"])


if __name__ == "__main__":
    unittest.main()
