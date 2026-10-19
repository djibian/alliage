#!/usr/bin/env python3
"""Alliage v0.4: interface locale étroitement limitée au pilote Quarto.

Pas d'API IA, pas de modification du dépôt, pas de publication.
"""
from __future__ import annotations
import argparse
import hashlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import threading
from urllib.parse import urlsplit, unquote

from experiment import prepare, RenderError
from resolve_source import LocalizationError, git

PILOT_URL = "https://djibian.github.io/pedagogie/enseignements/tim/4e-3e/activites/3e/02-nommer-classer/activite.html"
PILOT_REL = "enseignements/tim/4e-3e/activites/3e/02-nommer-classer/activite.qmd"
IDENTIFIER = re.compile(r"^[0-9a-f]{32}$")
ALLOWED_FILES = {".html", ".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico"}


def require_pilot(capture: object):
    if not isinstance(capture, dict) or capture.get("schema") != "pedagolab.selection.v0":
        raise ValueError("Sélection Alliage v0 (schéma hérité) requise.")
    page = capture.get("page")
    if not isinstance(page, dict) or page.get("url") != PILOT_URL:
        raise ValueError("Prototype limité à la page exacte Mission 02 publiée.")
    dom = capture.get("dom")
    quote = capture.get("quote")
    if not isinstance(dom, dict) or not isinstance(quote, dict):
        raise ValueError("Sélection invalide.")
    if not dom.get("exactMatchesBlockSlice") or not isinstance(quote.get("exact"), str):
        raise ValueError("Sélection imprécise ou vide.")
    if len(quote["exact"]) > 150 or not quote["exact"].strip():
        raise ValueError("Sélection trop longue ou vide pour le prototype.")
    return capture


def select_guard(capture: dict, source_root: Path) -> list[Path]:
    """Garde témoin fixe sur l'autre occurrence pour les deux ancres qualifiées."""
    selected = capture["dom"].get("cssPath")
    pairs = {
        "#je-prépare-les-cinq-ressources > p:nth-of-type(2)": "selection-2.json",
        "#validation > ul > li:nth-of-type(1)": "selection-1.json",
    }
    if capture["quote"]["exact"] != "cinq fichiers" or selected not in pairs:
        return []
    path = source_root / "local-anchors" / pairs[selected]
    return [path] if path.is_file() else []


class Service:
    def __init__(self, repo: Path, out: Path, token: str, source_root: Path):
        self.repo = repo.expanduser().resolve(strict=True)
        self.out = out.expanduser().resolve()
        self.token = token
        self.source_root = source_root
        self.commit = git(self.repo, "rev-parse", "HEAD")
        self.lock = threading.RLock()
        self.sessions: dict[str, dict] = {}
        if self.repo == self.out or self.repo in self.out.parents:
            raise ValueError("Le dossier expérimental ne doit pas être dans le dépôt Git.")
        if self.out == self.repo.parent:
            raise ValueError("Le dossier expérimental doit être distinct du dépôt.")
        if not (self.repo / PILOT_REL).is_file():
            raise ValueError("La source Quarto attendue est absente.")
        # Découverte sans création: le premier essai crée seulement le dossier local.

    def experiment(self, payload: dict) -> dict:
        capture = require_pilot(payload.get("selection"))
        proposal_a = payload.get("optionA")
        proposal_b = payload.get("optionB")
        if not isinstance(proposal_a, str) or not isinstance(proposal_b, str):
            raise ValueError("Deux propositions textuelles sont nécessaires.")
        if len(proposal_a) > 150 or len(proposal_b) > 150:
            raise ValueError("Une proposition dépasse 150 caractères.")
        with self.lock:
            identifier = secrets.token_hex(16)
            output = self.out / identifier
            report = prepare(self.repo, output, capture, ["A=" + proposal_a, "B=" + proposal_b],
                             select_guard(capture, self.source_root), self.commit, True)
            if report["status"] != "RENDER_VERIFIED_LOCAL":
                raise RenderError("Rendu local non vérifié.")
            self.sessions[identifier] = report
            return {
                "status": "RENDER_VERIFIED_LOCAL",
                "id": identifier,
                "comparison_url": f"http://127.0.0.1:8765/experiences/{identifier}/comparaison.html",
                "report": report,
                "warning": "HTML public non relié cryptographiquement au commit ; aucune publication."
            }

    def decision(self, payload: dict) -> dict:
        identifier = payload.get("id")
        choice = payload.get("choice")
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
            raise ValueError("Identifiant expérimental invalide.")
        if choice not in ["A", "B", "REJETER"]:
            raise ValueError("Choisir A, B ou REJETER.")
        with self.lock:
            report = self.sessions.get(identifier)
            if report is None:
                raise ValueError("Expérience absente de cette session ; recommence la comparaison.")
            report_file = self.out / identifier / "rapport.json"
            if not report_file.is_file():
                raise ValueError("Rapport expérimental disparu.")
            persisted = json.loads(report_file.read_text(encoding="utf-8"))
            if persisted != report:
                raise ValueError("Rapport modifié après vérification : décision refusée.")
            chosen = next((r for r in report["options"] if r["option"] == choice), None)
            if chosen:
                file_path = self.out / identifier / chosen["qmd"]
                if hashlib.sha256(file_path.read_bytes()).hexdigest() != chosen["patched_qmd_sha256"]:
                    raise ValueError("Variante modifiée après vérification : décision refusée.")
            decision = {
                "schema": "pedagolab.decision.v0",
                "status": "REJECTED_LOCAL" if choice == "REJETER" else "SELECTED_EXPERIMENTAL_ONLY",
                "choice": choice,
                "source_commit": report["source"]["commit"],
                "source_sha256": report["source"]["sha256"],
                "selected_qmd": chosen["qmd"] if chosen else None,
                "selected_qmd_sha256": chosen["patched_qmd_sha256"] if chosen else None,
                "production_write": False,
                "publication": "NOT_PUBLISHED",
            }
            target = self.out / identifier / "decision.json"
            # Historique local : un fichier immutable par décision, puis dernier état.
            index = 1
            while (self.out / identifier / f"decision-{index:03d}.json").exists():
                index += 1
            record = self.out / identifier / f"decision-{index:03d}.json"
            serialized = json.dumps(decision, ensure_ascii=False, indent=2) + "\n"
            with open(record, "x", encoding="utf-8") as fd:
                fd.write(serialized)
                fd.flush()
                os.fsync(fd.fileno())
            temp = self.out / identifier / (".decision-" + secrets.token_hex(8))
            temp.write_text(serialized, encoding="utf-8")
            os.replace(temp, target)
            return decision

    def preview(self, url_path: str) -> tuple[bytes, str]:
        parts = unquote(urlsplit(url_path).path).split("/")
        if len(parts) < 4 or parts[1] != "experiences" or not IDENTIFIER.fullmatch(parts[2]):
            raise FileNotFoundError()
        if parts[2] not in self.sessions or any(p in ("", ".", "..") for p in parts[3:]):
            raise FileNotFoundError()
        candidate = (self.out / parts[2] / Path(*parts[3:])).resolve()
        base = (self.out / parts[2]).resolve()
        if base not in candidate.parents or candidate.suffix.lower() not in ALLOWED_FILES:
            raise FileNotFoundError()
        if not candidate.is_file():
            raise FileNotFoundError()
        mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if mime.startswith("text/") or mime == "application/javascript":
            mime += "; charset=utf-8"
        return candidate.read_bytes(), mime


def make_handler(service: Service):
    class Handler(BaseHTTPRequestHandler):
        server_version = "Alliage/0.4"
        def log_message(self, *_args):
            return # ne jamais journaliser jetons ou ressources
        def send_json(self, code, body):
            encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(encoded)
        def trusted_host(self):
            return self.headers.get("Host") == "127.0.0.1:8765"
        def do_GET(self):
            if not self.trusted_host():
                return self.send_json(HTTPStatus.FORBIDDEN, {"error": "HOST_REFUSED"})
            if urlsplit(self.path).path == "/api/health":
                return self.send_json(HTTPStatus.OK, {"status": "READY_LOCAL", "revision": service.commit, "schema": "pedagolab.bridge.v0"})
            try:
                content, mime = service.preview(self.path)
            except (FileNotFoundError, ValueError, OSError):
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "NOT_FOUND"})
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(content)
        def do_POST(self):
            if not self.trusted_host():
                return self.send_json(HTTPStatus.FORBIDDEN, {"error": "HOST_REFUSED"})
            origin = self.headers.get("Origin")
            if origin and not (origin.startswith("moz-extension://") or origin.startswith("chrome-extension://")):
                return self.send_json(HTTPStatus.FORBIDDEN, {"error": "ORIGIN_REFUSED"})
            supplied = self.headers.get("X-Pedagolab-Token", "")
            if not hmac.compare_digest(supplied, service.token):
                return self.send_json(HTTPStatus.FORBIDDEN, {"error": "TOKEN_REFUSED"})
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self.send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "JSON_REQUIRED"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 24_000:
                    raise ValueError("Payload trop grand ou absent.")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("Objet JSON attendu.")
                if self.path == "/api/experiment":
                    result = service.experiment(payload)
                elif self.path == "/api/decision":
                    result = service.decision(payload)
                else:
                    return self.send_json(HTTPStatus.NOT_FOUND, {"error": "NOT_FOUND"})
            except (LocalizationError, RenderError, OSError, ValueError, KeyError, json.JSONDecodeError) as err:
                reason = err.reason if isinstance(err, LocalizationError) else type(err).__name__
                return self.send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"status": "REFUSED", "reason": reason, "detail": str(err)[:500]})
            return self.send_json(HTTPStatus.OK, result)
    return Handler


def main():
    parser = argparse.ArgumentParser(description="Alliage — pont local pour le pilote Quarto")
    parser.add_argument("--repo", type=Path, required=True, help="Copie locale persistante du dépôt pédagogique (jamais copiée dans Alliage)")
    parser.add_argument("--out", type=Path, default=Path.home() / "alliage-experiences" / "interactif")
    args = parser.parse_args()
    token = secrets.token_urlsafe(24)
    if not args.repo.expanduser().is_dir():
        parser.error(f"Dépôt source introuvable : {args.repo}. Le répertoire /tmp peut disparaître après redémarrage ; clone le dépôt dans ~/projets/pedagogie, puis indique --repo.")
    service = Service(args.repo, args.out, token, Path(__file__).parent)
    server = ThreadingHTTPServer(("127.0.0.1", 8765), make_handler(service))
    print("Alliage v0.4 — local uniquement, aucune écriture dans le dépôt.", flush=True)
    print("URL : http://127.0.0.1:8765/api/health", flush=True)
    print("Jeton temporaire (à coller dans l'extension) : " + token, flush=True)
    print("Arrêt : Ctrl+C", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
