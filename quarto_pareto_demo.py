#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pareto pilot: one explicit local command for two Git-pinned Quarto renders.

Reuse P3.3 -> P3.1 -> P3.2 and HTTP verified assets. No AI API,
implicit Git fetch, checkout, commit, merge, publication or browser launch.
An opt-in --fetch-demo is limited to the trusted PUBLIC/FICTIONAL branch.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

from quarto_versions import _git

from quarto_local_http import AttestedPreview, make_server
from quarto_observed_session import create_observed_session

SHA = re.compile(r"[0-9a-f]{40}\Z")
TRACKED_BRANCH = re.compile(
    r"refs/remotes/origin/experiment/[a-zA-Z0-9][a-zA-Z0-9._/-]*\Z"
)
PUBLIC_DEMO_REPOSITORY = "djibian/alliage"
PUBLIC_DEMO_TRACKING_REF = "refs/remotes/origin/experiment/pareto-quarto-demo"


class DemoRefused(ValueError):
    """Unsafe or ambiguous pilot usage: refuse a demo operation."""


def verify_public_demo_clone(repo: Path) -> Path:
    """Fail before executing trusted-demo Quarto if clone/origin is wrong.

    This checks the local Git configuration, not cryptographic provenance of
    every commit on a local tracking ref. No network or fetch happens here.
    """
    repo = Path(repo).expanduser().resolve(strict=True)
    root = _git(repo, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    if Path(root).resolve(strict=True) != repo:
        raise DemoRefused("Racine Git exacte requise.")
    remote = _git(repo, "remote", "get-url", "origin").decode("utf-8").strip()
    if remote not in ("https://github.com/djibian/alliage.git",
                      "git@github.com:djibian/alliage.git"):
        raise DemoRefused("Origine GitHub différente de la démonstration publique attendue.")
    return repo


def fetch_fictional_demo(repo: Path, repository_id: str, tracking_ref: str) -> str:
    """One user-initiated fetch, tightly bound to the public demo branch.

    Returns the FULL local tracking SHA *before* fetching, for V1.
    Never touches the checkout, creates commits or publishes to GitHub.
    """
    if (repository_id != PUBLIC_DEMO_REPOSITORY or
            tracking_ref != PUBLIC_DEMO_TRACKING_REF):
        raise DemoRefused("Actualisation autorisée uniquement sur la branche de démonstration fictive.")
    repo = verify_public_demo_clone(repo)
    before = _git(repo, "rev-parse", "--verify", tracking_ref + "^{commit}").decode("ascii").strip()
    if SHA.fullmatch(before) is None:
        raise DemoRefused("Ancien SHA de suivi absent ou invalide.")
    command = [
        "git", "-C", str(repo), "fetch", "--no-tags", "origin",
        "refs/heads/experiment/pareto-quarto-demo:" + tracking_ref,
    ]
    try:
        fetched = subprocess.run(command, capture_output=True, timeout=90,
                                 env={**os.environ, "GIT_TERMINAL_PROMPT": "0",
                                      "GIT_NO_LAZY_FETCH": "1"})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DemoRefused("Actualisation Git explicite impossible.") from exc
    if fetched.returncode:
        raise DemoRefused("Actualisation Git refusée ; aucun rendu lancé.")
    return before


def validate_inputs(repository_id: str, baseline_sha: str, tracking_ref: str,
                    consent: bool) -> None:
    if consent is not True:
        raise DemoRefused("Confirmer explicitement le projet Quarto public/fictif de confiance.")
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", repository_id):
        raise DemoRefused("Identité Git déclarée owner/repo requise.")
    parts = repository_id.split("/")
    if any(part.startswith(".") or part.endswith(".") or ".." in part
           for part in parts):
        raise DemoRefused("Segments de dépôt Git ambigus ou dangereux.")
    if SHA.fullmatch(baseline_sha) is None:
        raise DemoRefused("SHA complet de référence obligatoire.")
    if (TRACKED_BRANCH.fullmatch(tracking_ref) is None or
            ".." in tracking_ref or "//" in tracking_ref or
            tracking_ref.endswith(("/", ".", ".lock"))):
        raise DemoRefused("Branche de suivi origin/experiment/* explicite obligatoire.")


def prepare_preview(repo: Path, repository_id: str, tracking_ref: str,
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
    return result, preview


def prepare(repo: Path, repository_id: str, tracking_ref: str,
            baseline_sha: str, *, public_fictional_trusted: bool):
    result, preview = prepare_preview(
        repo, repository_id, tracking_ref, baseline_sha,
        public_fictional_trusted=public_fictional_trusted)
    server = make_server(preview)  # ephemeral 127.0.0.1 only
    return result, preview, server


def browser_refresh_callback(repo: Path, observed_sha: str):
    """Revalidate ONE public Git origin and refresh only after an HTTP click.

    Keep the last successfully rendered SHA if Git advanced but rendering
    failed. This allows retrying the same commit without dropping V1.
    """
    state = {"observed": observed_sha}

    def update(_current_preview: AttestedPreview):
        fetch_fictional_demo(repo, PUBLIC_DEMO_REPOSITORY,
                             PUBLIC_DEMO_TRACKING_REF)
        remote = _git(repo, "rev-parse", "--verify",
                      PUBLIC_DEMO_TRACKING_REF + "^{commit}").decode("ascii").strip()
        if not SHA.fullmatch(remote):
            raise DemoRefused("SHA de branche invalide.")
        if remote == state["observed"]:
            return None
        result, new_preview = prepare_preview(
            repo, PUBLIC_DEMO_REPOSITORY, PUBLIC_DEMO_TRACKING_REF,
            state["observed"], public_fictional_trusted=True)
        if result["observed_commit"] != remote:
            raise DemoRefused("Branche Git déplacée pendant le rendu.")
        state["observed"] = result["observed_commit"]
        return new_preview

    return update


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Comparer deux révisions Quarto publiques/fictives en une commande locale.")
    parser.add_argument("--repo", type=Path, required=True,
                        help="Racine exacte du clone Git autorisé")
    parser.add_argument("--demo", action="store_true",
                        help="Raccourci vers le SEUL dépôt et la branche fictifs publics autorisés")
    parser.add_argument("--repository-id", help="owner/repo déclaré")
    parser.add_argument("--tracking-ref",
                        help="refs/remotes/origin/experiment/<branche> récupérée explicitement")
    parser.add_argument("--baseline-sha",
                        help="SHA40 avant modification ; omissible avec --fetch-demo")
    parser.add_argument("--fetch-demo", action="store_true",
                        help="Récupérer explicitement la seule branche publique fictive puis comparer depuis l'ancien SHA local")
    parser.add_argument("--browser-refresh", action="store_true",
                        help="Autoriser un clic volontaire Firefox à déclencher UN fetch et deux rendus Quarto de la fixture publique")
    parser.add_argument("--public-fictional-trusted", action="store_true",
                        help="J'atteste une ressource exclusivement publique/fictive et Quarto de confiance")
    args = parser.parse_args(argv)
    try:
        if args.demo:
            if args.repository_id not in (None, PUBLIC_DEMO_REPOSITORY):
                raise DemoRefused("--demo ne permet pas un autre dépôt Git.")
            if args.tracking_ref not in (None, PUBLIC_DEMO_TRACKING_REF):
                raise DemoRefused("--demo ne permet pas une autre branche Git.")
            args.repository_id = PUBLIC_DEMO_REPOSITORY
            args.tracking_ref = PUBLIC_DEMO_TRACKING_REF
        elif not args.repository_id or not args.tracking_ref:
            raise DemoRefused("--repository-id et --tracking-ref requis sans --demo.")
        if args.browser_refresh and (not args.demo or
                                     not args.public_fictional_trusted):
            raise DemoRefused("--browser-refresh exige --demo et --public-fictional-trusted.")
        if not args.baseline_sha and not args.fetch_demo:
            raise DemoRefused("--baseline-sha requis sans actualisation Git explicite.")
        # A browser-refresh launch executes unsandboxed Quarto immediately.
        # Verify the real clone and origin BEFORE any first render, even when
        # --fetch-demo is absent. This is a local-only preflight, NOT a fetch.
        if args.browser_refresh:
            verify_public_demo_clone(args.repo)
        # Validate user consent and arguments before any contact with GitHub.
        if args.fetch_demo:
            validate_inputs(args.repository_id, args.baseline_sha or "0" * 40,
                            args.tracking_ref, args.public_fictional_trusted)
            old_sha = fetch_fictional_demo(
                args.repo, args.repository_id, args.tracking_ref)
            baseline = args.baseline_sha or old_sha
        else:
            baseline = args.baseline_sha
        if args.browser_refresh:
            result, preview = prepare_preview(
                args.repo, args.repository_id, args.tracking_ref,
                baseline, public_fictional_trusted=True)
            refresh = browser_refresh_callback(
                args.repo, result["observed_commit"])
            server = make_server(preview, refresh_callback=refresh)
        else:
            result, preview, server = prepare(
                args.repo, args.repository_id, args.tracking_ref,
                baseline, public_fictional_trusted=args.public_fictional_trusted)
    except (ValueError, OSError) as exc:
        parser.exit(2, "REFUSED: " + str(exc) + "\n")
    try:
        print("Alliage — Quarto réellement rendu depuis deux SHA Git ; aucune publication.", flush=True)
        print("Dépôt / branche déclarés : " + args.repository_id +
              " / " + args.tracking_ref, flush=True)
        print("Référence Git : " + result["baseline_commit"], flush=True)
        print("Proposition Git : " + result["observed_commit"], flush=True)
        print("Actualisation Git explicitement demandée : " +
              ("OUI" if args.fetch_demo else "NON"), flush=True)
        print("Ressource à ouvrir dans Firefox : " +
              preview.browser_url(server.server_port), flush=True)
        print("Choisir V1/V2 dans la page ; Ctrl+C arrête le serveur local.", flush=True)
        print("Actualisation volontaire depuis Firefox : " +
              ("ACTIVÉE pour la fixture fictive" if args.browser_refresh
               else "DÉSACTIVÉE"), flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
