# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiment import (prepare, css_target, parse_html, canonical_text, text_in_html, RenderError)
from resolve_source import LocalizationError

REL = "enseignements/tim/4e-3e/activites/3e/02-nommer-classer/activite.qmd"
QMD = '''---
title: "Test"
---

::: {.action}
## 1 — Je prépare les cinq ressources

Ouvre `AtelierDemo`, puis crée le dossier.

Place les cinq fichiers dans le répertoire `AtelierDemo` pour cet exercice :
:::

::: {.verification}
## Validation

- [ ] Les cinq fichiers sont rangés dans `AtelierDemo > docs`.
:::
'''


def git(path, *args):
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def fake_quarto(root, source):
    text = (root / source).read_text(encoding="utf-8")
    # Simulated Quarto HTML for the exact DOM scopes used by real selections.
    a = next(line for line in text.splitlines() if line.startswith("Place "))
    a = a.replace("`", "")
    b = next(line for line in text.splitlines() if line.startswith("- [ ] Les "))[6:].replace("`", "")
    html = f'''<!doctype html><html><body><main>
    <section id="je-prépare-les-cinq-ressources"><h2>1 — Je prépare les cinq ressources</h2><p>Ouvre TIM</p><p>{a}</p></section>
    <section id="validation"><h2>Validation</h2><ul><li>{b}</li></ul></section>
    </main></body></html>'''
    out = root / "dist" / "eleve" / Path(source).with_suffix(".html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        path = self.repo / REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(QMD, encoding="utf-8")
        (self.repo / "_quarto.yml").write_text("project:\n  type: default\n", encoding="utf-8")
        (self.repo / "_quarto-eleve.yml").write_text("project:\n  output-dir: dist/eleve\n", encoding="utf-8")
        css = self.repo / "publication/quarto/tim.css"
        css.parent.mkdir(parents=True,exist_ok=True)
        css.write_text("body {font-family: sans-serif}",encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.name=Demo", "-c", "user.email=demo@example.test", "commit", "-qm", "fixture")
        self.a = json.loads((ROOT / "exemples/selection-1.json").read_text(encoding="utf-8"))
        self.b = json.loads((ROOT / "exemples/selection-2.json").read_text(encoding="utf-8"))
        self.out = self.root / "experiment"

    def test_output_two_variants_renders_and_original_untouched(self):
        with patch("experiment.run_quarto", side_effect=fake_quarto), patch("experiment.shutil.which", return_value="/usr/bin/quarto"):
            report = prepare(self.repo, self.out, self.a,
                             ["A=cinq ressources", "B=cinq fichiers proposés"],
                             [ROOT / "exemples/selection-2.json"], None, True)
        self.assertEqual(report["status"], "RENDER_VERIFIED_LOCAL")
        self.assertFalse(report["production_write"])
        self.assertFalse(report["provenance"]["published_html_revision_verified"])
        self.assertEqual(len(report["options"]), 2)
        self.assertTrue(all(v["render_verified"] for v in report["options"]))
        self.assertEqual((self.repo / REL).read_text(encoding="utf-8"), QMD)
        self.assertEqual(subprocess.check_output(["git", "-C", str(self.repo), "status", "--porcelain"], text=True), "")
        self.assertIn("Place les cinq ressources", (self.out / REL.replace(REL, report["options"][0]["qmd"])).read_text(encoding="utf-8"))
        self.assertIn("- [ ] Les cinq fichiers sont rangés dans", (self.out / report["options"][0]["qmd"]).read_text(encoding="utf-8"))
        self.assertTrue((self.out / report["options"][1]["html"]).is_file())

    def test_fail_duplicate_output(self):
        self.out.mkdir()
        with self.assertRaises(LocalizationError) as ctx:
            prepare(self.repo, self.out, self.a, ["A=cinq ressources"], [], None, False)
        self.assertEqual(ctx.exception.reason, "OUTPUT_EXISTS")

    def test_fail_dirty_repo(self):
        (self.repo / "temp.txt").write_text("change", encoding="utf-8")
        with self.assertRaises(LocalizationError) as ctx:
            prepare(self.repo, self.out, self.a, ["A=cinq ressources"], [], None, False)
        self.assertEqual(ctx.exception.reason, "DIRTY_REPOSITORY")

    def test_fail_bad_proposal(self):
        with self.assertRaises(LocalizationError) as ctx:
            prepare(self.repo, self.out, self.a, ["A=cinq **ressources**"], [], None, False)
        self.assertEqual(ctx.exception.reason, "INVALID_OPTION")

    def test_fail_overlap_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = Path(tmp) / "guard.json"
            g.write_text(json.dumps(self.a), encoding="utf-8")
            with self.assertRaises(LocalizationError) as ctx:
                prepare(self.repo, self.out, self.a, ["A=cinq ressources"], [g], None, False)
            self.assertEqual(ctx.exception.reason, "GUARD_OVERLAP")

    def test_fail_render_other_text_changed(self):
        def bad_render(root, source):
            result = fake_quarto(root, source)
            if root.name == "A":
                result.write_text(result.read_text(encoding="utf-8").replace("Ouvre TIM", "Change TIM"), encoding="utf-8")
            return result
        with patch("experiment.run_quarto", side_effect=bad_render), patch("experiment.shutil.which", return_value="/usr/bin/quarto"):
            with self.assertRaises(RenderError):
                prepare(self.repo, self.out, self.a, ["A=cinq ressources"], [], None, True)
        self.assertFalse(self.out.exists())

    def test_css_exact(self):
        page = parse_html('<main><section id="validation"><ul><li>Les <strong>cinq fichiers</strong> sont là.</li></ul></section></main>')
        self.assertEqual(css_target(page, "#validation > ul > li:nth-of-type(1)").all_text(), "Les cinq fichiers sont là.")
        with self.assertRaises(RenderError):
            css_target(page, "#validation > ul > li:nth-of-type(2)")


if __name__ == "__main__":
    unittest.main()
