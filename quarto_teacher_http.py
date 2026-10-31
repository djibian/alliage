#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.6B research: serve ONLY fictional P3.6A professor-output fixtures.

This is not authorization to serve genuine professor resources. It does not
authenticate a manifest, sandbox Quarto or verify the effective Quarto profile.
No Git, Quarto, writes, Firefox extension or publication actions.
"""
from __future__ import annotations

import argparse
import hashlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from pathlib import PurePosixPath
import secrets
from urllib.parse import quote

from quarto_navigation import NavigationError, _regular_within
from quarto_teacher_render import TeacherRenderError, verify_session

BIND = "127.0.0.1"
PREFIX = "dist/professeur/"
MAX_ASSETS = 2000
# Deliberately STATIC: remote resources and every script (including Quarto's
# own) are blocked. Full interactive fidelity is NOT proven by this experiment.
CSP = (
    "sandbox allow-same-origin; default-src 'none'; script-src 'none'; "
    "connect-src 'none'; img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; font-src 'self' data:; "
    "media-src 'self'; object-src 'none'; frame-src 'none'; "
    "worker-src 'none'; form-action 'none'; base-uri 'none'"
)


class TeacherHTTPError(ValueError):
    """Unsafe, unverified or non-fictional resource requested."""


def _asset_name(value: object) -> str:
    if not isinstance(value, str) or not value.startswith(PREFIX):
        raise TeacherHTTPError("Sortie professeur non autorisée.")
    if ("\\" in value or "\x00" in value or "%" in value
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise TeacherHTTPError("Chemin non canonique.")
    relative = PurePosixPath(value)
    if relative.is_absolute() or relative.as_posix() != value:
        raise TeacherHTTPError("Chemin non canonique.")
    return value


class FictionalTeacherPreview:
    """Verified professor-output assets, restricted to fictional sessions."""

    def __init__(self, session: Path):
        self.session = Path(session).expanduser().absolute()
        # verify_session checks the real P3.6A HTML identity, symlinks, exact
        # inventory and SHA-256. The manifest is local, NOT signed or trusted.
        try:
            verify_session(self.session)
            report = json.loads((self.session / "manifest.json").read_text(
                encoding="utf-8"))
        except (TeacherRenderError, OSError, ValueError, TypeError) as exc:
            raise TeacherHTTPError("Session P3.6A non vérifiable.") from exc
        rid = report.get("resource_id")
        # Hard feature gate: NO actual professor session is eligible in P3.6B.
        if not isinstance(rid, str) or not rid.startswith("quarto:fiction/"):
            raise TeacherHTTPError("P3.6B autorise uniquement des fixtures fictives.")
        files = report.get("rendered_files")
        html = report.get("rendered_html")
        if not isinstance(files, list) or not 1 <= len(files) <= MAX_ASSETS:
            raise TeacherHTTPError("Inventaire P3.6A invalide.")
        if not isinstance(html, dict) or not isinstance(html.get("path"), str):
            raise TeacherHTTPError("HTML professeur non attesté.")
        self.prefix = "/alliage-professor-fixture-" + secrets.token_hex(16)
        self.routes: dict[str, tuple[str, int, str]] = {}
        for item in files:
            if not isinstance(item, dict):
                raise TeacherHTTPError("Entrée de manifeste invalide.")
            name = _asset_name(item.get("path"))
            size = item.get("bytes")
            digest = item.get("sha256")
            if type(size) is not int or size < 0 or not isinstance(digest, str):
                raise TeacherHTTPError("Entrée de manifeste non vérifiable.")
            route = self.prefix + "/" + quote(name, safe="/")
            if route in self.routes:
                raise TeacherHTTPError("Collision de routes professeur.")
            self.routes[route] = (name, size, digest)
        html_route = self.prefix + "/" + quote(_asset_name(html["path"]), safe="/")
        if html_route not in self.routes:
            raise TeacherHTTPError("HTML professeur absent de l'inventaire.")
        self.html_route = html_route

    def browser_url(self, port: int) -> str:
        return f"http://{BIND}:{port}{self.html_route}"

    def get_asset(self, path: str) -> tuple[bytes, str]:
        asset = self.routes.get(path)
        if asset is None:
            raise FileNotFoundError("Route non autorisée.")
        name, size, digest = asset
        try:
            file = _regular_within(self.session / "project", name)
            if file.stat().st_size != size:
                raise TeacherHTTPError("Taille d'actif modifiée.")
            data = file.read_bytes()
        except (NavigationError, OSError) as exc:
            raise TeacherHTTPError("Actif professeur indisponible.") from exc
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise TeacherHTTPError("SHA-256 d'actif professeur modifié.")
        if file.suffix.lower() in (".js", ".mjs"):
            mime = "text/javascript"
        elif file.suffix.lower() == ".css":
            mime = "text/css"
        else:
            mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        if mime.startswith("text/") or mime in ("application/json", "image/svg+xml"):
            mime += "; charset=utf-8"
        return data, mime


def make_handler(preview: FictionalTeacherPreview):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AlliageFictionalTeacher/0"
        sys_version = ""

        def log_message(self, *_args):
            # Neither URL capability nor private filesystem information.
            return

        def respond(self, status: HTTPStatus, data=b"",
                    mime="text/plain; charset=utf-8", send_body=True):
            self.send_response(status)
            for key, value in (
                ("Content-Type", mime),
                ("Content-Length", str(len(data))),
                ("Cache-Control", "no-store"),
                ("X-Content-Type-Options", "nosniff"),
                ("Cross-Origin-Resource-Policy", "same-origin"),
                ("Cross-Origin-Opener-Policy", "same-origin"),
                ("X-Frame-Options", "DENY"),
                ("Referrer-Policy", "no-referrer"),
                ("X-DNS-Prefetch-Control", "off"),
                ("Content-Security-Policy", CSP),
            ):
                self.send_header(key, value)
            self.end_headers()
            if send_body:
                self.wfile.write(data)

        def authorized(self) -> bool:
            port = self.server.server_port
            if self.headers.get("Host") != f"{BIND}:{port}":
                return False
            origin = self.headers.get("Origin")
            if origin is not None and origin != f"http://{BIND}:{port}":
                return False
            if self.headers.get("Sec-Fetch-Site") not in (
                    None, "none", "same-origin"):
                return False
            return True

        def handle_asset(self, send_body=True):
            if not self.authorized():
                return self.respond(HTTPStatus.FORBIDDEN, send_body=send_body)
            # Only byte-exact, preenumerated paths. No queries/fragments or
            # decoding of percent-encoded traversal components.
            if ("?" in self.path or "#" in self.path or len(self.path) > 4096):
                return self.respond(HTTPStatus.NOT_FOUND, send_body=send_body)
            try:
                data, mime = preview.get_asset(self.path)
            except (FileNotFoundError, TeacherHTTPError):
                return self.respond(HTTPStatus.NOT_FOUND, send_body=send_body)
            return self.respond(HTTPStatus.OK, data, mime, send_body=send_body)

        def do_GET(self):
            self.handle_asset()

        def do_HEAD(self):
            self.handle_asset(send_body=False)

        def do_POST(self):
            self.respond(HTTPStatus.METHOD_NOT_ALLOWED)

        def do_OPTIONS(self):
            self.respond(HTTPStatus.METHOD_NOT_ALLOWED)

    return Handler


def make_server(preview: FictionalTeacherPreview) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((BIND, 0), make_handler(preview))
    server.daemon_threads = True
    return server


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description="P3.6B : aperçu HTTP fictif UNIQUEMENT.")
    cli.add_argument("--session", required=True, type=Path)
    args = cli.parse_args(argv)
    try:
        preview = FictionalTeacherPreview(args.session)
        server = make_server(preview)
    except (TeacherHTTPError, OSError, ValueError) as exc:
        cli.exit(2, "REFUSED: " + str(exc) + "\n")
    try:
        print("Alliage — laboratoire FICTIF P3.6B (Ctrl+C pour arrêter).", flush=True)
        print("URL fictive : " + preview.browser_url(server.server_port), flush=True)
        print("Aucun script autorisé ; aucun contenu professeur réel admis.", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
