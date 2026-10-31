# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.6 private professor render: synthetic Git projects only, no private corpus."""
from __future__ import annotations

import os
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quarto_teacher_render import (
    TeacherRenderError, plan, render, verify_session,
    _validate_qmd_frontmatter, _verify_tracked_copy,
    _expected_quarto_gitignore,
)
from quarto_teacher_provenance import TeacherProvenanceError

SOURCE = "cours/mission/activite.qmd"
TEACHER_ONLY = "FICTIONAL_TEACHER_MARKER_2026_NOT_A_CORRECTION"
STUDENT_ONLY = "FICTIONAL_STUDENT_MARKER_2026_NOT_AN_ANSWER"
CONFIG = (
    'project:\n'
    '  type: default\n'
    '  output-dir: dist\n'
    '  render:\n'
    '    - "cours/**/*.qmd"\n'
    '  resources:\n'
    '    - "cours/**/assets/**"\n'
    '\n'
    'profile:\n'
    '  default: eleve\n'
    '  group:\n'
    '    - [eleve, professeur]\n'
    '\n'
    'lang: fr\n'
    'format:\n'
    '  html:\n'
    '    toc: false\n'
    '    embed-resources: true\n'
    '    page-layout: full\n'
    '    format-links: false\n'
    '    css: publication/tim.css\n'
)


def git(repo, *args):
    return subprocess.check_output(
        ["git", "--no-replace-objects", "-C", str(repo), *args],
        text=True, stderr=subprocess.PIPE).strip()


class TeacherRenderTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.repo = self.home / "git-src"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        (self.repo / "cours/mission/assets").mkdir(parents=True)
        (self.repo / "publication").mkdir()
        (self.repo / "_quarto.yml").write_text(CONFIG, encoding="utf-8")
        (self.repo / "_quarto-professeur.yml").write_text(
            "project:\n  output-dir: dist/professeur\n", encoding="utf-8")
        (self.repo / "_quarto-eleve.yml").write_text(
            "project:\n  output-dir: dist/eleve\n", encoding="utf-8")
        (self.repo / "publication/tim.css").write_text(
            "h2 { color: rebeccapurple; }\n", encoding="utf-8")
        # Every real Quarto 1.10.x render must exercise its deterministic
        # .gitignore housekeeping against a tracked fictitious input file.
        (self.repo / ".gitignore").write_text(
            "# Fictitious Git ignores\ndist/\n", encoding="utf-8")
        (self.repo / SOURCE).write_text(
            '---\ntitle: "Laboratoire fictif"\n---\n\n# Mission de test\n'
            "Texte commun.\n\n"
            '::: {.content-visible when-profile="professeur"}\n'
            + TEACHER_ONLY + "\n:::\n\n"
            '::: {.content-hidden when-profile="professeur"}\n'
            + STUDENT_ONLY + "\n:::\n",
            encoding="utf-8")
        (self.repo / "cours/mission/autre.qmd").write_text(
            "# Autre activité fictive (ne doit pas être rendue)\n",
            encoding="utf-8")
        (self.repo / "cours/mission/assets/asset.txt").write_text(
            "ressource fictive\n", encoding="utf-8")
        self.commit("source and professor/learner profiles")
        self.sha = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", "refs/heads/professeur", self.sha)
        self.output = self.home / "private-result"

    def commit(self, message):
        git(self.repo, "add", "-A")
        git(self.repo, "-c", "user.name=Fixture", "-c",
            "user.email=fiction@example.test", "commit", "-qm", message)

    def args(self):
        return (self.repo, "fiction/laboratoire", SOURCE, "refs/heads/professeur", self.sha)

    def test_integrity_failure_default_does_not_expose_private_paths(self):
        """Routine refuses a changed Git blob without leaking a path."""
        project = self.home / "private-project"
        path = project / "private/illustrative-input.css"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"original")
        expected = {"private/illustrative-input.css":
                    hashlib.sha256(b"original").hexdigest()}
        _verify_tracked_copy(project, expected)
        path.write_bytes(b"replaced")
        with self.assertRaises(TeacherRenderError) as caught:
            _verify_tracked_copy(project, expected)
        self.assertEqual(str(caught.exception),
                         "Fichier Git suivi modifié par Quarto.")
        self.assertNotIn("illustrative-input", str(caught.exception))
        with self.assertRaises(TeacherRenderError) as diagnosed:
            _verify_tracked_copy(project, expected, diagnose_integrity=True)
        self.assertIn('"kind": "CONTENT_CHANGED"', str(diagnosed.exception))
        self.assertIn('"count": 1', str(diagnosed.exception))
        self.assertIn('"path": "private/illustrative-input.css"',
                      str(diagnosed.exception))
        self.assertIn(hashlib.sha256(b"replaced").hexdigest(),
                      str(diagnosed.exception))
        self.assertNotIn("replaced", str(diagnosed.exception))

    def test_integrity_diagnostic_keeps_missing_and_symlink_refused(self):
        project = self.home / "private-project"
        project.mkdir()
        target = project / "fiction.txt"
        expected = {"fiction.txt": hashlib.sha256(b"original").hexdigest()}
        with self.assertRaisesRegex(TeacherRenderError, "MISSING_OR_NONREGULAR"):
            _verify_tracked_copy(project, expected, diagnose_integrity=True)
        target.symlink_to(self.repo / "_quarto.yml")
        with self.assertRaisesRegex(TeacherRenderError, "SYMLINK"):
            _verify_tracked_copy(project, expected, diagnose_integrity=True)

    def test_quarto_gitignore_exact_delta_allowed_and_recorded(self):
        """Recognize Quarto's byte-exact housekeeping, not an exemption."""
        project = self.home / "snap"
        project.mkdir()
        original = b"# Synthetic\ndist/\n"
        initial_sha = hashlib.sha256(original).hexdigest()
        expected = _expected_quarto_gitignore(original)
        self.assertEqual(
            expected,
            original + b"\n/.quarto/\n**/*.quarto_ipynb\n",
        )
        self.assertNotEqual(expected, original)
        path = project / ".gitignore"
        path.write_bytes(expected)
        mutation = _verify_tracked_copy(
            project, {".gitignore": initial_sha}, original_gitignore=original)
        self.assertEqual(len(mutation), 1)
        self.assertEqual(mutation[0]["path"], ".gitignore")
        self.assertEqual(mutation[0]["source_sha256"], initial_sha)
        self.assertEqual(
            mutation[0]["render_copy_sha256"],
            hashlib.sha256(expected).hexdigest(),
        )
        self.assertIs(mutation[0]["source_bytes_preserved"], False)
        # Without the *original bytes*, no exception to integrity is possible.
        with self.assertRaises(TeacherRenderError):
            _verify_tracked_copy(project, {".gitignore": initial_sha})

    def test_quarto_gitignore_unexpected_change_still_refused(self):
        project = self.home / "snap"
        project.mkdir()
        original = b"# Synthetic\ndist/\n"
        expected = {".gitignore": hashlib.sha256(original).hexdigest()}
        target = project / ".gitignore"
        # Correct Quarto additions PLUS one injected line must be rejected.
        target.write_bytes(_expected_quarto_gitignore(original) + b"secret/\n")
        with self.assertRaises(TeacherRenderError):
            _verify_tracked_copy(project, expected, original_gitignore=original)
        target.write_bytes(original)
        self.assertEqual(_verify_tracked_copy(
            project, expected, original_gitignore=original), [])
        # Already-complete ignore files must remain byte-for-byte unchanged.
        already = _expected_quarto_gitignore(original)
        target.write_bytes(already + b"\n")
        with self.assertRaises(TeacherRenderError):
            _verify_tracked_copy(
                project, {".gitignore": hashlib.sha256(already).hexdigest()},
                original_gitignore=already)
        self.assertEqual(_expected_quarto_gitignore(already), already)

    def test_plan_never_executes_quarto_or_writes_source(self):
        before = (git(self.repo, "rev-parse", "HEAD"),
                  git(self.repo, "status", "--porcelain"))
        result = plan(*self.args())
        self.assertEqual(result["commit"], self.sha)
        self.assertEqual(result["status"], "PINNED_SOURCE_AND_PROFILES_DECLARED_RENDER_NOT_RUN")
        self.assertEqual(result["render_profile_requested"], "professeur")
        self.assertFalse(result["quarto_executed"])
        self.assertFalse(result["teacher_html_verified"])
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["student_deployment_verified"])
        self.assertFalse(self.output.exists())
        self.assertEqual(before,(git(self.repo, "rev-parse", "HEAD"),
                                 git(self.repo, "status", "--porcelain")))

    def test_refuses_render_without_explicit_consent(self):
        with self.assertRaises(TeacherRenderError):
            render(*self.args(), self.output)
        self.assertFalse(self.output.exists())

    def test_reject_output_inside_repo(self):
        with patch("quarto_teacher_render.shutil.which", return_value="/fake/quarto"):
            with self.assertRaises(TeacherRenderError):
                render(*self.args(), self.repo / "dist-preview", trusted_quarto=True)

    def test_moving_ref_is_refused(self):
        git(self.repo, "update-ref", "refs/heads/professeur", self.sha)
        with self.assertRaises(TeacherProvenanceError):
            # Bad SHA never considered valid provenance.
            plan(self.repo, "fiction/laboratoire", SOURCE, "refs/heads/professeur", "a" * 40)

    def test_unrecognized_quarto_layer_and_generated_output_refused(self):
        for name in ("_quarto-extra.yml", "cours/_metadata.yml",
                     "cours/mission/_quarto.yml", "_environment", "dist/eleve/private.html"):
            with self.subTest(name=name):
                path = self.repo / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("dummy\n", encoding="utf-8")
                self.commit("adversarial extra layer")
                latest = git(self.repo, "rev-parse", "HEAD")
                git(self.repo, "update-ref", "refs/heads/professeur", latest)
                with self.assertRaises(TeacherRenderError):
                    plan(self.repo, "fiction/laboratoire", SOURCE,
                         "refs/heads/professeur", latest)
                path.unlink()
                self.commit("remove adverse layer")

    def test_reject_document_level_filter_or_script_metadata(self):
        base = (self.repo / SOURCE).read_text(encoding="utf-8")
        for insert in ("filters:\n  - arbitrary.lua\n", "execute: true\n",
                       "include-in-header: leak.html\n", "format:\n  html: default\n"):
            with self.subTest(insert=insert):
                (self.repo / SOURCE).write_text(base.replace(
                    "---\ntitle:", "---\n" + insert + "title:"), encoding="utf-8")
                self.commit("malicious fixture")
                latest = git(self.repo, "rev-parse", "HEAD")
                git(self.repo, "update-ref", "refs/heads/professeur", latest)
                with self.assertRaises(TeacherRenderError):
                    plan(self.repo, "fiction/laboratoire", SOURCE,
                         "refs/heads/professeur", latest)
        (self.repo / SOURCE).write_text(base, encoding="utf-8")

    def test_B1_quoted_keys_crlf_nested_yaml_and_aliases_refused(self):
        """Actual frontmatter bypasses from the independent P3.6A audit."""
        base = (self.repo / SOURCE).read_text(encoding="utf-8")
        scenarios = {
            "quoted filters double": 'title: "Fiction"\n"filters":\n  - demonstration.lua',
            "quoted filters single": "title: 'Fiction'\n'filters':\n  - demonstration.lua",
            "ordinary filters": "title: 'Fiction'\nfilters:\n  - demonstration.lua",
            "CRLF executable header": 'title: "Fiction"\r\nfilters:\r\n  - demonstration.lua',
            "CRLF benign header": 'title: "Fiction"\r\nsubtitle: "Notes fictives"',
            "BOM prefix": "\ufeff---\ntitle: Fiction",
            "duplicate title": 'title: "Fiction"\ntitle: "Malice"',
            "alias": 'title: &title_anchor "Fiction"',
            "composed map": 'title: "Fiction"\n<<: *alias',
            "multiline": 'title: |\n  Fiction',
            "unknown key": 'title: "Fiction"\nfilters-v2: demonstration.lua',
            "quoted project key": '"project": {pre-render: demonstration.lua}',
            "quoted execute key": '"execute": true',
            "script key": "pre-render: demonstration.sh",
            "nested metadata": "title: 'Fiction'\nformat:\n  html: default",
            "invalid YAML": "title: [a,",
            "implicit typed title": "title: true",
            "missing frontmatter": "# Fictif\n",
        }
        for label, meta in scenarios.items():
            with self.subTest(case=label):
                if label == "missing frontmatter":
                    source_bytes = meta.encode("utf-8")
                elif label == "BOM prefix":
                    source_bytes = (meta + "\n---\nFictif.\n").encode("utf-8")
                else:
                    source_bytes = ("---\n" + meta + "\n---\nFictif.\n").encode("utf-8")
                with self.assertRaises(TeacherRenderError):
                    _validate_qmd_frontmatter(source_bytes)
        # The previously qualified fictitious valid single-title fixture must pass.
        _validate_qmd_frontmatter(base.encode("utf-8"))

    def test_B1_realistic_safe_qmd_metadata_still_recognized(self):
        """Real-world metadata *shape*, entirely fictional values."""
        qmd = (
            "---\n"
            'title: "Activité fictive : gestion de fichiers"\n'
            "subtitle: 'Exercice fictif'\n"
            "activity-id: TIM-FAKE-02\n"
            "activity-order: 2\n"
            "curriculum-unit: U12\n"
            "publication-status: preparation\n"
            "duration: 55 min\n"
            'official-refs: ["REF-A", "REF-B"]\n'
            "concepts: [organisation, repertoires]\n"
            "support-level: simulation\n"
            "---\n\n# Fictif\n"
        )
        _validate_qmd_frontmatter(qmd.encode("utf-8"))

    def _fake_session(self):
        """Minimal internally consistent fictitious session: no Quarto required."""
        path = self.home / "session"
        project = path / "project"
        folder = project / "dist/professeur/cours/mission"
        folder.mkdir(parents=True)
        html = folder / "activite.html"
        asset = folder / "asset.txt"
        html.write_text("<html><body>Fictif</body></html>\n", encoding="utf-8")
        asset.write_text("Actif fictif\n", encoding="utf-8")
        files = []
        for file in (html, asset):
            data = file.read_bytes()
            files.append({"path": file.relative_to(project).as_posix(),
                          "bytes": len(data),
                          "sha256": hashlib.sha256(data).hexdigest()})
        files.sort(key=lambda item: item["path"])
        html_entry = next(f for f in files if f["path"].endswith(".html"))
        manifest = {
            "schema": "alliage.quarto-professor-render.v0",
            "source_path": SOURCE,
            "rendered_files": files,
            "rendered_html": html_entry,
            "publication_performed": False,
            "student_deployment_verified": False,
        }
        (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return path, manifest

    def test_B2_symlink_intermediate_dist_is_rejected_even_with_valid_hashes(self):
        """Audit B2: hashes alone cannot authorize external physical files."""
        path, _ = self._fake_session()
        self.assertEqual(verify_session(path)["status"],
                         "LOCAL_PROFESSOR_FILES_REHASHED")
        dist = path / "project/dist"
        outside = self.home / "external-output"
        dist.rename(outside)
        dist.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(TeacherRenderError):
            verify_session(path)

    def test_B2_symlink_project_is_rejected(self):
        path, _ = self._fake_session()
        project = path / "project"
        outside = self.home / "external-project"
        project.rename(outside)
        project.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(TeacherRenderError):
            verify_session(path)

    def test_B3_manifest_cannot_designate_asset_as_html(self):
        path, manifest = self._fake_session()
        self.assertEqual(verify_session(path)["status"],
                         "LOCAL_PROFESSOR_FILES_REHASHED")
        manifest["rendered_html"] = next(
            file for file in manifest["rendered_files"]
            if file["path"].endswith(".txt"))
        (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(TeacherRenderError):
            verify_session(path)

    def test_B3_manifest_cannot_change_source_or_html_identity(self):
        for source in ("../hijack.qmd", "cours/autre.qmd", SOURCE + "/../fake.qmd"):
            with self.subTest(source=source):
                path, manifest = self._fake_session()
                manifest["source_path"] = source
                (path / "manifest.json").write_text(json.dumps(manifest),
                                                     encoding="utf-8")
                with self.assertRaises(TeacherRenderError):
                    verify_session(path)
                shutil.rmtree(path)

    @unittest.skipUnless(os.environ.get("ALLIAGE_TEST_REAL_QUARTO") == "1",
                         "Requires explicit Quarto real test job")
    def test_B1_real_quarto_recognizes_quoted_filters_and_crlf(self):
        """Prove a fictional Lua filter can actually run despite --no-execute."""
        self.assertIsNotNone(shutil.which("quarto"))
        sentinel = "FICTIONAL_LUA_FILTER_WAS_EXECUTED_IN_QUARTO"
        for mode in ("quoted", "crlf"):
            with self.subTest(mode=mode):
                project = self.home / ("quarto-" + mode)
                shutil.copytree(self.repo, project,
                                ignore=shutil.ignore_patterns(".git"))
                # Quarto resolves a frontmatter filter path from its QMD directory.
                (project / "cours/mission/audit-filter.lua").write_text(
                    'function Pandoc(doc)\n'
                    '  return pandoc.Pandoc({pandoc.Para("'
                    + sentinel + '")}, doc.meta)\n'
                    'end\n',
                    encoding="utf-8")
                title = 'title: "Fiction"\n'
                head = ('"filters":\n' if mode == "quoted" else 'filters:\n')
                qmd = "---\n" + title + head + "  - audit-filter.lua\n---\n\n# Test fictif\n"
                if mode == "crlf":
                    qmd = qmd.replace("\n", "\r\n")
                (project / SOURCE).write_bytes(qmd.encode("utf-8"))
                with self.assertRaises(TeacherRenderError):
                    _validate_qmd_frontmatter(qmd.encode("utf-8"))
                cmd = ["quarto", "render", SOURCE, "--to", "html",
                       "--profile", "professeur", "--no-execute"]
                env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                       "HOME": str(self.home), "QUARTO_PROFILE": "professeur",
                       "LANG": "C.UTF-8"}
                result = subprocess.run(cmd, cwd=project, env=env,
                                        capture_output=True, timeout=180)
                self.assertEqual(
                    result.returncode, 0,
                    "Échec Quarto fixture fictive : "
                    + (result.stdout + result.stderr).decode("utf-8", "replace")[-1400:])
                html_path = project / "dist/professeur" / Path(SOURCE).with_suffix(".html")
                self.assertTrue(html_path.is_file())
                self.assertIn(sentinel, html_path.read_text(encoding="utf-8"))

    @unittest.skipUnless(os.environ.get("ALLIAGE_TEST_REAL_QUARTO") == "1",
                         "Requires explicit Quarto real test job")
    def test_real_quarto_professor_only_and_student_sentinel(self):
        self.assertIsNotNone(shutil.which("quarto"))
        before = (git(self.repo, "rev-parse", "HEAD"),
                  git(self.repo, "status", "--porcelain"))
        result = render(*self.args(), self.output, trusted_quarto=True)
        self.assertEqual(result["status"], "PROFESSOR_RENDER_OBSERVED_LOCAL_ONLY")
        self.assertFalse(result["tracked_source_bytes_all_preserved"])
        self.assertEqual(len(result["tracked_source_mutations_accepted"]), 1)
        self.assertEqual(
            result["tracked_source_mutations_accepted"][0]["path"],
            ".gitignore")

        self.assertTrue(result["teacher_html_verified"])
        self.assertFalse(result["render_profile_effective_verified"])
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["student_deployment_verified"])
        self.assertTrue(result["rendered_html"]["path"].startswith("dist/professeur/"))
        self.assertEqual(verify_session(self.output)["status"],
                         "LOCAL_PROFESSOR_FILES_REHASHED")
        # The source Git checkout stays unchanged; the temporary project's
        # tracked .gitignore may only carry the exact audited housekeeping.
        source_ignore = (self.repo / ".gitignore").read_bytes()
        copy_ignore = (self.output / "project" / ".gitignore").read_bytes()
        self.assertEqual(copy_ignore, _expected_quarto_gitignore(source_ignore))

        html_path = self.output / "project" / result["rendered_html"]["path"]
        html = html_path.read_text(encoding="utf-8")
        self.assertIn(TEACHER_ONLY, html)
        self.assertNotIn(STUDENT_ONLY, html)
        self.assertFalse((self.output / "project/dist/eleve").exists())
        self.assertEqual(before, (git(self.repo, "rev-parse", "HEAD"),
                                  git(self.repo, "status", "--porcelain")))
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        # embed-resources: true may inline CSS, not create an extra CSS file.
        self.assertGreater(len(html), 200)
        # Distinct learner render on another *fictional* worktree, not served
        # and not published; its bytes must not contain teacher-only sentinel.
        learner_project = self.home / "fictional-learner-only"
        shutil.copytree(self.repo, learner_project,
                        ignore=shutil.ignore_patterns(".git"))
        command = ["quarto", "render", SOURCE, "--to", "html",
                   "--profile", "eleve", "--no-execute"]
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
               "HOME": str(self.home), "QUARTO_PROFILE": "eleve",
               "LANG": "C.UTF-8"}
        call = subprocess.run(command, cwd=learner_project, env=env,
                              capture_output=True, timeout=180)
        self.assertEqual(call.returncode, 0, "Fictional learner render failed")
        learner_html = learner_project / "dist/eleve" / Path(SOURCE).with_suffix(".html")
        self.assertTrue(learner_html.is_file())
        rendered = learner_html.read_text(encoding="utf-8")
        self.assertNotIn(TEACHER_ONLY, rendered)
        self.assertIn(STUDENT_ONLY, rendered)

    @unittest.skipUnless(os.environ.get("ALLIAGE_TEST_REAL_QUARTO") == "1",
                         "Requires explicit Quarto real test job")
    def test_same_size_html_tampering_is_detected(self):
        self.assertIsNotNone(shutil.which("quarto"))
        result = render(*self.args(), self.output, trusted_quarto=True)
        target = self.output / "project" / result["rendered_html"]["path"]
        data = target.read_bytes()
        target.write_bytes(b"x" * len(data))
        with self.assertRaises(TeacherRenderError):
            verify_session(self.output)


if __name__=="__main__":
    unittest.main()
