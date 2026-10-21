# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit Git adversarial tests and opt-in real Quarto render smoke test."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quarto_historical_preview import create_preview, PreviewError


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE).decode().strip()


class HistoricalPreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "source"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        self.write("_quarto.yml", "project:\n  type: default\n  output-dir: _site\nformat:\n  html:\n    toc: false\n    css: styles.css\nexecute:\n  enabled: false\n")
        self.write("activite.qmd", "---\ntitle: Essai fictif\n---\n\n## Consigne\nTexte V1.\n\n![Forme](assets/figure.svg)\n")
        self.write("assets/figure.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12"><circle cx="6" cy="6" r="5"/></svg>')
        self.write("styles.css", "h2 { color: blue; }\n")
        self.commit("V1")
        self.v1 = git(self.repo, "rev-parse", "HEAD")
        self.write("activite.qmd", "---\ntitle: Essai fictif\n---\n\n## Consigne\nTexte V2.\n\n![Forme](assets/figure.svg)\n")
        self.write("_quarto.yml", "project:\n  type: default\n  output-dir: _site\nformat:\n  html:\n    toc: true\n    css: styles.css\nexecute:\n  enabled: false\n")
        self.commit("V2")
        self.v2 = git(self.repo, "rev-parse", "HEAD")
        self.write("styles.css", "h2 { color: red; }\n")
        self.write("assets/figure.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12"><rect width="12" height="12"/></svg>')
        self.commit("V3 sans modifier QMD")
        self.v3 = git(self.repo, "rev-parse", "HEAD")

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit(self, name):
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.name=Fiction", "-c", "user.email=fiction@example.test", "commit", "-qm", name)

    def preview(self, commit, name="export", render=False):
        return create_preview(self.repo, commit, "activite.qmd", self.root / name, render)

    def test_reconstruct_all_dependencies_without_checkout_or_source_change(self):
        before = git(self.repo, "rev-parse", "HEAD")
        self.write("styles.css", "DIRTY UNCOMMITTED\n")
        first = self.preview(self.v1, "first")
        second = self.preview(self.v2, "second")
        third = self.preview(self.v3, "third")
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), before)
        self.assertEqual((self.repo / "styles.css").read_text(), "DIRTY UNCOMMITTED\n")
        self.assertEqual([x["path"] for x in first["tracked_files"]],
                         ["_quarto.yml", "activite.qmd", "assets/figure.svg", "styles.css"])
        self.assertEqual(first["render_status"], "NOT_RENDERED")
        self.assertEqual(second["source_sha256"], third["source_sha256"])
        self.assertNotEqual(first["source_sha256"], second["source_sha256"])
        for path in ("styles.css", "assets/figure.svg"):
            self.assertNotEqual((self.root / "second/project" / path).read_bytes(),
                                (self.root / "third/project" / path).read_bytes())
        self.assertNotEqual((self.root / "first/project/_quarto.yml").read_bytes(),
                            (self.root / "second/project/_quarto.yml").read_bytes())
        for name, result in (("first", first), ("second", second), ("third", third)):
            self.assertEqual(result, json.loads((self.root / name / "manifest.json").read_text()))
            self.assertFalse(result["deployment_verified"])
            self.assertEqual(result["publication_status"], "NOT_INITIATED_BY_ALLIAGE")
            self.assertIsNone(result["source_repository_modified"])
            self.assertFalse(result["source_repository_modification_verified"])
            self.assertEqual(result["external_render_effects"], "NOT_APPLICABLE")
            for item in result["tracked_files"]:
                data = (self.root / name / "project" / item["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])

    def test_reject_unsafe_destinations_and_unknown_revisions(self):
        with self.assertRaises(PreviewError):
            self.preview("main", "bad")
        with self.assertRaises(PreviewError):
            create_preview(self.repo, self.v1, "../secret.qmd", self.root / "bad")
        with self.assertRaises(PreviewError):
            create_preview(self.repo, self.v1, "absent.qmd", self.root / "bad")
        with self.assertRaises(PreviewError):
            create_preview(self.repo, self.v1, "activite.qmd", self.repo / "bad")
        with self.assertRaises(PreviewError):
            create_preview(self.repo, self.v1, "activite.qmd", self.root)
        self.assertFalse((self.repo / "bad").exists())

    def test_git_replace_is_not_allowed_to_change_snapshot(self):
        git(self.repo, "replace", self.v1, self.v2)
        result = self.preview(self.v1)
        self.assertIn("Texte V1", (self.root / "export/project/activite.qmd").read_text())
        self.assertEqual(result["commit"], self.v1)

    def test_reject_symlinks_and_git_lfs_pointers(self):
        link = self.repo / "shortcut"
        link.symlink_to("styles.css")
        self.commit("symlink")
        with self.assertRaisesRegex(PreviewError, "lien symbolique"):
            self.preview(git(self.repo, "rev-parse", "HEAD"), "linked")
        link.unlink()
        git(self.repo, "add", "-A")
        self.write("data.txt", "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 8\n")
        self.commit("LFS pointer")
        with self.assertRaisesRegex(PreviewError, "Git LFS"):
            self.preview(git(self.repo, "rev-parse", "HEAD"), "lfs")
        self.assertFalse((self.root / "lfs").exists())


    def test_lying_render_hook_cannot_establish_external_non_mutation(self):
        """A renderer stub can mutate the source without changing the extracted files."""
        real_run = subprocess.run

        def fake_run(args, **kwargs):
            if args[:2] == ["quarto", "--version"]:
                return subprocess.CompletedProcess(args, 0, stdout="test-quarto\n", stderr="")
            if args[:2] == ["quarto", "render"]:
                Path(kwargs["cwd"], "activite.html").write_text(
                    "<!doctype html><html><body>Essai isolé</body></html>", encoding="utf-8")
                (self.repo / "styles.css").write_text("MUTATION EXTERNE\n", encoding="utf-8")
                return subprocess.CompletedProcess(args, 0, stdout="ok\n", stderr="")
            return real_run(args, **kwargs)

        with mock.patch("quarto_historical_preview.shutil.which", return_value="/fake/quarto"), \
                mock.patch("quarto_historical_preview.subprocess.run", side_effect=fake_run):
            report = self.preview(self.v1, "hook-test", render=True)
        self.assertEqual((self.repo / "styles.css").read_text(), "MUTATION EXTERNE\n")
        self.assertEqual(report["render_status"], "RENDERED_FROM_GIT_SNAPSHOT")
        self.assertEqual(report["publication_status"], "NOT_INITIATED_BY_ALLIAGE")
        self.assertIsNone(report["source_repository_modified"])
        self.assertFalse(report["source_repository_modification_verified"])
        self.assertFalse(report["deployment_verified"])
        self.assertEqual(report["external_render_effects"], "NOT_VERIFIED")
        self.assertFalse(report["rendered_html"]["existed_before_render"])

    def test_real_quarto_custom_output_and_stale_default_html_must_fail(self):
        """Quarto may produce 'personnalise.html'; a tracked 'activite.html' is stale."""
        if os.environ.get("ALLIAGE_TEST_REAL_QUARTO") != "1":
            self.skipTest("Real Quarto validation requires ALLIAGE_TEST_REAL_QUARTO=1")
        if not shutil.which("quarto"):
            self.fail("Quarto executable is mandatory")
        self.write("activite.qmd",
                   "---\ntitle: Fictif\nformat:\n  html:\n    output-file: personnalise.html\n---\n\n## Essai\nSortie personnalisée.\n")
        self.write("activite.html", "<!doctype html><p>HTML ANCIEN</p>")
        self.commit("HTML obsolète et nom de sortie personnalisé")
        version = git(self.repo, "rev-parse", "HEAD")

        # Vérifier par le moteur réel que cette option produit bien un AUTRE nom.
        control = self.root / "quarto-control"
        shutil.copytree(self.repo, control, ignore=shutil.ignore_patterns(".git"))
        run = subprocess.run(["quarto", "render", "activite.qmd", "--to", "html",
                              "--no-execute"], cwd=control, text=True, capture_output=True, timeout=90)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue(list(control.rglob("personnalise.html")),
                        "Quarto doit réellement avoir écrit la sortie personnalisée")
        self.assertEqual((control / "activite.html").read_text(encoding="utf-8"),
                         "<!doctype html><p>HTML ANCIEN</p>")

        with self.assertRaisesRegex(PreviewError, "préexistant"):
            self.preview(version, "stale", render=True)
        self.assertFalse((self.root / "stale").exists())

    def test_reject_project_rendering_multiple_documents_or_missing_project_file(self):
        self.write("autre.qmd", "---\ntitle: Autre essai\n---\n\n# Autre\n")
        self.commit("projet à deux documents")
        version = git(self.repo, "rev-parse", "HEAD")
        # L'extraction reste possible en lecture seule ; le rendu est refusé.
        self.assertEqual(self.preview(version, "snapshot-only")["render_status"], "NOT_RENDERED")
        with self.assertRaisesRegex(PreviewError, "unique exigée"):
            self.preview(version, "multiple", render=True)
        self.assertFalse((self.root / "multiple").exists())
        (self.repo / "_quarto.yml").unlink()
        self.commit("projet sans configuration")
        with self.assertRaisesRegex(PreviewError, "_quarto.yml"):
            self.preview(git(self.repo, "rev-parse", "HEAD"), "missing", render=True)
        self.assertFalse((self.root / "missing").exists())

    def test_real_quarto_render_of_two_versions(self):
        if os.environ.get("ALLIAGE_TEST_REAL_QUARTO") != "1":
            self.skipTest("Real Quarto validation requires ALLIAGE_TEST_REAL_QUARTO=1")
        if not shutil.which("quarto"):
            self.fail("Quarto executable is mandatory for real-render test")
        first = self.preview(self.v1, "first", True)
        second = self.preview(self.v2, "second", True)
        third = self.preview(self.v3, "third", True)
        for x in (first, second, third):
            self.assertEqual(x["render_status"], "RENDERED_FROM_GIT_SNAPSHOT")
            self.assertIsNotNone(x["quarto_version"])
            self.assertFalse(x["rendered_html"]["existed_before_render"])
            self.assertIsNone(x["source_repository_modified"])
            self.assertEqual(x["external_render_effects"], "NOT_VERIFIED")
        html1 = (self.root / "first" / first["rendered_html"]["path"]).read_text(encoding="utf-8")
        html2 = (self.root / "second" / second["rendered_html"]["path"]).read_text(encoding="utf-8")
        html3 = (self.root / "third" / third["rendered_html"]["path"]).read_text(encoding="utf-8")
        self.assertIn("Texte V1", html1)
        self.assertIn("Texte V2", html2)
        # Avant le rendu de projet, ces options _quarto.yml étaient IGNORÉES.
        for html in (html1, html2, html3):
            self.assertIn("styles.css", html)
        self.assertNotIn('id="TOC"', html1)
        for html in (html2, html3):
            self.assertTrue('id="TOC"' in html or "Sommaire" in html)
        for version, manifest in (("first", first), ("second", second), ("third", third)):
            self.assertIn("/_site/", "/" + manifest["rendered_html"]["path"])
            self.assertTrue((self.root / version / "project/_site/styles.css").is_file())
        self.assertEqual(second["source_sha256"], third["source_sha256"])
        self.assertNotEqual((self.root / "second/project/styles.css").read_text(),
                            (self.root / "third/project/styles.css").read_text())
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), self.v3)


if __name__ == "__main__":
    unittest.main()
