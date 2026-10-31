#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""One-shot P3.6B Firefox lab: generate AND serve only a fixed fictional fixture.

No --session or --repo argument is accepted. This script explicitly uses the
public, synthetic TeacherRenderTests fixture in this same Git revision; it
cannot accept a path to a genuine professor session. It is NOT product code.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

from quarto_teacher_http import FictionalTeacherPreview, make_server
from quarto_teacher_render import render, verify_session

# An experimental dependency on the already reviewed, fixed, public fixture.
# Keep it visible: do not generalize this into an arbitrary session importer.
sys.path.insert(0, str(Path(__file__).resolve().parent / "tests"))
from test_quarto_teacher_render import (  # noqa: E402
    SOURCE, STUDENT_ONLY, TEACHER_ONLY, TeacherRenderTests,
)


def create_fixed_fictional_session():
    """Construct real Git+Quarto fixtures entirely from public test literals."""
    fixture = TeacherRenderTests(
        "test_plan_never_executes_quarto_or_writes_source")
    fixture.setUp()
    try:
        source_bytes = (fixture.repo / SOURCE).read_bytes()
        # Positive inspection of the *source to be rendered* in this process.
        if (b"Laboratoire fictif" not in source_bytes
                or TEACHER_ONLY.encode() not in source_bytes
                or STUDENT_ONLY.encode() not in source_bytes
                or fixture.sha != fixture.args()[-1]
                or fixture.args()[1] != "fiction/laboratoire"):
            raise ValueError("La fixture de référence a été modifiée.")
        report = render(*fixture.args(), fixture.output, trusted_quarto=True)
        if (report["resource_id"] !=
                "quarto:fiction/laboratoire:" + SOURCE
                or report["publication_performed"] is not False
                or report["student_deployment_verified"] is not False
                or report["teacher_html_verified"] is not True
                or report["render_profile_effective_verified"] is not False):
            raise ValueError("Échec des garanties de la fixture P3.6A.")
        if verify_session(fixture.output)["status"] != "LOCAL_PROFESSOR_FILES_REHASHED":
            raise ValueError("Sortie Quarto fictive non qualifiée.")
        preview = FictionalTeacherPreview(fixture.output)
        page, mime = preview.get_asset(preview.html_route)
        if (TEACHER_ONLY.encode() not in page
                or STUDENT_ONLY.encode() in page
                or not mime.startswith("text/html")):
            raise ValueError("Les sentinelles fictives ne sont pas conformes.")
        return fixture, preview, report
    except BaseException:
        fixture.doCleanups()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Firefox P3.6B : fixture créée localement, jamais de session privée.")
    parser.add_argument(
        "--trusted-fixture-quarto", action="store_true",
        help="Autoriser Quarto réel uniquement sur la fixture publique embarquée.")
    args = parser.parse_args(argv)
    if not args.trusted_fixture_quarto:
        parser.error("Opt-in --trusted-fixture-quarto obligatoire.")
    if not shutil.which("git") or not shutil.which("quarto"):
        parser.error("Git et Quarto doivent être disponibles localement.")
    # P3.6A's exact .gitignore prediction is qualified only on these versions.
    import subprocess
    version = subprocess.check_output(
        ["quarto", "--version"], text=True, timeout=10).strip()
    if version not in ("1.10.19", "1.10.20"):
        parser.error("Quarto 1.10.19 ou 1.10.20 requis.")

    fixture = None
    server = None
    try:
        fixture, preview, report = create_fixed_fictional_session()
        server = make_server(preview)
        print("=== ALLIAGE P3.6B — FIREFOX FICTIF UNIQUEMENT ===", flush=True)
        print("Quarto :", version, flush=True)
        print("Source : fixture publique intégrée dans tests/test_quarto_teacher_render.py",
              flush=True)
        print("Identité :", report["resource_id"], flush=True)
        print("Fichiers fictifs autorisés :", len(preview.routes), flush=True)
        print("Professeur fictif présent ; sentinelle élève absente : PASS", flush=True)
        print("CSP : scripts et connexions réseau désactivés", flush=True)
        print("URL LOCALE DE TEST (ne pas publier) :",
              preview.browser_url(server.server_port), flush=True)
        print("Ouvrir cette URL dans Firefox de test ; Ctrl+C pour fermer.",
              flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServeur fictif arrêté.", flush=True)
    finally:
        if server is not None:
            server.server_close()
        if fixture is not None:
            fixture.doCleanups()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
