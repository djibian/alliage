# SPDX-License-Identifier: AGPL-3.0-or-later
"""F1 fake HTTP witness tests. No Firefox, Quarto or external network."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import threading
import unittest
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "experiments" / "p36f_fixture.py"
spec = importlib.util.spec_from_file_location("p36f_fixture", SCRIPT)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class F1LocalWitnessTests(unittest.TestCase):
    def test_two_loopback_servers_and_negative_witness(self):
        servers, counter = fixture.start_pair(0, 0)
        self.assertEqual(len(servers), 2)
        decoy, source = servers
        self.assertEqual(decoy.server_address[0], "127.0.0.1")
        self.assertEqual(source.server_address[0], "127.0.0.1")
        self.assertNotEqual(decoy.server_address[1], source.server_address[1])
        threads = [threading.Thread(target=s.serve_forever, daemon=True)
                   for s in servers]
        try:
            for thread in threads:
                thread.start()
            a = f"http://127.0.0.1:{source.server_address[1]}"
            b = f"http://127.0.0.1:{decoy.server_address[1]}"
            with urlopen(a + fixture.PATH, timeout=3) as response:
                html = response.read()
                self.assertEqual(response.status, 200)
            self.assertIn(b"ALLIAGE_FICTION_ONLY", html)
            self.assertIn((b + "/probe").encode(), html)
            self.assertIn(b'target="_blank"', html)
            with urlopen(b + "/stats", timeout=3) as response:
                self.assertEqual(
                    json.load(response)["fictional_decoy_requests"], 0)
            # This is the NO-VETO control, NOT proof of an extension veto.
            with urlopen(b + "/probe", timeout=3) as response:
                self.assertEqual(response.status, 200)
            with urlopen(b + "/stats", timeout=3) as response:
                self.assertEqual(
                    json.load(response)["fictional_decoy_requests"], 1)
            with counter["lock"]:
                self.assertEqual(counter["count"], 1)
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
