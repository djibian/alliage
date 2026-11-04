#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pareto pilot: one explicit local command after an authorized Git fetch.

Reuse P3.3 -> P3.1 -> P3.2 and HTTP verified assets. No AI API,
Git fetch, checkout, commit, merge, publication or implicit browser launch.
Only for an explicitly trusted, entirely PUBLIC/FICTIONAL Quarto project.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from quarto_local_http import AttestedPreview, make_server
from quarto_observed_session import create_observed_session

SHA = re.compile(r"[0-9a-f]{40}\Z")
TRACKED_BRANCH = re.compile(
    r"refs/remotes/origin/experiment/[a-zA-Z0-9][a-zA-Z0-9._/-]*\Z"
)


class DemoRefused(ValueError):
    """Unsafe or ambiguous pilot usage: fail without touching a repository."""


def validate_inputs(repository_id: str, baseline_sha: str, tracking_ref: str,
                    consent: bool) -> None:
    if consent is not True:
        raise DemoRefused("Confirmer explicitement le projet Quarto public/fictif de confiance.")
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", repository_id):
        raise DemoRefused("Identité Git déclarée owner/repo requise.")
    if SHA.fullmatch(baseline_sha) is None:
        raise DemoRefused("SHA complet de référence obligatoire.")
    if (TRACKED_BRANCH.fullmatch(tracking_ref) is None or
            ".." in tracking_ref or "//" in tracking_ref or
            tracking_ref.endswith(("/", ".", ".lock"))):
        raise DemoRefused("Branche de suivi origin/experiment/* explicite obligatoire.")


def prepare(repo: Path, repository_id: str, tracking_ref: str,
            baseline_sha: str, *, public_fictional_trusted: bool):
    validate_inputs(repository_id, baseline_sha, tracking_ref,
                    public_fictional_trusted)
    # The underlying experiment verifies a FAST_FORWARD and renders two
    # Git-pinned snapshots under HOME; it never calls Git fetch.
    result = create_observed_session(
        repo, repository_id, "activite.qmd", tracking_ref, baseline_sha,
        trusted_quarto=True,
    )
    preview = AttestedPreview(Path(result["session_path"]), result["resource_id"])
    server = make_server(preview)  # ephemeral 127.0.0.1 only
    return result, preview, server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Comparer deux révisions Quarto publiques/fictives en une commande locale.")
    parser.add_argument("--repo", type=Path, required=True,
                        help="Racine exacte du clone Git autorisé")
    parser.add_argument("--repository-id", required=True, help="owner/repo déclaré")
    parser.add_argument("--tracking-ref", required=True,
                        help="refs/remotes/origin/experiment/<branche> récupérée explicitement")
    parser.add_argument("--baseline-sha", required=True,
                        help="SHA40 avant la modification Git de l'IA")
    parser.add_argument("--public-fictional-trusted", action="store_true",
                        help="J'atteste une ressource exclusivement publique/fictive et Quarto de confiance")
    args = parser.parse_args(argv)
    try:
        result, preview, server = prepare(
            args.repo, args.repository_id, args.tracking_ref,
            args.baseline_sha, public_fictional_trusted=args.public_fictional_trusted)
    except (ValueError, OSError) as exc:
        parser.exit(2, "REFUSED: " + str(exc) + "\n")
    try:
        print("Alliage — Quarto réellement rendu depuis deux SHA Git ; aucune publication.", flush=True)
        print("Référence Git : " + result["baseline_commit"], flush=True)
        print("Proposition Git : " + result["observed_commit"], flush=True)
        print("Aucun fetch automatique ; la branche suivie est une copie locale.", flush=True)
        print("Ressource à ouvrir dans Firefox : " +
              preview.browser_url(server.server_port), flush=True)
        print("Choisir V1/V2 dans la page ; Ctrl+C arrête le serveur local.", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
