# SPDX-License-Identifier: AGPL-3.0-or-later
"""Adversarial loopback Quarto preview tests; fictional files and local HTTP only."""
from __future__ import annotations

import hashlib
import http.client
import json
from pathlib import Path
import threading
import unittest
from urllib.parse import urlsplit
from unittest.mock import patch

from quarto_local_http import AttestedPreview, HTTPPreviewError, make_server
from quarto_navigation import NavigationError
from test_quarto_observed_session import ObservedSessionTests


class LocalHTTPPreviewTests(unittest.TestCase):
    def setUp(self):
        # Reuse the genuine P3.3/P3.1/P3.2 fake-Git integration fixture.
        self.fixture = ObservedSessionTests("test_check_is_read_only_and_css_change_is_real")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        with patch("quarto_observed_session.create_preview",
                   side_effect=self.fixture.fake_preview):
            report = self.fixture.run_session()
        self.session = Path(report["session_path"])
        self.resource_id = report["resource_id"]
        self.assets = {}
        # Include ES modules that historically failed under file:// in Firefox.
        for version in ("V1", "V2"):
            site = self.session / version / "project/_site"
            manifest_path = self.session / version / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            for relative, content in {
                "activite_files/libs/quarto-html/quarto.js":
                    b"export const fixture = 'quarto module';",
                "activite_files/libs/quarto-html/tabsets/tabsets.js":
                    b"export const tabsets = true;",
            }.items():
                target = site / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                manifest["rendered_files"].append({
                    "path": "project/_site/" + relative,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "bytes": len(content)})
                self.assets[(version, relative)] = content
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.preview = AttestedPreview(self.session, self.resource_id)
        self.server = make_server(self.preview)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, path, method="GET", headers=None):
        connection = http.client.HTTPConnection("127.0.0.1",
                                                self.server.server_port, timeout=5)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            body = response.read()
            return response.status, dict(response.getheaders()), body
        finally:
            connection.close()

    def test_resource_html_is_native_unmodified_and_capability_scoped(self):
        url = urlsplit(self.preview.browser_url(self.server.server_port))
        self.assertEqual(url.hostname, "127.0.0.1")
        self.assertTrue(url.path.endswith("/V2/project/_site/activite.html"))
        self.assertIn("alliage-history-v0=", url.query)
        code, headers, body = self.request(url.path + "?" + url.query)
        self.assertEqual(code, 200)
        self.assertEqual(body, (self.session / "V2/project/_site/activite.html").read_bytes())
        self.assertTrue(headers["Content-Type"].startswith("text/html"))
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Cross-Origin-Resource-Policy"], "same-origin")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertEqual(self.request(url.path)[0], 200)  # no query => inert overlay

    def test_quarto_css_and_modules_are_served_with_strict_mime(self):
        for version in ("V1", "V2"):
            root = self.preview.prefix + "/" + version + "/project/_site/"
            code, headers, content = self.request(root + "styles.css")
            self.assertEqual(code, 200)
            self.assertEqual(content, (self.session / version /
                                      "project/_site/styles.css").read_bytes())
            self.assertTrue(headers["Content-Type"].startswith("text/css"))
            for relative in ("activite_files/libs/quarto-html/quarto.js",
                             "activite_files/libs/quarto-html/tabsets/tabsets.js"):
                code, headers, content = self.request(root + relative)
                self.assertEqual(code, 200)
                self.assertEqual(content, self.assets[(version, relative)])
                self.assertTrue(headers["Content-Type"].startswith("text/javascript"))
        self.assertEqual(self.request(self.preview.prefix + "/V1/project/_site/activite.html")[0], 200)

    def test_reject_unauthorized_host_origin_or_cross_site(self):
        asset = self.preview.prefix + "/V2/project/_site/activite.html"
        cases = (
            {"Host": "evil.example"},
            {"Host": "localhost:" + str(self.server.server_port)},
            {"Origin": "https://evil.example"},
            {"Origin": "null"},
            {"Sec-Fetch-Site": "cross-site"},
            {"Sec-Fetch-Site": "same-site"},
        )
        for headers in cases:
            with self.subTest(headers=headers):
                self.assertEqual(self.request(asset, headers=headers)[0], 403)
        good = {"Origin": "http://127.0.0.1:" + str(self.server.server_port),
                "Sec-Fetch-Site": "same-origin"}
        self.assertEqual(self.request(asset, headers=good)[0], 200)

    def test_reject_unlisted_capabilities_paths_and_methods(self):
        prefix = self.preview.prefix
        for path in (
            "/", "/api/health", "/api/experiment", "/etc/passwd",
            prefix.replace("a", "b", 1) + "/V2/project/_site/activite.html",
            prefix + "/V3/project/_site/activite.html",
            prefix + "/V2/project/activite.qmd",
            prefix + "/V2/manifest.json",
            prefix + "/V2/project/_site/extra.js",
            prefix + "/V2/project/_site/%2e%2e/manifest.json",
            prefix + "/V2/project/_site/../manifest.json",
            prefix + "/V2/project/_site/%2Fetc%2Fpasswd",
            prefix + "/V2/project/_site/activite.html?" + "x" * 4100,
        ):
            with self.subTest(path=path[:100]):
                self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request(prefix + "/V2/project/_site/activite.html",
                                      method="POST")[0], 405)
        self.assertEqual(self.request(prefix + "/V2/project/_site/activite.html",
                                      method="OPTIONS")[0], 405)

    def test_detect_post_start_same_size_asset_tampering_and_symlink(self):
        path = self.preview.prefix + "/V2/project/_site/styles.css"
        asset = self.session / "V2/project/_site/styles.css"
        original = asset.read_bytes()
        asset.write_bytes(b"x" * len(original))
        self.assertEqual(self.request(path)[0], 404)
        asset.write_bytes(original)
        self.assertEqual(self.request(path)[0], 200)
        asset.unlink()
        asset.symlink_to(self.session / "V1/project/_site/styles.css")
        self.assertEqual(self.request(path)[0], 404)

    def test_refuse_preflight_if_manifest_or_css_is_not_attested(self):
        with self.assertRaises(NavigationError):
            AttestedPreview(self.session, "quarto:fiction/laboratoire:other.qmd")
        path = self.session / "V2/project/_site/styles.css"
        original = path.read_bytes()
        path.write_bytes(b"y" * len(original))
        with self.assertRaises(NavigationError):
            AttestedPreview(self.session, self.resource_id)


if __name__ == "__main__":
    unittest.main()
