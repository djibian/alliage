#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Experimental, local composition of P3.3 observation, P3.1 rendering and P3.2 navigation.

This is NOT an Alliage product architecture, a background watcher, an AI agent,
a publication operation or a claim about the freshness of a remote Git branch.
No implicit fetch or checkout. Real Quarto may run hooks and is NOT sandboxed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from quarto_branch_delta import compare
from quarto_historical_preview import create_preview
from quarto_navigation import build_navigation
from quarto_versions import _git


class SessionError(ValueError):
    """Refuse an incomplete or ambiguous experimental observation."""


# P3.2's existing Firefox content script allows only /activite.html.
# Extending source support needs a separate, tested browser change.
PILOT_SOURCE = "activite.qmd"


def _fingerprint(repo: Path) -> tuple[str, str]:
    """Sample HEAD and porcelain status, NOT worktree file contents or metadata."""
    head = _git(repo, "rev-parse", "HEAD").decode("ascii", "strict").strip()
    status = _git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    return head, hashlib.sha256(status).hexdigest()


def observe(repo: Path, repository_id: str, source: str,
            tracking_ref: str, baseline_sha: str) -> dict:
    """Read the explicit local tracking ref; do not infer remote freshness."""
    if source != PILOT_SOURCE:
        raise SessionError("Pilote Firefox limité à activite.qmd / activite.html.")
    delta = compare(repo, repository_id, source, tracking_ref, baseline_sha)
    expected_id = f"quarto:{repository_id}:{source}"
    if (delta.get("resource_id") != expected_id
            or delta.get("source_path") != source
            or delta.get("baseline_commit") != baseline_sha
            or delta.get("remote_freshness_verified") is not False
            or delta.get("deployment_verified") is not False
            or delta.get("fetch_performed_by_alliage") is not False):
        raise SessionError("Observation Git incohérente ou provenance indémontrée.")
    if (delta.get("relation") != "FAST_FORWARD"
            or delta.get("ref_changed") is not True
            or delta.get("project_tree_changed") is not True):
        raise SessionError("Seul un avancement FAST_FORWARD avec arbre modifié est admissible.")
    return delta


def _history_root() -> Path:
    """Use only P3.2's existing home-local session directory."""
    home = Path.home().resolve(strict=True)
    parent = home / "alliage-experiences"
    root = parent / "historique"
    for path in (parent, root):
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise SessionError("Chemin de laboratoire symbolique ou non répertoire : refus.")
    root.mkdir(parents=True, exist_ok=True)
    if root.resolve(strict=True) != root:
        raise SessionError("Chemin de laboratoire redirigé.")
    return root


def create_observed_session(repo: Path, repository_id: str, source: str,
                            tracking_ref: str, baseline_sha: str,
                            *, trusted_quarto: bool = False) -> dict:
    """Build a new V1/V2 local session with exactly pinned Git commits.

    The caller must explicitly opt into executing Quarto on a trusted fixture.
    No automatic refresh: refs are observed locally and pinned once per call.
    """
    if not trusted_quarto:
        raise SessionError("Rendu Quarto non sandboxé : --trusted-quarto requis.")
    delta = observe(repo, repository_id, source, tracking_ref, baseline_sha)
    repo = Path(repo).expanduser().resolve(strict=True)
    before = _fingerprint(repo)
    session = None
    try:
        root = _history_root()
        session = Path(tempfile.mkdtemp(prefix="p31-final-observed-", dir=root))
        pairs = (("V1", delta["baseline_commit"], delta["baseline"]),
                 ("V2", delta["observed_commit"], delta["observed"]))
        for version, sha, snapshot in pairs:
            # P3.1 receives a SHA, never a moving branch or HEAD.
            manifest = create_preview(repo, sha, source, session / version, render=True)
            if (manifest.get("commit") != sha or manifest.get("source_path") != source
                    or manifest.get("source_sha256") != snapshot.get("sha256")
                    or manifest.get("render_status") != "RENDERED_FROM_GIT_SNAPSHOT"
                    or manifest.get("publication_status") != "NOT_INITIATED_BY_ALLIAGE"
                    or manifest.get("deployment_verified") is not False):
                raise SessionError("Discordance Git / manifeste du rendu " + version)
        # P3.2 independently rehashes every Git-tracked file and both HTML files.
        page = build_navigation(session, ["V1", "V2"], reference="V1")
        if _fingerprint(repo) != before:
            raise SessionError("HEAD ou statut Git modifié durant la session : résultat refusé.")
        return {
            "schema": "alliage.quarto-observed-session.v0",
            "resource_id": delta["resource_id"],
            "resource_identity_scope": "DECLARED_REPOSITORY_ID_AND_GIT_SOURCE_PATH",
            "baseline_commit": delta["baseline_commit"],
            "observed_commit": delta["observed_commit"],
            "local_reference": "V1",
            "local_observed": "V2",
            "navigation_url": page.as_uri(),
            "session_path": str(session),
            # A dirty file can change bytes while porcelain status stays "M".
            # Never claim a full worktree content-integrity attestation.
            "checkout_head_and_status_unchanged": True,
            "checkout_file_contents_unchanged_verified": False,
            "remote_freshness_verified": False,
            "publication_performed": False,
            "deployment_verified": False,
            "integrity_verification": "POINT_IN_TIME_ONLY",
            "quarto_external_effects": "NOT_VERIFIED",
            "firefox_manually_verified": False,
        }
    except (Exception, KeyboardInterrupt, SystemExit):
        # Ctrl+C is not an Exception. Clean up Python interruptions as well;
        # SIGKILL, power loss and failed removal remain outside this guarantee.
        if session is not None:
            shutil.rmtree(session)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="P3.3 → P3.1 → P3.2 local, sans fetch ni publication.")
    parser.add_argument("--repo", required=True, type=Path,
                        help="Racine exacte d'un clone Git local autorisé")
    parser.add_argument("--repository-id", required=True, help="owner/repo déclaré")
    parser.add_argument("--source", required=True, help="Fichier QMD (pilote : activite.qmd)")
    parser.add_argument("--tracking-ref", required=True,
                        help="refs/remotes/origin/experiment/<branche>, mise à jour explicite")
    parser.add_argument("--baseline-sha", required=True, help="Commit antérieur, SHA complet")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Observation locale sans rendu ni session")
    mode.add_argument("--render", action="store_true", help="Créer une session Quarto réelle")
    parser.add_argument("--trusted-quarto", action="store_true",
                        help="Accepter explicitement les hooks/filters d'un projet local fiable")
    args = parser.parse_args(argv)
    if args.render and not args.trusted_quarto:
        parser.error("--render exige --trusted-quarto (Quarto n'est pas sandboxé)")
    if args.check and args.trusted_quarto:
        parser.error("--trusted-quarto est réservé à --render")
    try:
        if args.check:
            result = observe(args.repo, args.repository_id, args.source,
                             args.tracking_ref, args.baseline_sha)
        else:
            result = create_observed_session(
                args.repo, args.repository_id, args.source,
                args.tracking_ref, args.baseline_sha, trusted_quarto=True)
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(2, "REFUSED: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
