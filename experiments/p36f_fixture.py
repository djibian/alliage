# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.6F1: two 127.0.0.1-only HTTP servers, entirely fictional.

A serves the only eligible HTML under /p36f-fiction/lesson.html.
B counts GET /probe to establish the negative (without veto)
and positive (with veto) browser experiments. Never binds off loopback.
THIS IS NOT A NETWORK SANDBOX OR A FIREFOX TEST.
"""
from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PATH = "/p36f-fiction/lesson.html"


def create_handler(kind: str, decoy_port: int, counter: dict):
    if kind not in ("a", "b"):
        raise ValueError("Server role must be a or b")

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, mime: str, body: bytes):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; style-src 'unsafe-inline'")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/probe" and kind == "b":
                with counter["lock"]:
                    counter["count"] += 1
                self._send(200, "text/plain; charset=utf-8", b"FICTIONAL_DECOY_RECEIVED")
                return
            if self.path == "/stats" and kind == "b":
                with counter["lock"]:
                    value = counter["count"]
                self._send(200, "application/json",
                           json.dumps({"fictional_decoy_requests": value}).encode())
                return
            if self.path == PATH and kind == "a":
                href = f"http://127.0.0.1:{decoy_port}/probe"
                html = (f'<!doctype html><html lang="fr"><meta charset="utf-8">'
                        f'<title>ALLIAGE_FICTION_ONLY</title>'
                        f'<h1>Fixture P3.6F1, aucune information professeur</h1>'
                        f'<a id="escape" href="{href}">Tentative vers le leurre</a>'
                        f'<a id="newtab" href="{href}" target="_blank">'
                        f'Nouvel onglet fictif</a>'
                        f'<a href="#escape">Fragment interne</a>'
                        f'</html>').encode("utf-8")
                self._send(200, "text/html; charset=utf-8", html)
                return
            self._send(404, "text/plain; charset=utf-8", b"NOT_FOUND")

        def log_message(self, _format, *_args):
            # Do not print URLs, tokens, paths or request bodies.
            return

    return Handler


def start_pair(port: int, decoy_port: int):
    if port == decoy_port:
        raise ValueError("Fixture and decoy ports must differ")
    counter = {"count": 0, "lock": threading.Lock()}
    servers = []
    try:
        for role, p in (("a", port), ("b", decoy_port)):
            server = ThreadingHTTPServer(
                ("127.0.0.1", p), create_handler(role, decoy_port, counter))
            server.daemon_threads = True
            servers.append(server)
        return servers, counter
    except Exception:
        for server in servers:
            server.server_close()
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Laboratoire HTTP 100 % fictif, LOCAL UNIQUEMENT.")
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--decoy-port", type=int, default=18766)
    args = parser.parse_args()
    for p in (args.port, args.decoy_port):
        if not 1024 <= p <= 65535:
            parser.error("Ports locaux 1024..65535 uniquement.")
    servers, _ = start_pair(args.port, args.decoy_port)
    threads = [threading.Thread(target=s.serve_forever, daemon=True)
               for s in servers]
    try:
        for thread in threads:
            thread.start()
        print("P36F1_FIXTURE_HTTP_ONLY; aucun confinement Firefox/OS attesté.")
        print("Arrêt Ctrl+C. Ne jamais utiliser de contenu pédagogique réel.")
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
