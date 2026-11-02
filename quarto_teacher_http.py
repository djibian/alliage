#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.6B research: serve ONLY fictional P3.6A professor-output fixtures.

This is not authorization to serve genuine professor resources. It does not
authenticate a manifest, sandbox Quarto or verify the effective Quarto profile.
No Git, Quarto, writes, Firefox extension or publication actions.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from types import MappingProxyType
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import stat
from pathlib import Path
from pathlib import PurePosixPath
import secrets
from urllib.parse import quote

from quarto_teacher_render import (
    MAX_RENDERED_BYTES, TeacherRenderError, verify_session,
)

BIND = "127.0.0.1"
PREFIX = "dist/professeur/"
MAX_ASSETS = 2000
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
# Deliberately STATIC: remote resources and every script (including Quarto's
# own) are blocked. Quarto's embed-resources uses data:text/css stylesheets;
# permit only that additional stylesheet scheme, without enabling scripts,
# external stylesheets or network connections. This is still not full fidelity.
CSP = (
    "sandbox allow-same-origin; default-src 'none'; script-src 'none'; "
    "connect-src 'none'; img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline' data:; font-src 'self' data:; "
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
    # Quarto may copy files into its output tree. Inclusion in a generated
    # inventory alone must not grant HTTP access to QMD/source/config files.
    # Reject the session rather than silently omitting required dependencies.
    forbidden_suffixes = {
        ".qmd", ".md", ".ipynb", ".yml", ".yaml", ".toml",
        ".py", ".lua", ".sh",
    }
    forbidden_names = {"manifest.json", ".gitignore", ".env"}
    if (any(part.startswith(".") for part in relative.parts)
            or relative.suffix.lower() in forbidden_suffixes
            or relative.name.lower() in forbidden_names):
        raise TeacherHTTPError("Source ou métadonnée non diffusable.")
    return value


def _seal_asset(session: Path, name: str, size: int, digest: str) -> bytes:
    """Read a single verified file through O_NOFOLLOW dirfds, once at admission.

    Pin directories and the final regular file by open file descriptors. A
    concurrent rename cannot redirect the read to a later symlink target.
    This is POSIX-only; unsupported platforms refuse rather than fall back.
    """
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW"):
        raise TeacherHTTPError("Lecture atomique non prise en charge.")
    dir_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY
    data_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    parts = ("project", *name.split("/"))
    directory = None
    try:
        directory = os.open(session, dir_flags)
        for component in parts[:-1]:
            nextfd = os.open(component, dir_flags, dir_fd=directory)
            os.close(directory)
            directory = nextfd
        fd = os.open(parts[-1], data_flags, dir_fd=directory)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_size != size:
                raise TeacherHTTPError("Actif Quarto non régulier ou altéré.")
            # fdopen closes exactly the verified descriptor on all outcomes.
            with os.fdopen(fd, "rb", closefd=True) as stream:
                fd = -1
                data = stream.read(size + 1)
        finally:
            if fd != -1:
                os.close(fd)
    except OSError as exc:
        raise TeacherHTTPError("Lecture sûre de l'actif refusée.") from exc
    finally:
        if directory is not None:
            os.close(directory)
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise TeacherHTTPError("SHA-256 d'actif professeur modifié.")
    return data


def _assert_verified_manifest_unchanged(session: Path, expected_sha256: str) -> None:
    """Only compare a later manifest to the validated bytes; never parse it.

    This is a drift detector, NOT an atomic provenance claim. If the file
    changes after the check, the HTTP routes remain tied to the original
    verified manifest and the already sealed immutable asset bytes.
    """
    dir_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    directory = None
    fd = -1
    try:
        directory = os.open(session, dir_flags)
        fd = os.open("manifest.json", flags, dir_fd=directory)
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode)
                or st.st_size > MAX_MANIFEST_BYTES):
            raise TeacherHTTPError("Manifeste changé après vérification.")
        with os.fdopen(fd, "rb", closefd=True) as stream:
            fd = -1
            data = stream.read(MAX_MANIFEST_BYTES + 1)
    except OSError as exc:
        raise TeacherHTTPError("Manifeste non vérifiable après admission.") from exc
    finally:
        if fd != -1:
            os.close(fd)
        if directory is not None:
            os.close(directory)
    if (len(data) > MAX_MANIFEST_BYTES
            or hashlib.sha256(data).hexdigest() != expected_sha256):
        raise TeacherHTTPError("Manifeste changé après vérification.")


@dataclass(frozen=True, slots=True, init=False, eq=False, repr=False)
class FictionalTeacherPreview:
    """Frozen professor-output snapshot; public fields cannot be reassigned.

    Dataclass freezing protects ordinary consumers, not arbitrary Python code
    using object.__setattr__, monkeypatching methods or process memory.
    """
    session: Path
    prefix: str
    html_route: str
    routes: MappingProxyType


    def __init__(self, session: Path):
        object.__setattr__(self, "session", Path(session).expanduser().absolute())
        # verify_session checks the real P3.6A HTML identity, symlinks, exact
        # inventory and SHA-256. The manifest is local, NOT signed or trusted.
        try:
            proof = verify_session(self.session, include_manifest=True)
            # C1: the exact object validated by P3.6A, NOT a second manifest
            # read that a concurrent writer could substitute.
            report = proof["verified_manifest"]
            manifest_sha256 = proof["verified_manifest_sha256"]
        except (TeacherRenderError, OSError, ValueError, TypeError, KeyError) as exc:
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
        object.__setattr__(self, "prefix", "/alliage-professor-fixture-" + secrets.token_hex(16))
        # P3.6D: only the single verified HTML may have an HTTP route.
        # Quarto's synthetic embed-resources HTML needs no external assets.
        # Other output files are rehashed by verify_session, but cannot be
        # loaded over HTTP even if renamed to an innocent-looking extension.
        routes: dict[str, tuple[bytes, str]] = {}
        html_name = _asset_name(html["path"])
        if not html_name.lower().endswith(".html"):
            raise TeacherHTTPError("Identité HTML non admise.")
        total = 0
        seen: set[str] = set()
        for item in files:
            if not isinstance(item, dict):
                raise TeacherHTTPError("Entrée de manifeste invalide.")
            name = _asset_name(item.get("path"))
            size = item.get("bytes")
            digest = item.get("sha256")
            if type(size) is not int or size < 0 or not isinstance(digest, str):
                raise TeacherHTTPError("Entrée de manifeste non vérifiable.")
            total += size
            if total > MAX_RENDERED_BYTES:
                raise TeacherHTTPError("Budget de sortie Quarto dépassé.")
            route = self.prefix + "/" + quote(name, safe="/")
            if route in seen:
                raise TeacherHTTPError("Collision de chemins professeur.")
            seen.add(route)
            if name == html_name:
                data = _seal_asset(self.session, name, size, digest)
                routes[route] = (data, "text/html; charset=utf-8")
        html_route = self.prefix + "/" + quote(html_name, safe="/")
        if len(routes) != 1 or html_route not in routes:
            raise TeacherHTTPError("HTML professeur absent de l'inventaire.")
        # Detect a manifest swap during admission, without ever consuming it
        # for authorization. Later swaps cannot affect sealed route bytes.
        _assert_verified_manifest_unchanged(self.session, manifest_sha256)
        object.__setattr__(self, "html_route", html_route)
        object.__setattr__(self, "routes", MappingProxyType(routes))

    def browser_url(self, port: int) -> str:
        return f"http://{BIND}:{port}{self.html_route}"

    def get_asset(self, path: str) -> tuple[bytes, str]:
        asset = self.routes.get(path)
        if asset is None:
            raise FileNotFoundError("Route non autorisée.")
        return asset  # sealed immutable bytes; no filesystem access on GET/HEAD


def make_handler(preview: FictionalTeacherPreview):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AlliageFictionalTeacher/0"
        sys_version = ""

        def parse_request(self):
            # CPython normalizes request-targets starting with // to /.
            # Keep a verdict on the *raw* target before its normalization.
            raw = self.raw_requestline.rstrip(b"\r\n").split(b" ")
            self._noncanonical_target = (
                len(raw) != 3 or not raw[1].startswith(b"/")
                or raw[1].startswith(b"//")
                or b"\\" in raw[1] or b"\x00" in raw[1]
            )
            return super().parse_request()

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
            if self._noncanonical_target:
                return False
            port = self.server.server_port
            host = self.headers.get_all("Host", [])
            if host != [f"{BIND}:{port}"]:
                return False
            origins = self.headers.get_all("Origin", [])
            if len(origins) > 1 or (origins and origins[0] != f"http://{BIND}:{port}"):
                return False
            sites = self.headers.get_all("Sec-Fetch-Site", [])
            if len(sites) > 1 or (sites and sites[0] not in ("none", "same-origin")):
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
    # No caller-selected --session: manifest's 'fiction' label is forgeable.
    # The ONLY supported entry point creates public fixtures in this process.
    cli = argparse.ArgumentParser(
        description="P3.6C: ne pas importer de session Quarto arbitraire.")
    cli.parse_args(argv)
    cli.error("Accès direct refusé : lancer p36b_fictional_firefox_demo.py.")


if __name__ == "__main__":
    raise SystemExit(main())
