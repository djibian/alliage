#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.3: compare a known Git commit with an explicitly chosen local tracking ref.

This reads Git objects already available locally. It does not fetch, checkout,
create refs, edit a working tree, render Quarto or publish.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

from quarto_versions import (
    VersionError, _git, _git_environment, _sha, _safe_source, _snapshot,
)


class DeltaError(ValueError):
    """The comparison cannot establish a well-defined local Git observation."""


COMMIT_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
REPO_ID = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
TRACKING_REF = re.compile(
    r"refs/remotes/origin/experiment/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*\Z"
)


def _ancestor(repo: Path, old: str, new: str) -> bool:
    try:
        proc = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(repo),
             "merge-base", "--is-ancestor", old, new],
            capture_output=True, timeout=30, env=_git_environment(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DeltaError("Comparaison d'ascendance Git impossible.") from exc
    if proc.returncode not in (0, 1):
        raise DeltaError("Git n'a pas pu qualifier l'ascendance.")
    return proc.returncode == 0


def _tree(repo: Path, commit: str) -> str:
    raw = _git(repo, "rev-parse", "--verify", "--end-of-options", commit + "^{tree}")
    tree = raw.decode("ascii", "strict").strip()
    if not COMMIT_SHA1.fullmatch(tree):
        raise DeltaError("Identité de l'arbre Git non reconnue.")
    return tree


def _assert_complete_unmodified_ancestry(repo: Path) -> None:
    """Refuse graphs whose parent relations can be falsified or truncated.

    git --no-replace-objects disables refs/replace/*, but does NOT disable
    the independent legacy info/grafts mechanism. --git-path resolves the
    real common Git directory, including when repo is a linked worktree.
    """
    graft_raw = _git(repo, "rev-parse", "--path-format=absolute",
                     "--git-path", "info/grafts")
    grafts = Path(graft_raw.decode("utf-8", "strict").strip())
    if not grafts.is_absolute():
        raise DeltaError("Emplacement des greffes Git ambigu.")
    if grafts.exists() or grafts.is_symlink():
        raise DeltaError("Greffes Git locales interdites : ascendance non fiable.")
    shallow = _git(repo, "rev-parse", "--is-shallow-repository").decode("ascii", "strict").strip()
    if shallow == "true":
        raise DeltaError("Dépôt Git superficiel interdit : ascendance incomplète.")
    if shallow != "false":
        raise DeltaError("Profondeur de l'historique Git indéterminée.")


def compare(repo: Path, repository_id: str, source: str, tracking_ref: str,
            baseline_sha: str) -> dict:
    """Compare two immutable Git commits; no network and no working-tree writes.

    The caller MUST explicitly fetch before invoking this function if it wants
    the tracking ref to reflect newer remote commits. We cannot prove freshness.
    """
    if not isinstance(repository_id, str) or not REPO_ID.fullmatch(repository_id):
        raise DeltaError("Identité de dépôt explicite owner/repo requise.")
    try:
        source = _safe_source(source)
    except VersionError as exc:
        raise DeltaError(str(exc)) from exc
    if not isinstance(tracking_ref, str) or not TRACKING_REF.fullmatch(tracking_ref):
        raise DeltaError("Ref distante locale explicite refs/remotes/origin/experiment/... requise.")
    if (not isinstance(baseline_sha, str) or not COMMIT_SHA1.fullmatch(baseline_sha)):
        raise DeltaError("SHA de référence complet et exact (40 caractères) requis.")
    try:
        repo = Path(repo).expanduser().resolve(strict=True)
        root = Path(_git(repo, "rev-parse", "--show-toplevel").decode("utf-8").strip()).resolve()
        if repo != root:
            raise DeltaError("La racine exacte du dépôt Git est requise.")
        _assert_complete_unmodified_ancestry(repo)
        baseline = _sha(repo, baseline_sha)
        observed = _sha(repo, tracking_ref)
        if baseline != baseline_sha:
            raise DeltaError("Le SHA initial ne correspond pas à un commit Git.")
        before = _snapshot(repo, baseline, source)
        after = _snapshot(repo, observed, source)
        before_tree = _tree(repo, baseline)
        after_tree = _tree(repo, observed)
    except (VersionError, OSError, UnicodeError, ValueError) as exc:
        if isinstance(exc, DeltaError):
            raise
        raise DeltaError("Observation Git refusée : " + str(exc)) from exc

    if baseline == observed:
        relation = "UNCHANGED"
    elif _ancestor(repo, baseline, observed):
        relation = "FAST_FORWARD"
    elif _ancestor(repo, observed, baseline):
        relation = "REWOUND"
    else:
        relation = "DIVERGED"

    return {
        "schema": "alliage.quarto-branch-delta.v0",
        "resource_id": f"quarto:{repository_id}:{source}",
        "source_path": source,
        "tracking_ref": tracking_ref,
        "baseline_commit": baseline,
        "observed_commit": observed,
        "relation": relation,
        # Deprecated compatibility field. Use ref_changed + relation; a
        # rewritten or rewound branch does NOT prove a newly created commit.
        "new_commit_observed": baseline != observed,
        "ref_changed": baseline != observed,
        "project_tree_changed": before_tree != after_tree,
        "source_blob_changed": before["git_blob"] != after["git_blob"],
        "baseline": {**before, "git_tree": before_tree},
        "observed": {**after, "git_tree": after_tree},
        "observation_scope": "LOCAL_REMOTE_TRACKING_REF",
        "remote_freshness_verified": False,
        "fetch_performed_by_alliage": False,
        "working_tree_updated_by_alliage": False,
        "deployment_verified": False,
        "publication_status": "NOT_VERIFIED",
        "read_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Comparer une ref de suivi Git locale à un commit connu, sans fetch ni publication.")
    parser.add_argument("--repo", required=True, type=Path, help="Copie Git locale autorisée")
    parser.add_argument("--repository-id", required=True, help="Identité déclarée owner/repo")
    parser.add_argument("--source", required=True, help="Chemin .qmd dans le dépôt")
    parser.add_argument("--tracking-ref", required=True,
                        help="refs/remotes/origin/experiment/<branche>")
    parser.add_argument("--baseline-sha", required=True, help="SHA complet déjà observé")
    args = parser.parse_args()
    try:
        result = compare(args.repo, args.repository_id, args.source,
                         args.tracking_ref, args.baseline_sha)
    except (DeltaError, OSError) as exc:
        parser.exit(2, "REFUSED: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
