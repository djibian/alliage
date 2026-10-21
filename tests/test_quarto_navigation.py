# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.2: local Firefox history page; synthetic data only, no private fixture."""
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from quarto_navigation import NavigationError, build_navigation
from quarto_historical_preview import create_preview


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.patcher = patch("quarto_navigation.Path.home", return_value=self.home)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.session = self.home / "alliage-experiences/historique/p31-final-demo"
        self.session.mkdir(parents=True)
        self.files = {}
        for i in (1, 2, 3):
            self.make_revision(i)

    def make_revision(self, i: int):
        folder = self.session / f"V{i}"
        project = folder / "project"
        site = project / "_site"
        site.mkdir(parents=True, exist_ok=True)
        qmd = f"---\ntitle: Test {i}\n---\n\n## Consigne\nTexte {i}.\n".encode()
        css = f"h2{{color:rgb({i},0,0)}}".encode()
        html = f"<!doctype html><h1>Test {i}</h1>".encode()
        relative = {"activite.qmd": qmd,
                    "styles.css": css,
                    ".github/workflows/demo.yml": b"name: test\n"}
        for name, data in relative.items():
            path = project / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (site / "activite.html").write_bytes(html)
        manifest = {
            "schema": "alliage.quarto-historical-preview.v0",
            "commit": f"{i:040x}", "source_path": "activite.qmd",
            "source_sha256": digest(qmd),
            "tracked_files": [
                {"path": n, "sha256": digest(data), "git_blob": "a" * 40,
                 "bytes": len(data)} for n, data in relative.items()
            ],
            "render_status": "RENDERED_FROM_GIT_SNAPSHOT",
            "publication_status": "NOT_INITIATED_BY_ALLIAGE",
            "deployment_verified": False,
            "external_render_effects": "NOT_VERIFIED",
            "quarto_version": "1.10.19",
            "rendered_html": {"path": "project/_site/activite.html",
                              "sha256": digest(html), "existed_before_render": False},
        }
        (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.files[i] = manifest

    def mutate_manifest(self, version, fn):
        path = self.session / version / "manifest.json"
        obj = json.loads(path.read_text())
        fn(obj)
        path.write_text(json.dumps(obj))

    def test_local_navigation_is_inert_without_extension_and_no_source_modified(self):
        before = {(p.relative_to(self.session), digest(p.read_bytes()))
                  for p in self.session.rglob("*") if p.is_file()}
        result = build_navigation(self.session, ["V1", "V2", "V3"], "V3")
        self.assertEqual(result, self.session / "navigation.html")
        html = result.read_text(encoding="utf-8")
        self.assertIn('<script type="application/json" id="alliage-history-data">', html)
        self.assertNotIn('<script src=', html)
        self.assertIn('<iframe id="alliage-preview-frame"', html)
        self.assertIn("./V3/project/_site/activite.html", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("published_verified", html)
        self.assertNotIn("Aucun contenu élève publié", html)
        self.assertIn("Alliage n'a déclenché aucune publication. Aucun déploiement vérifié.", html)
        record = re.search(r'<script type="application/json" id="alliage-history-data">(.*?)</script>', html)
        self.assertIsNotNone(record)
        payload = json.loads(record.group(1))
        self.assertEqual(payload["schema"], "alliage.quarto-navigation.v0")
        self.assertEqual(payload["reference_id"], "V3")
        self.assertFalse(payload["reference_is_working_tree"])
        self.assertFalse(payload["deployment_verified"])
        self.assertEqual(payload["verification"], "POINT_IN_TIME_ONLY")
        self.assertEqual(len(payload["entries"]), 3)
        after = {(p.relative_to(self.session), digest(p.read_bytes()))
                 for p in self.session.rglob("*") if p.is_file() and p != result}
        self.assertEqual(before, after)
        with self.assertRaisesRegex(NavigationError, "existe déjà"):
            build_navigation(self.session, ["V1", "V2", "V3"], "V2")

    def test_fail_closed_on_tampered_html_or_git_dependency(self):
        (self.session / "V2/project/_site/activite.html").write_text("<h1>tampered</h1>")
        with self.assertRaisesRegex(NavigationError, "HTML historique modifié"):
            build_navigation(self.session, ["V1", "V2", "V3"], "V3")
        self.assertFalse((self.session / "navigation.html").exists())
        self.make_revision(2)
        (self.session / "V2/project/styles.css").write_text("tampered")
        with self.assertRaisesRegex(NavigationError, "Dépendance Git modifiée"):
            build_navigation(self.session, ["V1", "V2", "V3"], "V3")

    def test_fail_closed_on_provenance_or_path_traversal(self):
        self.mutate_manifest("V2", lambda x: x.update(deployment_verified=True))
        with self.assertRaisesRegex(NavigationError, "Statut de rendu"):
            build_navigation(self.session, ["V1", "V2", "V3"], "V3")
        self.make_revision(2)
        self.mutate_manifest("V2", lambda x: x["rendered_html"].update(path="../activite.html"))
        with self.assertRaisesRegex(NavigationError, "HTML différent"):
            build_navigation(self.session, ["V1", "V2", "V3"], "V3")
        self.make_revision(2)
        self.mutate_manifest("V2", lambda x: x["tracked_files"][0].update(path="../activite.qmd"))
        with self.assertRaisesRegex(NavigationError, "Chemin"):
            build_navigation(self.session, ["V1", "V2", "V3"], "V3")

    def test_refuse_tracked_html_candidates_even_when_hashes_match(self):
        """P3.1 would reject either preexisting HTML candidate before rendering."""
        for candidate in ("activite.html", "_site/activite.html"):
            with self.subTest(tracked_html=candidate):
                self.make_revision(2)
                project = self.session / "V2/project"
                html_data = (project / "_site/activite.html").read_bytes()
                old_html = project / candidate
                if candidate != "_site/activite.html":
                    old_html.write_bytes(html_data)
                # Deliberately make the contradictory tracked item internally
                # coherent: it exists, has the right size and SHA-256.
                self.assertEqual(old_html.read_bytes(), html_data)
                def contradiction(manifest):
                    manifest["tracked_files"].append({
                        "path": candidate,
                        "sha256": digest(html_data),
                        "git_blob": "a" * 40,
                        "bytes": len(html_data),
                    })
                    self.assertIs(manifest["rendered_html"]["existed_before_render"], False)
                self.mutate_manifest("V2", contradiction)
                with self.assertRaisesRegex(NavigationError, "Manifeste contradictoire"):
                    build_navigation(self.session, ["V1", "V2", "V3"], "V3")
                self.assertFalse((self.session / "navigation.html").exists())

    def test_fallback_does_not_assert_no_external_publication(self):
        page = build_navigation(self.session, ["V1", "V2", "V3"], "V3")
        markup = page.read_text(encoding="utf-8")
        self.assertIn("Alliage n'a déclenché aucune publication.", markup)
        self.assertIn("Aucun déploiement vérifié.", markup)
        self.assertNotIn("Aucun contenu élève publié", markup)

    def test_reject_symlinked_html_and_wrong_or_duplicate_reference(self):
        target = self.session / "V3/project/_site/activite.html"
        target.unlink()
        target.symlink_to(self.session / "V1/project/_site/activite.html")
        with self.assertRaisesRegex(NavigationError, "Lien symbolique"):
            build_navigation(self.session, ["V1", "V2", "V3"], "V3")
        target.unlink()
        self.make_revision(3)
        for versions, reference in ((["V1", "V1"], "V1"),
                                    (["V1", "V2"], "V3"),
                                    (["V1"], "V1")):
            with self.assertRaises(NavigationError):
                build_navigation(self.session, versions, reference)

    def test_requires_explicit_pilot_session_location(self):
        invalid = self.home / "other-place"
        invalid.mkdir()
        with self.assertRaisesRegex(NavigationError, "p31-final"):
            build_navigation(invalid, ["V1", "V2"], "V2")


    def test_real_quarto_snapshots_feed_same_tab_navigator(self):
        if os.environ.get("ALLIAGE_TEST_REAL_QUARTO") != "1":
            self.skipTest("Test Quarto réel réservé au workflow dédié")
        if not shutil.which("quarto"):
            self.fail("Quarto réel obligatoire")
        # Single source, two commits and the complete P3.1 manifest, not mocks.
        # Remove only the synthetic local fixtures belonging to this test.
        for version in ("V1", "V2"):
            shutil.rmtree(self.session / version)
        repo = self.home / "fiction-git"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / "_quarto.yml").write_text(
            "project:\n  type: default\n  output-dir: _site\n"
            "format:\n  html:\n    toc: true\n    css: styles.css\n", encoding="utf-8")
        (repo / "styles.css").write_text("h2{color:blue}", encoding="utf-8")
        commits = []
        for number in (1, 2):
            (repo / "activite.qmd").write_text(
                f"---\ntitle: Activité fictive {number}\n---\n\n## Consigne\nVersion {number}.\n",
                encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fiction",
                            "-c", "user.email=fiction@example.test", "commit", "-qm",
                            f"V{number}"], check=True)
            commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"],
                                             text=True).strip()
            commits.append(commit)
            snapshot = create_preview(repo, commit, "activite.qmd",
                                      self.session / f"V{number}", True)
            self.assertEqual(snapshot["render_status"], "RENDERED_FROM_GIT_SNAPSHOT")
        page = build_navigation(self.session, ["V1", "V2"], "V2")
        self.assertTrue(page.is_file())
        self.assertIn(commits[0], page.read_text())
        self.assertIn(commits[1], page.read_text())
        self.assertEqual(subprocess.check_output(
            ["git", "-C", str(repo), "status", "--porcelain"], text=True), "")

    def test_existing_extension_v04_remains_scoped(self):
        config = json.loads((ROOT / "extension/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(config["version"], "0.4.0")
        self.assertEqual(len(config["content_scripts"]), 2)
        self.assertEqual(config["content_scripts"][0]["js"], ["atelier.js"])
        self.assertEqual(config["content_scripts"][1]["js"], ["historique.js"])
        self.assertEqual(config["content_scripts"][1]["matches"],
                         ["file:///*/alliage-experiences/historique/p31-final-*/navigation.html"])
        self.assertNotIn("<all_urls>", str(config))


if __name__ == "__main__":
    unittest.main()
