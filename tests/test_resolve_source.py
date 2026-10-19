import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from resolve_source import locate, LocalizationError

RELATIVE = "enseignements/tim/4e-3e/activites/3e/02-nommer-classer/activite.qmd"
SAMPLE_SOURCE = '''---
title: "Essai fictif Alliage"
---

::: {.action}
## 1 — Je prépare les cinq ressources

Place les cinq fichiers dans le répertoire `AtelierDemo` pour cet exercice :
:::

::: {.verification}
## Validation

- [ ] Les cinq fichiers sont rangés dans `AtelierDemo > docs`.
:::
'''


def git(path, *args):
    proc = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, check=True)
    return proc.stdout.strip()


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)
        git(self.repo, "init", "-q")
        self.file = self.repo / RELATIVE
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(SAMPLE_SOURCE, encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.name=Demo", "-c", "user.email=demo@example.test", "commit", "-qm", "fixture")
        self.first = json.loads((ROOT / "exemples/selection-1.json").read_text(encoding="utf-8"))
        self.second = json.loads((ROOT / "exemples/selection-2.json").read_text(encoding="utf-8"))

    def test_two_identical_quotes_different_source_locations(self):
        a = locate(self.repo, RELATIVE, self.first)
        b = locate(self.repo, RELATIVE, self.second)
        self.assertEqual(a["status"], "LOCATED_READ_ONLY")
        self.assertEqual(b["status"], "LOCATED_READ_ONLY")
        self.assertNotEqual(a["source"]["start_utf8"], b["source"]["start_utf8"])
        self.assertEqual(a["source"]["line"], 8)
        self.assertEqual(b["source"]["line"], 14)
        self.assertEqual(a["source"]["commit"], b["source"]["commit"])
        self.assertFalse(a["safety"]["write_permitted"])
        self.assertFalse(a["page"]["revision_verified"])
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_reject_mismatching_dom(self):
        bad = copy.deepcopy(self.first)
        bad["dom"]["endUtf16"] = 25
        with self.assertRaises(LocalizationError) as error:
            locate(self.repo, RELATIVE, bad)
        self.assertEqual(error.exception.reason, "DOM_MISMATCH")

    def test_reject_modified_source(self):
        self.file.write_text(SAMPLE_SOURCE + "\nUn ajout non commité.\n", encoding="utf-8")
        with self.assertRaises(LocalizationError) as error:
            locate(self.repo, RELATIVE, self.first)
        self.assertEqual(error.exception.reason, "DIRTY_SOURCE")

    def test_reject_wrong_file_for_page(self):
        with self.assertRaises(LocalizationError) as error:
            locate(self.repo, "README.md", self.first)
        self.assertEqual(error.exception.reason, "PAGE_SOURCE_MISMATCH")

    def test_reject_ambiguous_source(self):
        self.file.write_text(SAMPLE_SOURCE + "\nPlace les cinq fichiers dans le répertoire `AtelierDemo` pour cet exercice :\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.name=Demo", "-c", "user.email=demo@example.test", "commit", "-qm", "another occurrence")
        with self.assertRaises(LocalizationError) as error:
            locate(self.repo, RELATIVE, self.first)
        self.assertEqual(error.exception.reason, "AMBIGUOUS_SOURCE")

    def test_reject_stale_required_sha(self):
        with self.assertRaises(LocalizationError) as error:
            locate(self.repo, RELATIVE, self.first, require_sha="0" * 40)
        self.assertEqual(error.exception.reason, "UNEXPECTED_COMMIT")


if __name__ == "__main__":
    unittest.main()
