# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.6B professor HTTP safety experiment: exclusively fictional files."""
from __future__ import annotations

import contextlib
import io
import hashlib
import http.client
import json
import os
import socket
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

from quarto_teacher_http import (
    FictionalTeacherPreview, TeacherHTTPError, make_server,
)
from quarto_teacher_render import TeacherRenderError, verify_session


class FictionalTeacherHTTPTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="alliage-fiction-p36b-")
        self.addCleanup(tmp.cleanup)
        self.session = Path(tmp.name) / "session"
        self.session.mkdir(mode=0o700)
        project = self.session / "project"
        project.mkdir()
        self.html_path = (
            "dist/professeur/cours/mission/activite.html")
        self.css_path = (
            "dist/professeur/cours/mission/assets/theme.css")
        self.js_path = (
            "dist/professeur/cours/mission/activite_files/module.js")
        self.assets = {
            self.html_path:
                b'<!doctype html><title>FICTION</title><h1>Teacher fixture</h1>',
            self.css_path: b"h1 { color: rebeccapurple; }",
            self.js_path: b"export const FICTIONAL = true;",
        }
        for name, data in self.assets.items():
            target = project / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        # Explicitly present private-looking source/manifest sentinels: neither
        # is part of the approved output inventory nor eligible for a route.
        (project / "cours").mkdir(exist_ok=True)
        (project / "cours/secret.qmd").write_text(
            "FICTIONAL_SOURCE_MUST_NOT_BE_SERVED")
        self.manifest = {
            "schema": "alliage.quarto-professor-render.v0",
            "resource_id": "quarto:fiction/laboratoire:cours/mission/activite.qmd",
            "source_path": "cours/mission/activite.qmd",
            "status": "PROFESSOR_RENDER_OBSERVED_LOCAL_ONLY",
            "publication_performed": False,
            "student_deployment_verified": False,
            "render_profile_effective_verified": False,
            "teacher_html_verified": True,
            "rendered_files": [
                {"path": name, "bytes": len(data),
                 "sha256": hashlib.sha256(data).hexdigest()}
                for name, data in sorted(self.assets.items())
            ],
        }
        self.manifest["rendered_html"] = next(
            item for item in self.manifest["rendered_files"]
            if item["path"] == self.html_path
        )
        self.save_manifest()
        self.preview = FictionalTeacherPreview(self.session)
        self.server = make_server(self.preview)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def save_manifest(self):
        (self.session / "manifest.json").write_text(
            json.dumps(self.manifest), encoding="utf-8")

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, path, method="GET", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1",
                                          self.server.server_port, timeout=5)
        try:
            conn.request(method, path, headers=headers or {})
            response = conn.getresponse()
            return (response.status, dict(response.getheaders()),
                    response.read())
        finally:
            conn.close()

    def url(self):
        return urlsplit(self.preview.browser_url(self.server.server_port))

    def test_professor_html_exact_and_no_scripts_or_external_network(self):
        url = self.url()
        self.assertEqual(url.hostname, "127.0.0.1")
        self.assertEqual(url.query, "")
        code, headers, body = self.request(url.path)
        self.assertEqual(code, 200)
        self.assertEqual(body, self.assets[self.html_path])
        policy = headers["Content-Security-Policy"]
        self.assertIn("script-src 'none'", policy)
        self.assertIn("connect-src 'none'", policy)
        # Quarto embed-resources emits data:text/css URLs, which are not
        # authorized by 'unsafe-inline' alone. Permit CSS data: only.
        self.assertIn("style-src 'self' 'unsafe-inline' data:", policy)
        self.assertNotIn("script-src 'self'", policy)
        self.assertNotIn("connect-src 'self'", policy)
        style = next(part for part in policy.split(";")
                     if part.strip().startswith("style-src ")).strip()
        self.assertNotIn("https:", style)
        self.assertNotIn("http:", style)
        self.assertIn("sandbox allow-same-origin",
                      headers["Content-Security-Policy"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["Cross-Origin-Resource-Policy"], "same-origin")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertFalse(self.preview.prefix.startswith("/alliage-local-"))

    def test_exact_css_and_js_asset_bytes_but_scripts_disabled_in_browser(self):
        for name, data in self.assets.items():
            url = (self.preview.prefix + "/" + name)
            code, headers, body = self.request(url)
            self.assertEqual(code, 200)
            self.assertEqual(body, data)
            self.assertIn("script-src 'none'", headers["Content-Security-Policy"])
            if name.endswith(".css"):
                self.assertTrue(headers["Content-Type"].startswith("text/css"))
            if name.endswith(".js"):
                self.assertTrue(headers["Content-Type"].startswith("text/javascript"))
            self.assertEqual(self.request(url, method="HEAD")[2], b"")

    def test_refuse_paths_queries_unlisted_sources_and_methods(self):
        prefix = self.preview.prefix
        cases = (
            "/", "/api/health", "/api/experiment",
            prefix + "/manifest.json",
            prefix + "/project/cours/secret.qmd",
            prefix + "/cours/secret.qmd",
            prefix + "/dist/eleve/cours/mission/activite.html",
            prefix + "/dist/professeur/cours/mission/activite.qmd",
            prefix + "/dist/professeur/cours/mission/unlisted.css",
            prefix + "/dist/professeur/cours/mission/%2e%2e/secret.qmd",
            prefix + "/dist/professeur/cours/mission/../secret.qmd",
            prefix + "/dist/professeur/cours/mission/%2Fetc%2Fpasswd",
            self.url().path + "?anything=1",
            self.url().path + "#" + "x",
            "/alliage-professor-fixture-" + "0" * 32 + "/" + self.html_path,
        )
        for path in cases:
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request(self.url().path, method="POST")[0], 405)
        self.assertEqual(self.request(self.url().path, method="OPTIONS")[0], 405)

    def test_reject_cross_site_host_and_origin(self):
        cases = (
            {"Host": "evil.example"},
            {"Host": f"localhost:{self.server.server_port}"},
            {"Origin": "https://evil.example"},
            {"Origin": "null"},
            {"Sec-Fetch-Site": "cross-site"},
            {"Sec-Fetch-Site": "same-site"},
        )
        for headers in cases:
            with self.subTest(headers=headers):
                self.assertEqual(self.request(self.url().path, headers=headers)[0], 403)
        good = {"Host": f"127.0.0.1:{self.server.server_port}",
                "Origin": f"http://127.0.0.1:{self.server.server_port}",
                "Sec-Fetch-Site": "same-origin"}
        self.assertEqual(self.request(self.url().path, headers=good)[0], 200)

    def test_post_start_mutation_and_symlink_do_not_change_sealed_bytes(self):
        """A response is the admitted immutable snapshot, not mutable disk."""
        asset = self.session / "project" / self.css_path
        route = self.preview.prefix + "/" + self.css_path
        original = asset.read_bytes()
        asset.write_bytes(b"x" * len(original))
        self.assertEqual(self.request(route)[0], 200)
        self.assertEqual(self.request(route)[2], original)
        # A newly admitted preview must still detect altered bytes.
        with self.assertRaises(TeacherHTTPError):
            FictionalTeacherPreview(self.session)
        asset.unlink()
        asset.symlink_to(self.session / "project" / self.html_path)
        self.assertEqual(self.request(route)[2], original)
        # New admission rejects symlinks rather than silently following.
        with self.assertRaises(TeacherHTTPError):
            FictionalTeacherPreview(self.session)

    def test_raw_http_target_and_duplicate_security_headers_denied(self):
        """Test what CPython normalizes BEFORE Handler.path is available."""
        url = self.url()
        port = self.server.server_port
        host = f"127.0.0.1:{port}"
        requests = [
            (f"GET /{url.path} HTTP/1.1\r\nHost: {host}\r\n\r\n")
                .encode("ascii"),
            (f"GET http://{host}{url.path} HTTP/1.1\r\nHost: {host}\r\n\r\n")
                .encode("ascii"),
            (f"GET {url.path} HTTP/1.1\r\nHost: {host}\r\nHost: evil.example\r\n\r\n")
                .encode("ascii"),
            (f"GET {url.path} HTTP/1.1\r\nHost: {host}\r\n"
             f"Origin: http://{host}\r\nOrigin: https://evil.example\r\n\r\n")
                .encode("ascii"),
            (f"GET {url.path} HTTP/1.1\r\nHost: {host}\r\n"
             "Sec-Fetch-Site: none\r\nSec-Fetch-Site: cross-site\r\n\r\n")
                .encode("ascii"),
        ]
        for payload in requests:
            with self.subTest(request=payload.split(b"\r\n")[0]):
                with socket.create_connection(("127.0.0.1", port), timeout=5) as peer:
                    peer.sendall(payload)
                    first = peer.recv(256).split(b"\r\n")[0]
                self.assertIn(b" 403 ", first)
        self.assertEqual(self.request(url.path)[0], 200)

    def test_invalid_manifest_rejected_before_server_start(self):
        self.manifest["resource_id"] = (
            "quarto:djibian/pedagogie:cours/mission/activite.qmd")
        self.save_manifest()
        with self.assertRaisesRegex(TeacherHTTPError, "fictives"):
            FictionalTeacherPreview(self.session)
        self.manifest["resource_id"] = (
            "quarto:fiction/laboratoire:cours/mission/activite.qmd")
        self.manifest["rendered_html"]["sha256"] = "0" * 64
        self.save_manifest()
        with self.assertRaises(TeacherHTTPError):
            FictionalTeacherPreview(self.session)

    def test_manifest_cannot_add_non_output_route(self):
        self.manifest["rendered_files"].append({
            "path": "cours/secret.qmd",
            "bytes": len(b"FICTIONAL_SOURCE_MUST_NOT_BE_SERVED"),
            "sha256": hashlib.sha256(
                b"FICTIONAL_SOURCE_MUST_NOT_BE_SERVED").hexdigest(),
        })
        self.save_manifest()
        with self.assertRaises((TeacherHTTPError, TeacherRenderError)):
            FictionalTeacherPreview(self.session)

    def test_output_inventory_does_not_authorize_qmd_sources(self):
        """A Quarto-copied QMD must never become an HTTP route."""
        name = "dist/professeur/cours/mission/private-source.qmd"
        data = b"FICTIONAL_PROFESSOR_SOURCE_NOT_FOR_HTTP"
        target = self.session / "project" / name
        target.write_bytes(data)
        self.manifest["rendered_files"].append({
            "path": name, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
        self.save_manifest()
        # The normal P3.6A verifier checks integrity, not HTTP suitability.
        self.assertEqual(
            verify_session(self.session)["status"],
            "LOCAL_PROFESSOR_FILES_REHASHED",
        )
        with self.assertRaisesRegex(TeacherHTTPError, "diffusable"):
            FictionalTeacherPreview(self.session)

    def test_fixed_firefox_demo_refuses_unapproved_and_session_arguments(self):
        import p36b_fictional_firefox_demo as demo
        with contextlib.redirect_stderr(io.StringIO()):
            for args in ([], ["--session", str(self.session)],
                         ["--repo", str(self.session)],
                         ["--trusted-fixture-quarto", "--session",
                          str(self.session)]):
                with self.subTest(args=args):
                    with self.assertRaises(SystemExit) as error:
                        demo.main(args)
                    self.assertEqual(error.exception.code, 2)

    @unittest.skipUnless(os.environ.get("ALLIAGE_TEST_REAL_QUARTO") == "1",
                         "Run in dedicated Quarto fixture CI")
    def test_fixed_firefox_demo_generates_only_its_public_fixture(self):
        import p36b_fictional_firefox_demo as demo
        fixture, preview, report = demo.create_fixed_fictional_session()
        try:
            self.assertEqual(
                report["resource_id"],
                "quarto:fiction/laboratoire:cours/mission/activite.qmd",
            )
            self.assertEqual(
                verify_session(fixture.output)["status"],
                "LOCAL_PROFESSOR_FILES_REHASHED",
            )
            page, mime = preview.get_asset(preview.html_route)
            self.assertIn(b"FICTIONAL_TEACHER_MARKER", page)
            self.assertNotIn(b"FICTIONAL_STUDENT_MARKER", page)
            self.assertTrue(mime.startswith("text/html"))
        finally:
            fixture.doCleanups()

    @unittest.skipUnless(os.environ.get("ALLIAGE_TEST_REAL_QUARTO") == "1",
                         "Run in dedicated Quarto fixture CI")
    def test_real_quarto_fictional_professor_output_served(self):
        """Quarto integration, still a fully fictional fixture."""
        from test_quarto_teacher_render import TeacherRenderTests, render
        fixture = TeacherRenderTests("test_plan_never_executes_quarto_or_writes_source")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        manifest = render(*fixture.args(), fixture.output, trusted_quarto=True)
        preview = FictionalTeacherPreview(fixture.output)
        report = verify_session(fixture.output)
        self.assertEqual(report["status"], "LOCAL_PROFESSOR_FILES_REHASHED")
        self.assertEqual(len(preview.routes), len(manifest["rendered_files"]))
        # Exercise the actual HTTP transport on the real Quarto fictional
        # output, not merely the asset reader used by the HTTP handler.
        server = make_server(preview)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection(
                "127.0.0.1", server.server_port, timeout=5)
            try:
                connection.request("GET", preview.html_route)
                reply = connection.getresponse()
                html = reply.read()
                self.assertEqual(reply.status, 200)
                policy = dict(reply.getheaders())["Content-Security-Policy"]
                self.assertIn("script-src 'none'", policy)
                self.assertIn("style-src 'self' 'unsafe-inline' data:", policy)
            finally:
                connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertIn(b"FICTIONAL_TEACHER_MARKER", html)
        self.assertNotIn(b"FICTIONAL_STUDENT_MARKER", html)
        # Real Quarto embeds stylesheets as data: URLs in this fixture.
        # The HTTP CSP must explicitly permit this static display path.
        self.assertIn(b"data:text/css", html)
        self.assertEqual(html, (fixture.output / "project" /
                                manifest["rendered_html"]["path"]).read_bytes())


if __name__ == "__main__":
    unittest.main()
