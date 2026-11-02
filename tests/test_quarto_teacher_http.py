# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.6B professor HTTP safety experiment: exclusively fictional files."""
from __future__ import annotations

import contextlib
from dataclasses import FrozenInstanceError
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
from unittest.mock import patch
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

    def test_only_html_is_served_even_when_auxiliary_assets_are_valid(self):
        # L2: the verified inventory is NOT a list of HTTP authorizations.
        self.assertEqual(len(self.preview.routes), 1)
        self.assertEqual(
            list(self.preview.routes), [self.preview.html_route])
        for name in (self.css_path, self.js_path):
            route = self.preview.prefix + "/" + name
            with self.subTest(name=name):
                code, headers, body = self.request(route)
                self.assertEqual(code, 404)
                self.assertNotIn(self.assets[name], body)
                self.assertEqual(self.request(route, method="HEAD")[0], 404)
                with self.assertRaises(FileNotFoundError):
                    self.preview.get_asset(route)
        self.assertEqual(self.request(self.preview.html_route)[0], 200)
        self.assertEqual(self.request(self.preview.html_route, method="HEAD")[0], 200)

    def test_renamed_secret_in_output_stays_unavailable_over_http(self):
        """A source disguised as a CSS/image stays inaccessible."""
        name = "dist/professeur/cours/mission/teacher-secrets.css"
        payload = b"FICTIONAL_RENAMED_SOURCE_NOT_FOR_HTTP"
        target = self.session / "project" / name
        target.write_bytes(payload)
        self.manifest["rendered_files"].append({
            "path": name, "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest()
        })
        self.manifest["rendered_files"].sort(key=lambda x: x["path"])
        self.save_manifest()
        # The P3.6A oracle validates this file's bytes; L2 forbids HTTP
        # exposure even when a source is deliberately misnamed as an asset.
        self.assertEqual(
            verify_session(self.session)["status"],
            "LOCAL_PROFESSOR_FILES_REHASHED")
        preview = FictionalTeacherPreview(self.session)
        self.assertEqual(len(preview.routes), 1)
        url = preview.prefix + "/" + name
        with self.assertRaises(FileNotFoundError):
            preview.get_asset(url)
        self.assertEqual(
            preview.get_asset(preview.html_route)[0], self.assets[self.html_path])

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

    def test_post_start_mutation_and_symlink_do_not_change_sealed_html(self):
        """The only HTTP response is the original verified HTML snapshot."""
        asset = self.session / "project" / self.html_path
        route = self.preview.html_route
        original = asset.read_bytes()
        asset.write_bytes(b"x" * len(original))
        self.assertEqual(self.request(route)[0], 200)
        self.assertEqual(self.request(route)[2], original)
        with self.assertRaises(TeacherHTTPError):
            FictionalTeacherPreview(self.session)
        asset.unlink()
        asset.symlink_to(self.session / "project" / self.css_path)
        self.assertEqual(self.request(route)[2], original)
        with self.assertRaises(TeacherHTTPError):
            FictionalTeacherPreview(self.session)

    def test_direct_session_cli_is_disabled_even_for_forged_fiction(self):
        """An arbitrary manifest path is not authorization to serve HTTP."""
        from quarto_teacher_http import main as direct_main
        with contextlib.redirect_stderr(io.StringIO()):
            for args in ([], ["--session", str(self.session)]):
                with self.subTest(args=args):
                    with self.assertRaises(SystemExit) as error:
                        direct_main(args)
                    self.assertEqual(error.exception.code, 2)

    def test_manifest_switch_between_verification_and_admission_refused(self):
        """C1: never admit a second manifesto after validating the first."""
        original_verify = verify_session
        name = "dist/professeur/cours/mission/added.txt"
        payload = b"FICTIONAL_NOT_IN_PREVIOUSLY_VERIFIED_INVENTORY"
        entry = {"path": name, "bytes": len(payload),
                 "sha256": hashlib.sha256(payload).hexdigest()}

        def verify_then_switch(session, **kwargs):
            proof = original_verify(session, **kwargs)
            (self.session / "project" / name).write_bytes(payload)
            changed = dict(self.manifest)
            changed["rendered_files"] = sorted(
                [*self.manifest["rendered_files"], entry],
                key=lambda item: item["path"])
            changed["rendered_html"] = entry  # not a valid .html identity
            (self.session / "manifest.json").write_text(json.dumps(changed))
            return proof

        with patch("quarto_teacher_http.verify_session",
                   side_effect=verify_then_switch):
            with self.assertRaisesRegex(TeacherHTTPError, "Manifeste changé"):
                FictionalTeacherPreview(self.session)
        with self.assertRaises(TeacherRenderError):
            original_verify(self.session)  # changed manifest is INVALID
        # Previously opened preview serves only the already sealed fixture.
        code, _, body = self.request(self.url().path)
        self.assertEqual(code, 200)
        self.assertEqual(body, self.assets[self.html_path])

    def test_route_mapping_cannot_be_mutated_after_admission(self):
        """C2: immutable bytes, map AND preview attribute bindings."""
        route = self.preview.html_route
        with self.assertRaises(TypeError):
            self.preview.routes[route] = (b"UNVERIFIED", "text/html")
        with self.assertRaises(TypeError):
            del self.preview.routes[route]
        # Exact remaining auditor counterexample: replacing the field used
        # by the already running HTTP handler must fail, not serve new bytes.
        with self.assertRaises(FrozenInstanceError):
            self.preview.routes = {route: (b"FICTIONAL_UNVERIFIED", "text/html")}
        with self.assertRaises(FrozenInstanceError):
            del self.preview.routes
        for key, value in (
            ("html_route", "/replaced"),
            ("prefix", "/replaced"),
            ("session", self.session.parent),
        ):
            with self.subTest(field=key):
                with self.assertRaises(FrozenInstanceError):
                    setattr(self.preview, key, value)
        self.assertEqual(
            self.preview.get_asset(route)[0], self.assets[self.html_path])
        # Verify the in-flight handler continues to serve the sealed content.
        self.assertEqual(self.request(route)[2], self.assets[self.html_path])

    def test_manifest_proof_returns_same_validated_object_only_on_optin(self):
        ordinary = verify_session(self.session)
        self.assertNotIn("verified_manifest", ordinary)
        self.assertNotIn("verified_manifest_sha256", ordinary)
        detailed = verify_session(self.session, include_manifest=True)
        self.assertEqual(detailed["verified_manifest"], self.manifest)
        self.assertEqual(
            detailed["verified_manifest_sha256"],
            hashlib.sha256((self.session / "manifest.json").read_bytes()).hexdigest())

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
        self.assertEqual(len(preview.routes), 1)
        self.assertGreater(len(manifest["rendered_files"]), 1)
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
