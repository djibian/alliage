#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Inspecter des révisions Quarto Git sans modifier ni publier de ressource.

Phase 1 : seules les révisions locales déjà disponibles sont observées.
Une déclaration de SHA publié n'est PAS une preuve de déploiement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from pathlib import PurePosixPath


class VersionError(ValueError):
    """Référence ou source Git incompatible avec l'inspection sûre."""


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "--no-replace-objects", "-C", str(repo), *args], capture_output=True)
    if result.returncode:
        raise VersionError("Git a refusé l'inspection : " + result.stderr.decode("utf-8", "replace").strip()[:250])
    return result.stdout


def _sha(repo: Path, rev: str) -> str:
    value = _git(repo, "rev-parse", "--verify", "--end-of-options", rev + "^{commit}").decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise VersionError("Révision Git non résolue en SHA complet.")
    return value


def _safe_source(source: str) -> str:
    if (not isinstance(source, str) or not source or "\\" in source or "\x00" in source
            or source.startswith("/") or any(part in ("", ".", "..", ".git") for part in source.split("/"))
            or PurePosixPath(source).suffix != ".qmd"):
        raise VersionError("Chemin source .qmd relatif non autorisé.")
    return source


def _safe_ref(ref: str) -> str:
    if (not isinstance(ref, str) or not re.fullmatch(r"refs/(?:heads|remotes)/[a-zA-Z0-9_./-]+", ref)
            or ".." in ref or "//" in ref or ref.endswith(("/", "."))):
        raise VersionError("Référence de travail : branche locale ou distante explicite requise.")
    return ref


def _snapshot(repo: Path, revision: str, source: str) -> dict:
    # Sortie NUL : les chemins UTF-8 et les guillemets ne sont pas échappés.
    raw = _git(repo, "ls-tree", "-z", revision, "--", source)
    entries = raw.split(b"\x00")
    if len(entries) != 2 or entries[1] or b"\t" not in entries[0]:
        raise VersionError("Source absente ou chemin ambigu à cette révision.")
    header, path = entries[0].split(b"\t", 1)
    match = re.fullmatch(rb"(100644|100755) blob ([0-9a-f]{40})", header)
    if not match or path != source.encode("utf-8"):
        raise VersionError("Source absente, non régulière ou lien symbolique à cette révision.")
    blob = match.group(2).decode("ascii")
    data = _git(repo, "cat-file", "blob", blob)
    return {"commit": revision, "git_blob": blob, "sha256": hashlib.sha256(data).hexdigest()}


def inspect(repo: Path, repository_id: str, source: str, working_ref: str,
            published_sha: str | None = None, limit: int = 20) -> dict:
    """Renvoie une photographie vérifiable, sans fetch/checkout/écriture Git.

    Historique affiché : commits ayant modifié ce .qmd, pas ses dépendances.
    Le SHA de commit complet identifie néanmoins la révision du projet.
    """
    repo = Path(repo).expanduser().resolve(strict=True)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository_id):
        raise VersionError("Identifiant explicite de dépôt attendu : organisation/projet.")
    source = _safe_source(source)
    working_ref = _safe_ref(working_ref)
    if type(limit) is not int or not 1 <= limit <= 100:
        raise VersionError("Limite d'historique comprise entre 1 et 100.")
    root = Path(_git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if root != repo:
        raise VersionError("Utiliser la racine Git exacte, pas un sous-dossier.")
    working = _sha(repo, working_ref)
    working_source = _snapshot(repo, working, source)
    published = None
    if published_sha is not None:
        if not re.fullmatch(r"[0-9a-f]{40}", published_sha):
            raise VersionError("La déclaration publiée doit être un SHA Git complet.")
        published_revision = _sha(repo, published_sha)
        published_source = _snapshot(repo, published_revision, source)
        ancestor = subprocess.run(["git", "--no-replace-objects", "-C", str(repo), "merge-base", "--is-ancestor",
                                   published_revision, working], capture_output=True)
        if ancestor.returncode not in (0, 1):
            raise VersionError("Comparaison d'ascendance Git impossible.")
        published = {**published_source, "is_ancestor_of_working": ancestor.returncode == 0,
                     "deployment_verified": False, "status": "DECLARED_NOT_VERIFIED"}
    # -z préserve les caractères de contrôle d'un sujet sans casser la lecture.
    raw = _git(repo, "log", "-z", "-n", str(limit), "--format=%H%x00%s",
               working, "--", source)
    fields = raw.split(b"\x00")
    if not fields or fields[-1] != b"" or len(fields) % 2 != 1:
        raise VersionError("Journal Git illisible.")
    history = []
    for i in range(0, len(fields) - 1, 2):
        sha = fields[i].decode("ascii", "strict")
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise VersionError("Identifiant Git invalide dans l'historique.")
        title = fields[i + 1].decode("utf-8", "replace")
        history.append({"commit": sha, "label_unverified": title})
    return {
        "schema": "alliage.quarto-versions.v0",
        "resource_id": "quarto:" + repository_id + ":" + source,
        "source_path": source,
        "working_ref": working_ref,
        "working": working_source,
        "published": published,
        "publication_status": "DECLARED_NOT_VERIFIED" if published else "UNDECLARED",
        "history_scope": "SOURCE_PATH_ONLY",
        "history": history,
        "read_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspecter sans écriture les versions Git d'une ressource Quarto.")
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--repository-id", required=True, help="Identité explicite, ex. demo/cours")
    parser.add_argument("--source", required=True, help="Chemin relatif .qmd")
    parser.add_argument("--working-ref", required=True, help="refs/heads/... ou refs/remotes/...")
    parser.add_argument("--published-sha", help="SHA déclaré comme publié, non vérifié")
    args = parser.parse_args()
    try:
        result = inspect(args.repo, args.repository_id, args.source, args.working_ref, args.published_sha)
    except (VersionError, OSError) as exc:
        parser.exit(2, "REFUSED : " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
