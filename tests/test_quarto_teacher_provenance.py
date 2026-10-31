# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.5 read-only canonical teacher source probe; synthetic Git only."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quarto_teacher_provenance import TeacherProvenanceError, probe


SOURCE = "cours/mission/activite.qmd"
ROOT = (
    "project:\n"
    "  type: default\n"
    "  output-dir: dist\n"
    "  render:\n"
    "    - \"cours/**/*.qmd\"\n"
    "  resources:\n"
    "    - \"cours/**/assets/**\"\n"
    "\n"
    "profile:\n"
    "  default: eleve\n"
    "  group:\n"
    "    - [eleve, professeur]\n"
    "\n"
    "format:\n"
    "  html:\n"
    "    embed-resources: true\n"
)


def git(repo, *args):
    return subprocess.check_output(
        ["git", "--no-replace-objects", "-C", str(repo), *args],
        stderr=subprocess.PIPE, text=True).strip()


class TeacherSourceProbeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name) / "fixture"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        (self.repo / "cours/mission").mkdir(parents=True)
        (self.repo / "cours/mission/activite.qmd").write_text(
            "---\ntitle: Fictif\n---\n\n## Consigne\nFictif.\n", encoding="utf-8")
        (self.repo / "_quarto.yml").write_text(ROOT, encoding="utf-8")
        (self.repo / "_quarto-professeur.yml").write_text(
            "project:\n  output-dir: dist/professeur\n", encoding="utf-8")
        (self.repo / "_quarto-eleve.yml").write_text(
            "project:\n  output-dir: dist/eleve\n", encoding="utf-8")
        (self.repo / "styles.css").write_text("h2{color:red}\n", encoding="utf-8")
        self.commit("baseline")
        self.base = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "styles.css").write_text("h2{color:blue}\n", encoding="utf-8")
        self.commit("project CSS only")
        self.current = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", "refs/heads/enseignant", self.current)

    def commit(self, message):
        git(self.repo, "add", "-A")
        git(self.repo, "-c", "user.name=Fixture", "-c",
            "user.email=fixture@example.test", "commit", "-qm", message)

    def inspect(self, **kwargs):
        args = {"repo": self.repo, "repository_id": "fiction/laboratoire",
                "source": SOURCE, "working_ref": "refs/heads/enseignant",
                "expected_sha": self.current}
        args.update(kwargs)
        return probe(**args)

    def test_pinned_source_and_profiles_not_a_published_or_browser_proof(self):
        before = (git(self.repo, "rev-parse", "HEAD"),
                  git(self.repo, "status", "--porcelain=v1"))
        result = self.inspect()
        self.assertEqual(result["working_commit"], self.current)
        self.assertEqual(result["resource_id"],
                         "quarto:fiction/laboratoire:"+SOURCE)
        self.assertEqual(result["working_ref"], "refs/heads/enseignant")
        self.assertEqual(result["status"],
                         "SOURCE_PINNED_PROFILES_DECLARED_RENDER_NOT_VERIFIED")
        self.assertEqual(result["profiles"]["profiles"]["professeur"]["output_dir_declared"],
                         "dist/professeur")
        self.assertEqual(result["profiles"]["profiles"]["eleve"]["output_dir_declared"],
                         "dist/eleve")
        self.assertNotEqual(result["working_tree_git_sha"], "")
        self.assertFalse(result["profile_effective_render_verified"])
        self.assertIsNone(result["checkout_clean_at_observation"])
        self.assertIsNone(result["checkout_head_matches_ref"])
        self.assertFalse(result["teacher_html_url_verified"])
        self.assertFalse(result["published_html_url_verified"])
        self.assertFalse(result["student_deployment_verified"])
        self.assertFalse(result["teacher_content_exposure_authorized"])
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["quarto_executed"])
        self.assertFalse(result["network_access_performed_by_alliage"])
        self.assertEqual(before,(git(self.repo, "rev-parse", "HEAD"),
                                 git(self.repo, "status", "--porcelain=v1")))
        self.assertEqual(sorted(p.name for p in self.repo.iterdir()),
                         [".git", "_quarto-eleve.yml", "_quarto-professeur.yml",
                          "_quarto.yml", "cours", "styles.css"])

    def test_css_only_commit_changes_project_identity_not_source(self):
        newer = self.inspect()
        # The source is unchanged, but the Git tree changed at the second commit.
        git(self.repo, "update-ref", "refs/heads/ancien", self.base)
        older = self.inspect(working_ref="refs/heads/ancien", expected_sha=self.base)
        self.assertEqual(newer["source_git_blob"],older["source_git_blob"])
        self.assertEqual(newer["source_sha256"],older["source_sha256"])
        self.assertNotEqual(newer["working_commit"],older["working_commit"])
        self.assertNotEqual(newer["working_tree_git_sha"],older["working_tree_git_sha"])

    def test_moving_ref_or_unresolvable_sha_is_rejected(self):
        with self.assertRaisesRegex(TeacherProvenanceError,"SHA différent"):
            self.inspect(expected_sha=self.base)
        with self.assertRaises(TeacherProvenanceError):
            self.inspect(expected_sha="g"*40)
        with self.assertRaises(TeacherProvenanceError):
            self.inspect(working_ref="HEAD")

    def test_dirty_checkout_cannot_be_treated_as_verified_page(self):
        (self.repo / SOURCE).write_text("MODIFIÉ ET NON ENREGISTRÉ",encoding="utf-8")
        result = self.inspect()
        self.assertIsNone(result["checkout_clean_at_observation"])
        self.assertIsNone(result["checkout_head_matches_ref"])
        self.assertFalse(result["checkout_bytes_verified"])
        self.assertFalse(result["teacher_html_url_verified"])
        self.assertEqual((self.repo / SOURCE).read_text(encoding="utf-8"),
                         "MODIFIÉ ET NON ENREGISTRÉ")

    def test_altered_profile_is_never_silently_interpreted(self):
        (self.repo / "_quarto-professeur.yml").write_text(
            "project:\n  output-dir: dist/eleve\n",encoding="utf-8")
        self.commit("wrong teacher projection")
        git(self.repo, "update-ref", "refs/heads/enseignant",
            git(self.repo, "rev-parse", "HEAD"))
        with self.assertRaisesRegex(TeacherProvenanceError,"professeur non reconnu"):
            self.inspect(expected_sha=git(self.repo, "rev-parse", "HEAD"))

    def test_yaml_profile_override_or_missing_profile_fails_closed(self):
        for content in (
            "project:\n  output-dir: dist/professeur\nextra: true\n",
            "project:\n  output-dir: dist/professeur/../../eleve\n",
            "project:\n  output-dir: dist/professeur\n\nprofile:\n  default: professeur\n"
        ):
            with self.subTest(content=content):
                (self.repo / "_quarto-professeur.yml").write_text(content)
                self.commit("profile drift")
                latest = git(self.repo, "rev-parse", "HEAD")
                git(self.repo, "update-ref", "refs/heads/enseignant", latest)
                with self.assertRaises(TeacherProvenanceError):
                    self.inspect(expected_sha=latest)

    def test_missing_and_symlink_profiles_fail_closed(self):
        (self.repo / "_quarto-professeur.yml").unlink()
        self.commit("missing professor profile")
        latest = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", "refs/heads/enseignant", latest)
        with self.assertRaises(TeacherProvenanceError):
            self.inspect(expected_sha=latest)
        (self.repo / "_quarto-professeur.yml").symlink_to("_quarto-eleve.yml")
        self.commit("symlink professor profile")
        latest = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", "refs/heads/enseignant", latest)
        with self.assertRaises(TeacherProvenanceError):
            self.inspect(expected_sha=latest)

    def test_invalid_source_and_repository_are_rejected(self):
        for source in ("../activite.qmd", "/tmp/activite.qmd",
                       "cours/../../activite.qmd", "cours/mission/activite.html"):
            with self.assertRaises(TeacherProvenanceError):
                self.inspect(source=source)
        for repository_id in ("../lab", "fiction/laboratoire/private", "bad:repo"):
            with self.assertRaises(TeacherProvenanceError):
                self.inspect(repository_id=repository_id)


    def test_reject_root_yaml_ambiguities_b1(self):
        """B1: every auditor counterexample must refuse a positive probe."""
        cases = {
            "duplicate profile default": ROOT.replace(
                "    - [eleve, professeur]\n",
                "    - [eleve, professeur]\n  default: professeur\n"),
            "duplicate project output": ROOT.replace(
                "  output-dir: dist\n",
                "  output-dir: dist\n  output-dir: dist/eleve\n"),
            "compact conflicting project": ROOT + "\nproject: {output-dir: dist/eleve}\n",
            "compact conflicting profile": ROOT + "\nprofile: {default: professeur}\n",
            "additional profile group": ROOT.replace(
                "    - [eleve, professeur]\n",
                "    - [eleve, professeur]\n    - [public, interne]\n"),
            "additional profile key": ROOT.replace(
                "    - [eleve, professeur]\n",
                "    - [eleve, professeur]\n  extra: allowed\n"),
            "second profile block": ROOT + "\nprofile:\n  default: professeur\n",
            "yaml document boundary": ROOT + "\n---\nprofile: {default: professeur}\n",
            "invalid yaml syntax": ROOT + "\nthis line lacks a colon\n",
            "profile anchor": ROOT.replace(
                "profile:\n", "profile: &profileAnchor\n"),
            "alias in profile group": ROOT.replace(
                "    - [eleve, professeur]\n", "    - *profileAnchor\n"),
            "alias after a key": ROOT.replace(
                "  default: eleve\n", "  default: &choice eleve\n"),
            "merge key": ROOT.replace(
                "  group:\n", "  <<: *profileAnchor\n  group:\n"),
            "duplicate project type": ROOT.replace(
                "  type: default\n", "  type: default\n  type: default\n"),
            "project additional output": ROOT.replace(
                '    - "cours/**/*.qmd"\n',
                '    - "cours/**/*.qmd"\n    - "secret/other.qmd"\n'),
            "unknown top-level option": ROOT + "\nunknown: {default: professeur}\n",
            "unexpected format map": ROOT + "\nformat: {html: {toc: false}}\n",
            "unterminated quoted glob": ROOT.replace(
                '    - "cours/**/*.qmd"\n',
                '    - "cours/**/*.qmd\n'),
            "block scalar": ROOT.replace(
                "  default: eleve\n", "  default: |\n    professeur\n"),
            "duplicate format option": ROOT.replace(
                "    embed-resources: true\n",
                "    embed-resources: true\n    embed-resources: false\n"),
            "invalid indentation": ROOT.replace(
                "    - [eleve, professeur]\n", "   - [eleve, professeur]\n"),
            "tabs": ROOT.replace("  default: eleve\n", "\tdefault: eleve\n"),
            "CRLF": ROOT.replace("\n", "\r\n"),
            "YAML directive": "%YAML 1.2\n---\n" + ROOT,
            "unknown top-level profile variant": ROOT + "\nprofile.default: professeur\n",
        }
        for label, root in cases.items():
            with self.subTest(case=label):
                (self.repo / "_quarto.yml").write_text(root, encoding="utf-8")
                self.commit("adversarial root fixture")
                latest = git(self.repo, "rev-parse", "HEAD")
                git(self.repo, "update-ref", "refs/heads/enseignant", latest)
                with self.assertRaises(TeacherProvenanceError):
                    self.inspect(expected_sha=latest)
        # Exact validated reference still succeeds after all negative cases.
        (self.repo / "_quarto.yml").write_text(ROOT, encoding="utf-8")
        self.commit("restore recognized root config")
        latest = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", "refs/heads/enseignant", latest)
        self.assertEqual(
            self.inspect(expected_sha=latest)["status"],
            "SOURCE_PINNED_PROFILES_DECLARED_RENDER_NOT_VERIFIED")

    def test_realistic_multiprofile_project_shape_remains_recognized(self):
        """Recognize actual Quarto *shape*, using only fictional paths."""
        project = ROOT + (
            "lang: fr\n"
            "\n"
            "format:\n"
            "  html:\n"
            "    toc: false\n"
            "    embed-resources: true\n"
            "    page-layout: full\n"
            "    format-links: false\n"
            "    css: publication/tim.css\n"
            "  odt:\n"
            "    toc: false\n"
            "    page-width: 7\n"
            "    reference-doc: publication/sample.odt\n"
            "    filters:\n"
            "      - publication/filter.lua\n"
        )
        # ROOT already declares a format; move its one HTML option into the
        # realistic shape instead of duplicating the root mapping.
        project = project.replace(
            "format:\n  html:\n    embed-resources: true\n", "")
        (self.repo / "_quarto.yml").write_text(project, encoding="utf-8")
        self.commit("multiprofile Quarto project shape")
        latest = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "update-ref", "refs/heads/enseignant", latest)
        result = self.inspect(expected_sha=latest)
        self.assertTrue(result["profiles"]["declarations_recognized_not_effective_render_verified"])
        self.assertFalse(result["profile_effective_render_verified"])


if __name__=="__main__":
    unittest.main()
