# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.3 branch-delta tests: all fixtures fictitious, no real external remote."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

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
        git(self.repo, "reset", "--hard", self.initial)
        (self.repo / SOURCE).write_text("Branche alternative B\n")
        self.commit("branche B")
        b = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", REF, b)
        divergent = self.observe(a)
        self.assertEqual(divergent["relation"], "DIVERGED")
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
