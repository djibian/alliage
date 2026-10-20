# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quarto_versions import inspect, VersionError


SOURCE = "cours/activite.qmd"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE).decode().strip()


class QuartoVersionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        path = self.repo / SOURCE
        path.parent.mkdir()
        path.write_text("---\ntitle: Démo\n---\nV1\n", encoding="utf-8")
        git(self.repo, "add", ".")
        self.commit("première rédaction")
        self.v1 = git(self.repo, "rev-parse", "HEAD")
        path.write_text("---\ntitle: Démo\n---\nV2\n", encoding="utf-8")
        git(self.repo, "add", ".")
        self.commit("consigne simplifiée")
        self.v2 = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "unrelated.txt").write_text("autre ressource", encoding="utf-8")
        git(self.repo, "add", ".")
        self.commit("autre activité")
        self.v3 = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", "refs/heads/alliage/test", self.v3)
        git(self.repo, "update-ref", "refs/remotes/origin/alliage/test", self.v3)

    def commit(self, message):
        git(self.repo, "-c", "user.name=Demo", "-c", "user.email=demo@example.test",
            "commit", "-qm", message)

    def test_working_published_and_history_without_checkout(self):
        before = git(self.repo, "rev-parse", "HEAD")
        result = inspect(self.repo, "demo/cours", SOURCE, "refs/heads/alliage/test", self.v1)
        self.assertEqual(result["resource_id"], "quarto:demo/cours:cours/activite.qmd")
        self.assertEqual(result["working"]["commit"], self.v3)
        self.assertEqual(result["published"]["commit"], self.v1)
        self.assertTrue(result["published"]["is_ancestor_of_working"])
        self.assertFalse(result["published"]["deployment_verified"])
        self.assertEqual([x["commit"] for x in result["history"]], [self.v2, self.v1])
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), before)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_working_branch_remote_and_absent_publication(self):
        result = inspect(self.repo, "demo/cours", SOURCE, "refs/remotes/origin/alliage/test")
        self.assertIsNone(result["published"])
        self.assertEqual(result["publication_status"], "UNDECLARED")
        self.assertEqual(result["working"]["commit"], self.v3)
        self.assertEqual(result["working"]["git_blob"],
                         inspect(self.repo, "demo/cours", SOURCE, "refs/heads/alliage/test")["working"]["git_blob"])

    def test_reject_bad_paths_refs_and_publication(self):
        for bad in ("../private.qmd", "/tmp/essai.qmd", "cours/../secret.qmd", "cours/x.txt", "cours//essai.qmd"):
            with self.subTest(bad=bad), self.assertRaises(VersionError):
                inspect(self.repo, "demo/cours", bad, "refs/heads/alliage/test")
        for ref in ("HEAD", "main", "--help", "refs/heads/a..b", "refs/tags/latest"):
            with self.subTest(ref=ref), self.assertRaises(VersionError):
                inspect(self.repo, "demo/cours", SOURCE, ref)
        for published in ("main", "0" * 40):
            with self.subTest(published=published), self.assertRaises(VersionError):
                inspect(self.repo, "demo/cours", SOURCE, "refs/heads/alliage/test", published)

    def test_reject_symlink_at_revision(self):
        path = self.repo / SOURCE
        path.unlink()
        path.symlink_to("../unrelated.txt")
        git(self.repo, "add", ".")
        self.commit("lien symbolique interdit")
        git(self.repo, "update-ref", "refs/heads/alliage/test", "HEAD")
        with self.assertRaises(VersionError):
            inspect(self.repo, "demo/cours", SOURCE, "refs/heads/alliage/test")


    def test_replace_objects_cannot_falsify_commit_provenance(self):
        git(self.repo, "update-ref", "refs/heads/alliage/test", self.v1)
        original_blob = git(self.repo, "--no-replace-objects", "rev-parse", self.v1 + ":" + SOURCE)
        original_bytes = (self.repo / SOURCE).read_bytes().replace(b"V2", b"V1")
        git(self.repo, "replace", self.v1, self.v2)
        result = inspect(self.repo, "demo/cours", SOURCE, "refs/heads/alliage/test", self.v1)
        self.assertEqual(result["working"]["commit"], self.v1)
        self.assertEqual(result["working"]["git_blob"], original_blob)
        self.assertEqual(result["working"]["sha256"], hashlib.sha256(original_bytes).hexdigest())
        self.assertEqual([h["commit"] for h in result["history"]], [self.v1])
        self.assertEqual(result["published"]["git_blob"], original_blob)

    def test_non_ascii_and_quoted_source_path(self):
        names = ("cours/activité.qmd", 'cours/act"ivite.qmd')
        for name in names:
            (self.repo / name).write_text("---\ntitle: Demo\n---\nContenu\n", encoding="utf-8")
        git(self.repo, "add", ".")
        self.commit("création de ressources")
        git(self.repo, "update-ref", "refs/heads/alliage/test", "HEAD")
        expected_sha = git(self.repo, "rev-parse", "HEAD")
        for name in names:
            with self.subTest(name=name):
                result = inspect(self.repo, "demo/cours", name, "refs/heads/alliage/test")
                self.assertEqual(result["working"]["commit"], expected_sha)
                self.assertEqual(result["working"]["git_blob"],
                                 git(self.repo, "--no-replace-objects", "rev-parse", expected_sha + ":" + name))
                self.assertEqual([h["commit"] for h in result["history"]], [expected_sha])

    def test_commit_subject_with_carriage_return(self):
        (self.repo / SOURCE).write_text("---\ntitle: Demo\n---\nV4\n", encoding="utf-8")
        git(self.repo, "add", ".")
        self.commit("reformulation\rmoins directive")
        git(self.repo, "update-ref", "refs/heads/alliage/test", "HEAD")
        new_head = git(self.repo, "rev-parse", "HEAD")
        result = inspect(self.repo, "demo/cours", SOURCE, "refs/heads/alliage/test")
        self.assertEqual(result["working"]["commit"], new_head)
        self.assertEqual(result["history"][0]["commit"], new_head)
        self.assertEqual(result["history"][0]["label_unverified"], "reformulation\rmoins directive")
        self.assertEqual([h["commit"] for h in result["history"]][1:], [self.v2, self.v1])

    def test_local_dirty_source_is_not_confused_with_commit(self):
        path = self.repo / SOURCE
        path.write_text("MODIFICATION NON COMMITÉE", encoding="utf-8")
        result = inspect(self.repo, "demo/cours", SOURCE, "refs/heads/alliage/test", self.v1)
        self.assertEqual(result["working"]["commit"], self.v3)
        self.assertNotEqual(result["working"]["sha256"], __import__("hashlib").sha256(path.read_bytes()).hexdigest())
        self.assertEqual(path.read_text(), "MODIFICATION NON COMMITÉE")


if __name__ == "__main__":
    unittest.main()
