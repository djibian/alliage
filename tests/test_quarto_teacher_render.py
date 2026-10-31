# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.6 private professor render: synthetic Git projects only, no private corpus."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quarto_teacher_render import TeacherRenderError, plan, render, verify_session
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
        (self.repo / SOURCE).write_text(
            "---\ntitle: Laboratoire fictif\n---\n\n# Mission de test\n"
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

    @unittest.skipUnless(os.environ.get("ALLIAGE_TEST_REAL_QUARTO") == "1",
                         "Requires explicit Quarto real test job")
    def test_real_quarto_professor_only_and_student_sentinel(self):
        self.assertIsNotNone(shutil.which("quarto"))
        before = (git(self.repo, "rev-parse", "HEAD"),
                  git(self.repo, "status", "--porcelain"))
        result = render(*self.args(), self.output, trusted_quarto=True)
        self.assertEqual(result["status"], "PROFESSOR_RENDER_OBSERVED_LOCAL_ONLY")
        self.assertTrue(result["teacher_html_verified"])
        self.assertFalse(result["render_profile_effective_verified"])
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["student_deployment_verified"])
        self.assertTrue(result["rendered_html"]["path"].startswith("dist/professeur/"))
        self.assertEqual(verify_session(self.output)["status"],
                         "LOCAL_PROFESSOR_FILES_REHASHED")
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
