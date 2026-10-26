# SPDX-License-Identifier: AGPL-3.0-or-later
"""Experimental P3.3→P3.1→P3.2 tests; synthetic Git fixtures only."""
from __future__ import annotations

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
from quarto_observed_session import SessionError, create_observed_session, observe
from quarto_historical_preview import PreviewError, _git as preview_git, create_preview

REF = "refs/remotes/origin/experiment/laboratoire"
CONFIG = "project:\n  type: default\n  output-dir: _site\n\nformat:\n  html:\n    css: styles.css\n\nexecute:\n  enabled: false\n"


def git(repo, *argv):
    return subprocess.check_output(
        ["git", "--no-replace-objects", "-C", str(repo), *argv],
        text=True, stderr=subprocess.PIPE).strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ObservedSessionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.repo = self.home / "fictitious"
        self.repo.mkdir()
        self.home_patch = patch("quarto_observed_session.Path.home", return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        git(self.repo, "init", "-q")
        (self.repo / "_quarto.yml").write_text(CONFIG, encoding="utf-8")
        (self.repo / "activite.qmd").write_text(
            "---\ntitle: Fictif\n---\n\n## Consigne\nUne activité fictive.\n", encoding="utf-8")
        (self.repo / "styles.css").write_text("h2 { color: #991b1b; }\n", encoding="utf-8")
        self.commit("version rouge")
        self.initial = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", REF, self.initial)
        (self.repo / "styles.css").write_text("h2 { color: #7c3aed; }\n", encoding="utf-8")
        self.commit("version violette")
        self.second = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", REF, self.second)

    def commit(self, message):
        git(self.repo, "add", "-A")
        git(self.repo, "-c", "user.name=Fixture",
            "-c", "user.email=fixture@example.test", "commit", "-qm", message)

    def observed(self):
        return observe(self.repo, "fiction/laboratoire", "activite.qmd", REF, self.initial)

    def run_session(self, *, trust=True):
        return create_observed_session(
            self.repo, "fiction/laboratoire", "activite.qmd", REF, self.initial,
            trusted_quarto=trust)

    @staticmethod
    def fake_preview(repo, revision, source, out, render=True):
        """P3.1-compatible manifest to test the P3.2 integration without Quarto."""
        assert render is True
        assert source == "activite.qmd"
        out.mkdir()
        project = out / "project"
        site = project / "_site"
        site.mkdir(parents=True)
        tracked = []
        for name in ("activite.qmd", "styles.css", "_quarto.yml"):
            data = subprocess.check_output(["git", "-C", str(repo),
                                            "show", revision + ":" + name])
            (project / name).write_bytes(data)
            tracked.append({"path": name, "sha256": digest(data),
                            "bytes": len(data), "git_blob": "a" * 40})
        html = b'<!doctype html><html><head><link rel="stylesheet" href="styles.css"></head><body>Fictif</body></html>'
        (site / "activite.html").write_bytes(html)
        manifest = {
            "schema": "alliage.quarto-historical-preview.v0",
            "commit": revision, "source_path": source,
            "source_sha256": next(x["sha256"] for x in tracked if x["path"] == source),
            "tracked_files": tracked,
            "render_status": "RENDERED_FROM_GIT_SNAPSHOT",
            "rendered_html": {"path": "project/_site/activite.html",
                              "sha256": digest(html), "existed_before_render": False},
            "quarto_version": "fixture-quarto",
            "publication_status": "NOT_INITIATED_BY_ALLIAGE",
            "deployment_verified": False, "external_render_effects": "NOT_VERIFIED",
        }
        (out / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return manifest

    def test_check_is_read_only_and_css_change_is_real(self):
        before = (git(self.repo, "rev-parse", "HEAD"),
                  git(self.repo, "status", "--porcelain=v1"))
        report = self.observed()
        self.assertEqual(report["relation"], "FAST_FORWARD")
        self.assertTrue(report["project_tree_changed"])
        self.assertFalse(report["source_blob_changed"])
        self.assertEqual(report["observed_commit"], self.second)
        self.assertFalse(report["remote_freshness_verified"])
        self.assertFalse(report["deployment_verified"])
        self.assertEqual(before, (git(self.repo, "rev-parse", "HEAD"),
                                  git(self.repo, "status", "--porcelain=v1")))
        self.assertFalse((self.home / "alliage-experiences").exists())

    def test_session_reuses_p31_p32_and_never_touches_dirty_checkout(self):
        (self.repo / "activite.qmd").write_text("MODIFICATION NON ENREGISTREE")
        before = (git(self.repo, "rev-parse", "HEAD"),
                  git(self.repo, "status", "--porcelain=v1"))
        with patch("quarto_observed_session.create_preview", side_effect=self.fake_preview):
            report = self.run_session()
            again = self.run_session()
        self.assertEqual(report["baseline_commit"], self.initial)
        self.assertEqual(report["observed_commit"], self.second)
        self.assertEqual(report["local_reference"], "V1")
        self.assertEqual(report["local_observed"], "V2")
        self.assertFalse(report["remote_freshness_verified"])
        self.assertFalse(report["deployment_verified"])
        self.assertFalse(report["firefox_manually_verified"])
        self.assertTrue(report["navigation_url"].startswith("file://"))
        session = Path(report["session_path"])
        self.assertTrue((session / "navigation.html").is_file())
        self.assertIn("./V1/project/_site/activite.html",
                      (session / "navigation.html").read_text())
        self.assertEqual(json.loads((session / "V1/manifest.json").read_text())["commit"],
                         self.initial)
        self.assertEqual(json.loads((session / "V2/manifest.json").read_text())["commit"],
                         self.second)
        self.assertNotEqual(again["session_path"], report["session_path"])
        self.assertTrue((session / "navigation.html").exists())
        self.assertEqual(before, (git(self.repo, "rev-parse", "HEAD"),
                                  git(self.repo, "status", "--porcelain=v1")))

    def test_refuse_unsupported_resource_and_no_trust_without_session(self):
        with self.assertRaisesRegex(SessionError, "activite.qmd"):
            observe(self.repo, "fiction/laboratoire", "autre.qmd", REF, self.initial)
        with self.assertRaisesRegex(SessionError, "trusted-quarto"):
            self.run_session(trust=False)
        self.assertFalse((self.home / "alliage-experiences").exists())

    def test_refuse_unchanged_rewound_divergent_and_unmodified_tree(self):
        git(self.repo, "update-ref", REF, self.initial)
        with self.assertRaisesRegex(SessionError, "FAST_FORWARD"):
            self.observed()
        with self.assertRaisesRegex(SessionError, "FAST_FORWARD"):
            observe(self.repo, "fiction/laboratoire", "activite.qmd", REF, self.second)
        git(self.repo, "checkout", "-q", "--detach", self.initial)
        (self.repo / "styles.css").write_text("h2 {color: #113355;}\n")
        self.commit("branche concurrente")
        different = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", REF, different)
        with self.assertRaisesRegex(SessionError, "FAST_FORWARD"):
            observe(self.repo, "fiction/laboratoire", "activite.qmd", REF, self.second)
        self.assertFalse((self.home / "alliage-experiences").exists())

    def test_failure_or_tampering_removes_partial_session(self):
        calls = []
        def failure(*args, **kwargs):
            calls.append(1)
            if len(calls) == 2:
                raise PreviewError("Quarto fictif en échec")
            return self.fake_preview(*args, **kwargs)
        with patch("quarto_observed_session.create_preview", side_effect=failure):
            with self.assertRaisesRegex(PreviewError, "Quarto fictif"):
                self.run_session()
        root = self.home / "alliage-experiences" / "historique"
        self.assertEqual(list(root.iterdir()), [])

        def tamper(*args, **kwargs):
            report = self.fake_preview(*args, **kwargs)
            if Path(args[3]).name == "V2":
                (Path(args[3]) / "project/styles.css").write_text("MODIFIÉ")
            return report
        with patch("quarto_observed_session.create_preview", side_effect=tamper):
            with self.assertRaisesRegex(ValueError, "Dépendance Git modifiée"):
                self.run_session()
        self.assertEqual(list(root.iterdir()), [])

    def test_tracking_ref_move_during_render_does_not_change_pinned_sha(self):
        commits = []
        def move_ref(*args, **kwargs):
            commits.append(args[1])
            if len(commits) == 1:
                git(self.repo, "update-ref", REF, self.initial)
            return self.fake_preview(*args, **kwargs)
        with patch("quarto_observed_session.create_preview", side_effect=move_ref):
            report = self.run_session()
        self.assertEqual(commits, [self.initial, self.second])
        self.assertEqual(report["observed_commit"], self.second)
        self.assertEqual(git(self.repo, "rev-parse", REF), self.initial)

    def test_reject_symlinked_history_root(self):
        target = self.home / "redirect"
        target.mkdir()
        (self.home / "alliage-experiences").symlink_to(target, target_is_directory=True)
        with patch("quarto_observed_session.create_preview", side_effect=self.fake_preview):
            with self.assertRaisesRegex(SessionError, "symbolique"):
                self.run_session()
        self.assertEqual(list(target.iterdir()), [])

    def test_p31_git_read_overrides_unsafe_inherited_lazy_fetch_option(self):
        with patch.dict(os.environ, {"GIT_NO_LAZY_FETCH": "0"}):
            with patch("quarto_historical_preview.subprocess.run",
                       wraps=subprocess.run) as calls:
                self.assertEqual(preview_git(self.repo, "rev-parse", "HEAD").decode().strip(),
                                 self.second)
                self.assertEqual(calls.call_args.kwargs["env"]["GIT_NO_LAZY_FETCH"], "1")
                self.assertEqual(calls.call_args.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")

    def test_real_quarto_observation_and_css_only_render(self):
        if os.environ.get("ALLIAGE_TEST_REAL_QUARTO") != "1":
            self.skipTest("Rendu Quarto réel uniquement dans la CI dédiée")
        report = self.run_session()
        session = Path(report["session_path"])
        for v, expected in (("V1", b"#991b1b"), ("V2", b"#7c3aed")):
            manifest = json.loads((session / v / "manifest.json").read_text())
            self.assertEqual(manifest["render_status"], "RENDERED_FROM_GIT_SNAPSHOT")
            self.assertEqual(manifest["source_path"], "activite.qmd")
            self.assertIn(expected, (session / v / "project/_site/styles.css").read_bytes())
            html = session / v / manifest["rendered_html"]["path"]
            self.assertIn("styles.css", html.read_text(encoding="utf-8"))
        self.assertTrue((session / "navigation.html").is_file())


if __name__ == "__main__":
    unittest.main()
