import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from serveur import Service, make_handler, ThreadingHTTPServer, PILOT_REL, require_pilot
from test_experiment import QMD, fake_quarto, git


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        qmd = self.repo / PILOT_REL
        qmd.parent.mkdir(parents=True)
        qmd.write_text(QMD, encoding="utf-8")
        (self.repo / "_quarto.yml").write_text("project:\n  type: default\n",encoding="utf-8")
        (self.repo / "_quarto-eleve.yml").write_text("project:\n  output-dir: dist/eleve\n",encoding="utf-8")
        css = self.repo / "publication/quarto/tim.css"
        css.parent.mkdir(parents=True,exist_ok=True)
        css.write_text("body{}",encoding="utf-8")
        git(self.repo,"add",".")
        git(self.repo,"-c","user.name=Test","-c","user.email=test@example.org","commit","-qm","test")
        private_anchors = self.root / "local-anchors"
        private_anchors.mkdir()
        for n in (1, 2):
            (private_anchors / f"selection-{n}.json").write_bytes((ROOT / "exemples" / f"selection-{n}.json").read_bytes())
        self.service = Service(self.repo,self.root/"out", "secret-local-long", self.root)
        self.selection = json.loads((ROOT/"exemples/selection-1.json").read_text(encoding="utf-8"))
        self.payload = {"selection": self.selection,"optionA":"cinq ressources","optionB":"cinq fichiers proposés"}

    def create_experiment(self):
        with patch("experiment.run_quarto", side_effect=fake_quarto),patch("experiment.shutil.which",return_value="/usr/bin/quarto"):
            return self.service.experiment(self.payload)

    def test_create_compare_decide_and_guard(self):
        result=self.create_experiment()
        self.assertEqual(result["status"],"RENDER_VERIFIED_LOCAL")
        self.assertFalse(result["report"]["production_write"])
        self.assertEqual(result["report"]["guard_count"],1)
        self.assertTrue(all(o["render_verified"] for o in result["report"]["options"]))
        identifier = result["id"]
        data,mime=self.service.preview("/experiences/"+identifier+"/comparaison.html")
        self.assertIn(b"Comparaison de variantes",data)
        self.assertIn("text/html",mime)
        choice=self.service.decision({"id":identifier,"choice":"B"})
        self.assertEqual(choice["status"], "SELECTED_EXPERIMENTAL_ONLY")
        self.assertEqual(choice["choice"],"B")
        self.assertTrue((self.root/"out"/identifier/"decision.json").exists())
        other=self.service.decision({"id":identifier,"choice":"REJETER"})
        self.assertEqual(other["status"],"REJECTED_LOCAL")
        self.assertTrue((self.root/"out"/identifier/"decision-002.json").exists())
        self.assertEqual((self.repo/PILOT_REL).read_text(encoding="utf-8"),QMD)
        self.assertEqual(subprocess.check_output(["git","-C",str(self.repo),"status","--porcelain"],text=True),"")

    def test_cross_repo_or_page_refused(self):
        bad=json.loads(json.dumps(self.selection))
        bad["page"]["url"]="https://example.org/elsewhere"
        with self.assertRaises(ValueError):require_pilot(bad)
        with self.assertRaises(ValueError):self.service.experiment({**self.payload,"selection":bad})

    def test_tampering_refuses_selection(self):
        result=self.create_experiment()
        output=self.root/"out"/result["id"]
        (output/result["report"]["options"][0]["qmd"]).write_text("DANGER",encoding="utf-8")
        with self.assertRaises(ValueError):self.service.decision({"id":result["id"],"choice":"A"})

    def test_no_traversal_leak(self):
        result=self.create_experiment()
        identifier=result["id"]
        for suffix in ["/../../rapport.json", "/%2e%2e/rapport.json", "/rapport.json", "/variantes/A/"+PILOT_REL]:
            with self.assertRaises(FileNotFoundError):self.service.preview("/experiences/"+identifier+suffix)

    def test_http_post_requires_token_and_origin(self):
        server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(self.service))
        t=threading.Thread(target=server.serve_forever,daemon=True)
        t.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def send(headers=None):
            conn=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=3)
            h={"Host":"127.0.0.1:8765","Content-Type":"application/json"}
            if headers:h.update(headers)
            conn.request("POST","/api/decision", body=json.dumps({"id":"0"*32,"choice":"A"}),headers=h)
            response=conn.getresponse()
            status=response.status
            body=json.loads(response.read().decode())
            conn.close()
            return status, body
        self.assertEqual(send()[0],403)
        self.assertEqual(send({"X-Pedagolab-Token":"secret-local-long","Origin":"https://evil.test"})[0],403)
        self.assertEqual(send({"X-Pedagolab-Token":"secret-local-long","Origin":"moz-extension://aaaaaaaa"})[0],422)


if __name__ == "__main__": unittest.main()
