#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Serve only attested Quarto _site assets on loopback for an opt-in Firefox test.

Ephemeral read-only transport. No Git, rendering, API, write or publication.
The unguessable URL prefix is a local capability, not user authentication.
"""
from __future__ import annotations

import argparse
import hashlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import secrets
import threading
from urllib.parse import quote, urlsplit

from quarto_navigation import NavigationError, _load_version, _regular_within
from quarto_resource_entry import resource_entry_url

BIND = "127.0.0.1"
MAX_QUERY = 4096
ASSET_PREFIX = "project/_site/"


class HTTPPreviewError(ValueError):
    """Refuse unsafe, ambiguous or no-longer-attested local preview assets."""


class AttestedPreview:
    """Snapshot of the verified generated files, with rehashing on every GET."""

    def __init__(self, session: Path, resource_id: str):
        self.session = Path(session).expanduser().absolute()
        # Reuse P3.4's strict session location, .qmd identities and both
        # version checks. The query is still *declared*, not a signed claim.
        file_url = resource_entry_url(self.session, resource_id=resource_id)
        self.query = urlsplit(file_url).query
        self.prefix = "/alliage-local-" + secrets.token_hex(16)
        self.routes: dict[str, tuple[str, str, int, str]] = {}
        for version in ("V1", "V2"):
            info = _load_version(self.session, version)
            if (info["source_path"] != "activite.qmd" or
                    info["rendered_html_path"] != ASSET_PREFIX + "activite.html" or
                    not info["rendered_files_verified"] or
                    not info["rendered_css_verified"]):
                raise HTTPPreviewError("Révision Quarto non attestée.")
            manifest = self.session / version / "manifest.json"
            report = json.loads(manifest.read_text(encoding="utf-8"))
            for asset in report["rendered_files"]:
                name = asset["path"]
                if not isinstance(name, str) or not name.startswith(ASSET_PREFIX):
                    raise HTTPPreviewError("Dépendance Quarto non autorisée.")
                relative = name[len(ASSET_PREFIX):]
                endpoint = (self.prefix + "/" + version + "/" +
                            ASSET_PREFIX + quote(relative, safe="/"))
                if endpoint in self.routes:
                    raise HTTPPreviewError("Collision entre routes Quarto.")
                self.routes[endpoint] = (
                    version, name, asset["bytes"], asset["sha256"])

    def browser_url(self, port: int) -> str:
        return (f"http://{BIND}:{port}{self.prefix}/V2/"
                + ASSET_PREFIX + "activite.html?" + self.query)

    def get_asset(self, request_path: str) -> tuple[bytes, str]:
        record = self.routes.get(request_path)
        if record is None:
            raise FileNotFoundError("Route non autorisée.")
        version, name, size, expected_hash = record
        # Checks each component for symlinks and rejects nonregular/oversized
        # assets. SHA verification also detects same-size post-start tampering.
        try:
            candidate = _regular_within(self.session / version, name)
            if candidate.stat().st_size != size:
                raise HTTPPreviewError("Taille des fichiers Quarto altérée.")
            data = candidate.read_bytes()
        except (NavigationError, OSError) as exc:
            raise HTTPPreviewError("Fichier Quarto indisponible.") from exc
        if len(data) != size or hashlib.sha256(data).hexdigest() != expected_hash:
            raise HTTPPreviewError("Intégrité de fichier Quarto perdue.")
        suffix = candidate.suffix.lower()
        if suffix in (".js", ".mjs"):
            mime = "text/javascript"
        elif suffix == ".css":
            mime = "text/css"
        else:
            mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if mime.startswith("text/") or mime in ("application/json", "image/svg+xml"):
            mime += "; charset=utf-8"
        return data, mime


def make_handler(preview: AttestedPreview, refresh_callback=None):
    # Keep the verified asset inventory immutable for each preview. Only an
    # explicitly enabled, successful refresh atomically swaps this pointer.
    state = {"preview": preview, "nonce": None}
    gate = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = "AlliageHistoricalPreview/0"
        sys_version = ""

        def log_message(self, *_args):
            # Never log the secret URL prefix, query or local file paths.
            return

        def respond(self, code: HTTPStatus, data=b"", mime="text/plain; charset=utf-8",
                    send_body=True):
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            if send_body:
                self.wfile.write(data)

        def authorized_request(self):
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
            if not self.authorized_request():
                return self.respond(HTTPStatus.FORBIDDEN, send_body=send_body)
            # The URL prefix is a capability, not an authentication mechanism.
            # Only exact routes present in P3.1's inventory are accessible.
            path, sep, query = self.path.partition("?")
            if len(query) > MAX_QUERY or (sep and "#" in query):
                return self.respond(HTTPStatus.NOT_FOUND, send_body=send_body)
            try:
                content, mime = state["preview"].get_asset(path)
            except (FileNotFoundError, HTTPPreviewError):
                return self.respond(HTTPStatus.NOT_FOUND, send_body=send_body)
            return self.respond(HTTPStatus.OK, content, mime, send_body)

        def control_request_allowed(self, require_origin=False):
            if not self.authorized_request():
                return False
            if self.headers.get("Sec-Fetch-Site") != "same-origin":
                return False
            if self.headers.get("X-Alliage-Intent") != "user-click":
                return False
            if require_origin:
                expected = f"http://{BIND}:{self.server.server_port}"
                if self.headers.get("Origin") != expected:
                    return False
            return True

        def respond_json(self, code, payload):
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.respond(code, data, "application/json; charset=utf-8")

        def do_GET(self):
            active = state["preview"]
            capability_path = active.prefix + "/_alliage/refresh-capability"
            if refresh_callback is not None and self.path == capability_path:
                # Only the explicitly enabled PUBLIC/FICTIONAL demo has a
                # control endpoint. Reject non-browser and cross-site requests.
                if not self.control_request_allowed():
                    return self.respond(HTTPStatus.FORBIDDEN)
                if not gate.acquire(blocking=False):
                    return self.respond(HTTPStatus.CONFLICT)
                try:
                    state["nonce"] = secrets.token_urlsafe(32)
                    self.respond_json(HTTPStatus.OK, {"token": state["nonce"]})
                finally:
                    gate.release()
                return
            self.handle_asset()

        def do_HEAD(self):
            self.handle_asset(send_body=False)

        def do_POST(self):
            if refresh_callback is None:
                return self.respond(HTTPStatus.METHOD_NOT_ALLOWED)
            active = state["preview"]
            if self.path != active.prefix + "/_alliage/refresh":
                return self.respond(HTTPStatus.NOT_FOUND)
            if not self.control_request_allowed(require_origin=True):
                return self.respond(HTTPStatus.FORBIDDEN)
            # No request body, query, JSON payload, user-provided ref or path.
            if (self.headers.get("Transfer-Encoding") is not None or
                    self.headers.get("Content-Length") not in (None, "0")):
                return self.respond(HTTPStatus.BAD_REQUEST)
            if not gate.acquire(blocking=False):
                return self.respond(HTTPStatus.CONFLICT)
            try:
                provided = self.headers.get("X-Alliage-Refresh-Token", "")
                nonce = state["nonce"]
                if not nonce or not secrets.compare_digest(provided, nonce):
                    return self.respond(HTTPStatus.FORBIDDEN)
                # Consume before any Git or Quarto operation. A replay with
                # the same capability is never accepted.
                state["nonce"] = None
                try:
                    updated = refresh_callback(active)
                    if updated is None:
                        return self.respond_json(HTTPStatus.OK,
                                                 {"state": "unchanged"})
                    if (not isinstance(updated, AttestedPreview) or
                            updated.query == "" or
                            updated.query.split("=", 1)[0] !=
                                active.query.split("=", 1)[0]):
                        raise HTTPPreviewError("Aperçu actualisé non attesté.")
                    # Keep existing GET routes live until all Git+Quarto
                    # verification succeeded; then publish the new inventory.
                    state["preview"] = updated
                    self.respond_json(HTTPStatus.OK, {
                        "state": "updated",
                        "url": updated.browser_url(self.server.server_port)})
                except Exception:
                    # A rendering subprocess can raise CalledProcessError or
                    # other failures; fail closed, keep the old preview, and
                    # never expose paths, tracebacks or tokens to Firefox.
                    self.respond_json(HTTPStatus.UNPROCESSABLE_ENTITY, {
                        "state": "error",
                        "message": "Actualisation Git/Quarto refusée ; ancienne comparaison conservée."})
            finally:
                gate.release()

        def do_OPTIONS(self):
            self.respond(HTTPStatus.METHOD_NOT_ALLOWED)

    return Handler


def make_server(preview: AttestedPreview, refresh_callback=None) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((BIND, 0),
                                 make_handler(preview, refresh_callback))
    server.daemon_threads = True
    return server


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aperçu Quarto HTTP local éphémère, lecture seule, sans publication.")
    parser.add_argument("--session", required=True, type=Path,
                        help="Session fictive p31-final-observed-* déjà rendue.")
    parser.add_argument("--resource-id", required=True,
                        help="Identité déclarée, ex. quarto:fiction/laboratoire:activite.qmd")
    args = parser.parse_args()
    try:
        preview = AttestedPreview(args.session, args.resource_id)
        server = make_server(preview)
    except (NavigationError, HTTPPreviewError, OSError, ValueError) as exc:
        parser.exit(2, "REFUSED: " + str(exc) + "\n")
    try:
        print("Alliage — HTTP loopback temporaire (Ctrl+C pour arrêter).", flush=True)
        print("URL ressource : " + preview.browser_url(server.server_port), flush=True)
        print("Les fichiers sont rehashés à chaque réponse ; aucune publication.", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
