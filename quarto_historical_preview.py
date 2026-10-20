#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create an isolated, Git-pinned Quarto project snapshot; optionally render it.

No Git checkout/fetch, no changes to the source repository, no publication.
A Quarto render may execute project hooks: use --render only with a trusted repo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile


class PreviewError(ValueError):
    """Fail closed if Git provenance, output isolation or rendering is uncertain."""


SHA = re.compile(r"[0-9a-f]{40}\Z")
MAX_FILES = 2000
MAX_BLOB = 20 * 1024 * 1024
MAX_TOTAL = 100 * 1024 * 1024


def _git(repo: Path, *args: str) -> bytes:
    try:
        proc = subprocess.run(["git", "--no-replace-objects", "-C", str(repo), *args],
                              capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreviewError("Lecture Git impossible.") from exc
    if proc.returncode:
        raise PreviewError("Lecture Git refusée : " + proc.stderr.decode("utf-8", "replace")[:200])
    return proc.stdout


def _path(name: str) -> Path:
    if (not name or name.startswith("/") or "\\" in name or "\x00" in name or
            any(part in ("", ".", "..", ".git") for part in name.split("/"))):
        raise PreviewError("Chemin Git non autorisé.")
    return Path(*PurePosixPath(name).parts)


def _objects(repo: Path, revision: str) -> list[tuple[str, str, str, int]]:
    raw = _git(repo, "ls-tree", "-r", "-z", "--full-tree", revision)
    if not raw.endswith(b"\x00"):
        raise PreviewError("Inventaire Git invalide.")
    output = []
    total = 0
    for row in raw[:-1].split(b"\x00"):
        if len(output) >= MAX_FILES or b"\t" not in row:
            raise PreviewError("Inventaire Git trop grand ou invalide.")
        metadata, raw_name = row.split(b"\t", 1)
        match = re.fullmatch(rb"(100644|100755) blob ([0-9a-f]{40})", metadata)
        if not match:
            raise PreviewError("Instantané contenant un lien symbolique, sous-module ou objet non régulier.")
        try:
            name = raw_name.decode("utf-8", "strict")
        except UnicodeError as exc:
            raise PreviewError("Chemin Git sans encodage UTF-8.") from exc
        _path(name)
        blob = match.group(2).decode("ascii")
        try:
            size = int(_git(repo, "cat-file", "-s", blob).decode("ascii").strip())
        except ValueError as exc:
            raise PreviewError("Taille d'objet Git incorrecte.") from exc
        total += size
        if size > MAX_BLOB or total > MAX_TOTAL:
            raise PreviewError("Instantané trop volumineux pour le pilote.")
        output.append((name, match.group(1).decode("ascii"), blob, size))
    return output


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_preview(repo: Path, revision: str, source: str, out: Path,
                   render: bool = False) -> dict:
    """Return a durable manifest; project files are read from one Git commit only.

    Render is opt-in because Quarto project hooks and filters can execute code.
    Source must be an authorised trusted local repository, not untrusted content.
    """
    if not isinstance(revision, str) or not SHA.fullmatch(revision):
        raise PreviewError("SHA complet de commit Git requis (SHA-1, 40 caractères).")
    if not isinstance(source, str) or PurePosixPath(source).suffix != ".qmd":
        raise PreviewError("Source Quarto .qmd obligatoire.")
    _path(source)
    repo = Path(repo).expanduser().resolve(strict=True)
    root = Path(_git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if repo != root:
        raise PreviewError("Utiliser la racine exacte du dépôt Git.")
    commit = _git(repo, "rev-parse", "--verify", "--end-of-options",
                  revision + "^{commit}").decode("ascii").strip()
    if commit != revision:
        raise PreviewError("Le SHA demandé ne correspond pas à un commit entier.")

    dest = Path(out).expanduser().absolute()
    if dest.exists() or dest.is_symlink():
        raise PreviewError("Le dossier de sortie existe déjà.")
    dest = dest.resolve(strict=False)
    if repo == dest or repo in dest.parents or dest in repo.parents:
        raise PreviewError("La sortie doit rester extérieure au dépôt source.")
    if not dest.parent.is_dir():
        raise PreviewError("Créer d'abord le répertoire parent de sortie.")

    objects = _objects(repo, commit)
    if source not in [entry[0] for entry in objects]:
        raise PreviewError("Fichier source absent à cette révision.")
    stage = Path(tempfile.mkdtemp(prefix=".alliage-preview-", dir=dest.parent))
    try:
        project = stage / "project"
        project.mkdir()
        tracked = []
        for name, mode, blob, size in objects:
            data = _git(repo, "cat-file", "blob", blob)
            if len(data) != size:
                raise PreviewError("Taille d'objet Git incohérente.")
            if data.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                raise PreviewError("Objet Git LFS non matérialisé : rendu refusé.")
            target = project / _path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            if mode == "100755":
                target.chmod(0o755)
            tracked.append({"path": name, "git_blob": blob,
                            "sha256": hashlib.sha256(data).hexdigest(), "bytes": size})
        rendered = None
        quarto_version = None
        if render:
            if not shutil.which("quarto"):
                raise PreviewError("Quarto absent du PATH : aucun rendu attesté.")
            try:
                ver = subprocess.run(["quarto", "--version"], capture_output=True,
                                     text=True, timeout=15, cwd=project)
                if ver.returncode:
                    raise PreviewError("Version Quarto impossible à déterminer.")
                quarto_version = ver.stdout.strip()
                # Le projet déclare output-dir: _site ; Quarto interdit
                # --output-dir lors du rendu d'un seul document.
                cmd = ["quarto", "render", source, "--to", "html", "--no-execute"]
                res = subprocess.run(cmd, capture_output=True, text=True, cwd=project, timeout=180)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise PreviewError("Rendu Quarto impossible ou expiré.") from exc
            if res.returncode:
                raise PreviewError("Échec Quarto : " + (res.stdout + res.stderr)[-1000:])
            html = project / "_site" / _path(str(PurePosixPath(source).with_suffix(".html")))
            if not html.is_file() or html.is_symlink():
                raise PreviewError("HTML Quarto attendu absent du répertoire de sortie.")
            rendered = {"path": str(html.relative_to(stage)), "sha256": _file_hash(html)}
            for entry in tracked:
                if _file_hash(project / _path(entry["path"])) != entry["sha256"]:
                    raise PreviewError("Un fichier Git suivi a été modifié pendant le rendu.")

        result = {"schema": "alliage.quarto-historical-preview.v0",
                  "commit": commit, "source_path": source, "source_sha256": next(x["sha256"] for x in tracked if x["path"] == source),
                  "tracked_files": tracked, "snapshot_complete_for_tracked_files": True,
                  "render_status": "RENDERED_FROM_GIT_SNAPSHOT" if render else "NOT_RENDERED",
                  "rendered_html": rendered, "quarto_version": quarto_version,
                  "publication_status": "NOT_PUBLISHED", "deployment_verified": False,
                  "source_repository_modified": False,
                  "limits": {"git_lfs": "REJECTED", "git_submodules": "REJECTED",
                             "symlinks": "REJECTED", "external_dependencies": "NOT_VERIFIED"}}
        (stage / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8")
        os.replace(stage, dest)
        return result
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Restituer une révision Git Quarto dans un dossier isolé.")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--revision", required=True, help="SHA Git complet")
    parser.add_argument("--source", required=True, help="Chemin .qmd relatif")
    parser.add_argument("--out", type=Path, required=True, help="Nouveau dossier externe au dépôt")
    parser.add_argument("--render", action="store_true", help="Exécute Quarto : dépôt local de confiance seulement")
    args = parser.parse_args()
    try:
        manifest = create_preview(args.repo, args.revision, args.source, args.out, args.render)
    except (PreviewError, OSError, UnicodeError) as exc:
        parser.exit(2, "REFUSED: " + str(exc) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
