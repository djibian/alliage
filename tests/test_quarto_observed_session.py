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
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quarto_observed_session import SessionError, create_observed_session, observe
from quarto_historical_preview import PreviewError, _git as preview_git, create_preview
from quarto_resource_entry import resource_entry_url
from quarto_navigation import NavigationError

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
        rendered_css = (project / "styles.css").read_bytes()
        (site / "styles.css").write_bytes(rendered_css)
        rendered_files = [
            {"path": "project/_site/activite.html", "sha256": digest(html),
             "bytes": len(html)},
            {"path": "project/_site/styles.css", "sha256": digest(rendered_css),
             "bytes": len(rendered_css)},
        ]
        manifest = {
            "schema": "alliage.quarto-historical-preview.v0",
            "commit": revision, "source_path": source,
            "source_sha256": next(x["sha256"] for x in tracked if x["path"] == source),
            "tracked_files": tracked,
            "rendered_files": rendered_files,
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
        self.assertTrue(report["checkout_head_and_status_unchanged"])
        self.assertFalse(report["checkout_file_contents_unchanged_verified"])
        self.assertNotIn("checkout_unchanged_at_completion", report)
        self.assertTrue(report["navigation_url"].startswith("file://"))
        self.assertEqual(report["resource_surface"],
                         "LOCAL_RENDERED_HTML_NOT_CANONICAL_PUBLICATION")
        direct = urlsplit(report["resource_url"])
        self.assertEqual(direct.scheme, "file")
        self.assertTrue(direct.path.endswith("/V2/project/_site/activite.html"))
        self.assertIn("alliage-history-v0", parse_qs(direct.query))
        data = json.loads(parse_qs(direct.query)["alliage-history-v0"][0])
        self.assertEqual(data["schema"], "alliage.quarto-resource-history.v0")
        self.assertEqual(data["resource_id"], "quarto:fiction/laboratoire:activite.qmd")
        self.assertEqual(data["entries"],
                         [{"id": "V1", "commit": self.initial},
                          {"id": "V2", "commit": self.second}])
        self.assertFalse(data["deployment_verified"])
        self.assertFalse(data["publication_performed"])
        self.assertEqual(data["verification"], "POINT_IN_TIME_ONLY")
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

    def test_resource_url_refuses_tampered_preview_without_mutating_originals(self):
        with patch("quarto_observed_session.create_preview", side_effect=self.fake_preview):
            report = self.run_session()
        session = Path(report["session_path"])
        source_html = session / "V2/project/_site/activite.html"
        before = source_html.read_bytes()
        url = resource_entry_url(
            session, reference="V1", observed="V2",
            resource_id="quarto:fiction/laboratoire:activite.qmd")
        self.assertTrue(url.startswith(source_html.as_uri()))
        self.assertEqual(source_html.read_bytes(), before)
        (session / "V1/project/styles.css").write_text("ALTÉRÉ", encoding="utf-8")
        with self.assertRaisesRegex(NavigationError, "Dépendance Git modifiée"):
            resource_entry_url(
                session, reference="V1", observed="V2",
                resource_id="quarto:fiction/laboratoire:activite.qmd")
        self.assertEqual(source_html.read_bytes(), before)

    def test_generated_css_tampering_refused_even_with_intact_git_inputs(self):
        """B1: generated CSS is not the Git-tracked styles.css."""
        with patch("quarto_observed_session.create_preview", side_effect=self.fake_preview):
            report = self.run_session()
        session = Path(report["session_path"])
        generated = session / "V2/project/_site/styles.css"
        tracked = session / "V2/project/styles.css"
        before_tracked = tracked.read_bytes()
        generated.write_text("h2{color:black}", encoding="utf-8")
        self.assertEqual(tracked.read_bytes(), before_tracked)
        with self.assertRaisesRegex(NavigationError, "Dépendance Quarto générée modifiée"):
            resource_entry_url(session,
                resource_id="quarto:fiction/laboratoire:activite.qmd")

    def test_generated_inventory_refuses_missing_and_extra_css_files(self):
        """New assets, removed assets and omissions cannot escape the inventory."""
        with patch("quarto_observed_session.create_preview", side_effect=self.fake_preview):
            report = self.run_session()
        session = Path(report["session_path"])
        project = session / "V2/project"
        extra = project / "_site/extra.css"
        extra.write_text("fake", encoding="utf-8")
        with self.assertRaisesRegex(NavigationError, "Inventaire des sorties Quarto"):
            resource_entry_url(session,
                resource_id="quarto:fiction/laboratoire:activite.qmd")
        extra.unlink()
        manifest_path = session / "V2/manifest.json"
        original = json.loads(manifest_path.read_text())
        altered = dict(original)
        altered["rendered_files"] = [
            item for item in original["rendered_files"]
            if not item["path"].endswith("/styles.css")
        ]
        manifest_path.write_text(json.dumps(altered))
        with self.assertRaisesRegex(NavigationError, "Inventaire des sorties Quarto"):
            resource_entry_url(session,
                resource_id="quarto:fiction/laboratoire:activite.qmd")
        manifest_path.write_text(json.dumps(original))
        (project / "_site/styles.css").unlink()
        with self.assertRaisesRegex(NavigationError, "Fichier d'aperçu absent"):
            resource_entry_url(session,
                resource_id="quarto:fiction/laboratoire:activite.qmd")

    def test_resource_entry_refuses_legacy_manifest_without_rendered_inventory(self):
        """P3.2 legacy navigation may read it; direct history requires the stronger proof."""
        with patch("quarto_observed_session.create_preview", side_effect=self.fake_preview):
            report = self.run_session()
        session = Path(report["session_path"])
        manifest_path = session / "V1/manifest.json"
        manifest = json.loads(manifest_path.read_text())
        del manifest["rendered_files"]
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(NavigationError, "CSS non attestées"):
            resource_entry_url(session,
                resource_id="quarto:fiction/laboratoire:activite.qmd")

    def test_resource_entry_refuses_individually_valid_different_qmd(self):
        """B2: a V1 manifest for another QMD must never pair with V2."""
        with patch("quarto_observed_session.create_preview", side_effect=self.fake_preview):
            report = self.run_session()
        session = Path(report["session_path"])
        version = session / "V1"
        project = version / "project"
        manifest_path = version / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        other = b"---\\ntitle: Fictif autre\\n---\\n\\n## Autre\\n".replace(b"\\n", b"\n")
        (project / "autre.qmd").write_bytes(other)
        manifest["tracked_files"].append({
            "path":"autre.qmd", "sha256":digest(other), "git_blob":"a"*40,
            "bytes":len(other)
        })
        manifest["source_path"] = "autre.qmd"
        manifest["source_sha256"] = digest(other)
        old_html = project / "_site/activite.html"
        new_html = project / "_site/autre.html"
        old_html.rename(new_html)
        data = new_html.read_bytes()
        manifest["rendered_html"]["path"] = "project/_site/autre.html"
        manifest["rendered_html"]["sha256"] = digest(data)
        for item in manifest["rendered_files"]:
            if item["path"].endswith("/activite.html"):
                item["path"] = "project/_site/autre.html"
                break
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(NavigationError, "Identité source/HTML"):
            resource_entry_url(session,
                resource_id="quarto:fiction/laboratoire:activite.qmd")

    def test_resource_entry_refuses_root_html_despite_valid_manifest(self):
        """P3.2 supports root historical HTML; the direct URL does not."""
        with patch("quarto_observed_session.create_preview", side_effect=self.fake_preview):
            report = self.run_session()
        session = Path(report["session_path"])
        version = session / "V1"
        manifest_path = version / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        root_html = version / "project/activite.html"
        root_html.write_bytes((version / "project/_site/activite.html").read_bytes())
        manifest["rendered_html"]["path"] = "project/activite.html"
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(NavigationError, "Identité source/HTML"):
            resource_entry_url(session,
                resource_id="quarto:fiction/laboratoire:activite.qmd")

    def test_resource_url_refuses_forged_session_or_missing_navigation(self):
        with patch("quarto_observed_session.create_preview", side_effect=self.fake_preview):
            report = self.run_session()
        session = Path(report["session_path"])
        (session / "navigation.html").unlink()
        with self.assertRaisesRegex(NavigationError, "non autorisée"):
            resource_entry_url(
                session, resource_id="quarto:fiction/laboratoire:activite.qmd")
        with self.assertRaisesRegex(NavigationError, "non autorisée"):
            resource_entry_url(
                self.repo, resource_id="quarto:fiction/laboratoire:activite.qmd")
        # An invalid declaration cannot create a seemingly authoritative URL.
        (session / "navigation.html").write_text("fixture placeholder", encoding="utf-8")
        with self.assertRaisesRegex(NavigationError, "Identité de ressource"):
            resource_entry_url(
                session, resource_id="quarto:../../private:activite.qmd")

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

    def test_ctrl_c_removes_only_new_session_and_preserves_prior_sessions(self):
        """A Python keyboard interruption must not leave a partial V1/V2."""
        with patch("quarto_observed_session.create_preview", side_effect=self.fake_preview):
            previous = self.run_session()
        previous_dir = Path(previous["session_path"])
        previous_files = {str(p.relative_to(previous_dir)): digest(p.read_bytes())
                          for p in previous_dir.rglob("*") if p.is_file()}
        calls = []
        def interrupted(*args, **kwargs):
            calls.append(args[1])
            if len(calls) == 2:
                raise KeyboardInterrupt("interruption pendant V2")
            return self.fake_preview(*args, **kwargs)
        with patch("quarto_observed_session.create_preview", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.run_session()
        self.assertEqual(calls, [self.initial, self.second])
        self.assertEqual(list(previous_dir.parent.iterdir()), [previous_dir])
        self.assertEqual(previous_files,
                         {str(p.relative_to(previous_dir)): digest(p.read_bytes())
                          for p in previous_dir.rglob("*") if p.is_file()})

    def test_dirty_checkout_content_is_not_claimed_integrity_verified(self):
        """Preserving 'M' status does not prove bytes were preserved."""
        dirty = self.repo / "activite.qmd"
        dirty.write_text("NON COMMITÉ AVANT", encoding="utf-8")
        before_status = git(self.repo, "status", "--porcelain=v1")
        def alter_dirty_file(*args, **kwargs):
            if Path(args[3]).name == "V2":
                dirty.write_text("NON COMMITÉ APRES", encoding="utf-8")
            return self.fake_preview(*args, **kwargs)
        with patch("quarto_observed_session.create_preview", side_effect=alter_dirty_file):
            report = self.run_session()
        self.assertEqual(before_status, git(self.repo, "status", "--porcelain=v1"))
        self.assertEqual(dirty.read_text(encoding="utf-8"), "NON COMMITÉ APRES")
        self.assertTrue(report["checkout_head_and_status_unchanged"])
        self.assertFalse(report["checkout_file_contents_unchanged_verified"])
        self.assertNotIn("checkout_unchanged_at_completion", report)

    def test_reject_allow_empty_commit_with_identical_project_tree(self):
        """A new commit identity is not automatically a changed project."""
        git(self.repo, "-c", "user.name=Fixture",
            "-c", "user.email=fixture@example.test",
            "commit", "--allow-empty", "-qm", "sans contenu différent")
        newer = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", REF, newer)
        with self.assertRaisesRegex(SessionError, "arbre modifié"):
            observe(self.repo, "fiction/laboratoire", "activite.qmd", REF, self.second)
        self.assertFalse((self.home / "alliage-experiences").exists())

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

    def test_p31_partial_clone_missing_blob_refuses_without_lazy_download(self):
        """A real filtered clone must not retrieve a missing blob on P3.1 read."""
        remote = self.home / "fixture-remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        git(self.repo, "remote", "add", "origin", str(remote))
        git(self.repo, "push", "-q", "origin",
            self.second + ":refs/heads/experiment/laboratoire")
        git(remote, "symbolic-ref", "HEAD", "refs/heads/experiment/laboratoire")
        git(remote, "config", "uploadpack.allowFilter", "true")
        partial = self.home / "filtered-clone"
        subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout",
                        remote.as_uri(), str(partial)], check=True)
        blob = git(partial, "rev-parse", self.second + ":activite.qmd")
        git_env = {**os.environ, "GIT_NO_LAZY_FETCH": "1"}
        self.assertNotEqual(
            subprocess.run(["git", "-C", str(partial), "cat-file", "-e", blob],
                           env=git_env, capture_output=True).returncode, 0)
        before = git(partial, "count-objects", "-v")
        trace = self.home / "trace.json"
        with patch.dict(os.environ, {"GIT_NO_LAZY_FETCH": "0",
                                     "GIT_TRACE2_EVENT": str(trace)}):
            with self.assertRaises(PreviewError):
                create_preview(partial, self.second, "activite.qmd",
                               self.home / "missing-blob-output", render=False)
        self.assertFalse((self.home / "missing-blob-output").exists())
        self.assertEqual(before, git(partial, "count-objects", "-v"))
        self.assertNotEqual(
            subprocess.run(["git", "-C", str(partial), "cat-file", "-e", blob],
                           env=git_env, capture_output=True).returncode, 0)
        self.assertFalse(any(json.loads(line).get("event") == "child_start"
                             for line in trace.read_text().splitlines()))

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
        direct = urlsplit(report["resource_url"])
        self.assertTrue(direct.path.endswith("/V2/project/_site/activite.html"))
        self.assertIn("alliage-history-v0", parse_qs(direct.query))
        self.assertEqual(json.loads(parse_qs(direct.query)["alliage-history-v0"][0])["entries"],
                         [{"id":"V1","commit":self.initial},
                          {"id":"V2","commit":self.second}])
        # Real Quarto HTML is still the unmodified output hashed by P3.1.
        observed_manifest = json.loads((session / "V2/manifest.json").read_text())
        observed_html = session / "V2" / observed_manifest["rendered_html"]["path"]
        self.assertEqual(digest(observed_html.read_bytes()),
                         observed_manifest["rendered_html"]["sha256"])


if __name__ == "__main__":
    unittest.main()
