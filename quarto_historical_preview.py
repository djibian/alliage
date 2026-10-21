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



def _check_project_render_scope(project: Path, objects: list[tuple[str, str, str, int]]) -> None:
    """Accept only a narrow, unambiguous Quarto project config for P3.1.

    No generic YAML parser: complex mappings, profiles, aliases and any
    project.render override are unsupported and rejected, not guessed at.
    This is not an isolation mechanism for Quarto hooks/extensions.
    """
    names = [name for name, _, _, _ in objects]
    if "_quarto.yml" not in names:
        raise PreviewError("Rendu historique limité aux projets contenant _quarto.yml.")
    configs = [name for name in names if (
        (PurePosixPath(name).name.lower().startswith("_quarto") and
         PurePosixPath(name).suffix.lower() in (".yml", ".yaml", ".lua"))
        or PurePosixPath(name).name.lower() in ("quarto.yml", "quarto.yaml")
    )]
    if configs != ["_quarto.yml"]:
        raise PreviewError("Configuration Quarto supplémentaire ou profil non pris en charge.")
    try:
        value = (project / "_quarto.yml").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PreviewError("Configuration Quarto illisible.") from exc
    if any(char in value for char in ("\t", "\r", "\x00", "\ufeff")):
        raise PreviewError("Syntaxe de configuration Quarto non prise en charge.")
    # Anchors, aliases, merge keys, tags and document boundaries can change
    # the effective project mapping without a visible project.render line.
    for line in value.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        if (re.search(r"(?:^|\s)<<\s*:|[&*!]", line)
                or stripped.startswith(("---", "...", "%"))):
            raise PreviewError("Configuration Quarto YAML complexe non prise en charge.")
    lines = value.splitlines()
    starts = [index for index, line in enumerate(lines)
              if re.fullmatch(r"project:\s*(?:#.*)?", line)]
    if len(starts) != 1:
        raise PreviewError("Bloc project Quarto unique et explicite requis.")
    start = starts[0]
    if any(line.strip() and not line.lstrip().startswith("#")
           for line in lines[:start]):
        raise PreviewError("Le bloc project doit précéder les autres paramètres.")
    values = {}
    for line in lines[start + 1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" "):
            break
        match = re.fullmatch(r"  (type|output-dir):\s*([A-Za-z0-9_-]+)\s*(?:#.*)?", line)
        if not match or match.group(1) in values:
            raise PreviewError("Sélection project.render ou configuration projet non prise en charge.")
        values[match.group(1)] = match.group(2)
    if values != {"type": "default", "output-dir": "_site"}:
        raise PreviewError("Projet P3.1 attendu : type default et output-dir _site uniquement.")
    # Reject duplicate, quoted, or reintroduced project declarations elsewhere.
    remainder = "\n".join(lines[start + 1:])
    if re.search(r"(?m)^(?:['\"]?project['\"]?\s*:|\s*<<\s*:)", remainder):
        raise PreviewError("Bloc project supplémentaire ou fusion YAML interdite.")
    # Root keys must be plain: complex YAML mapping keys can introduce a
    # second project declaration through the explicit-key mapping syntax.
    for line in lines[start + 1:]:
        if not line or line[0].isspace() or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]*):(?:\s*.*)?", line)
        if not match or match.group(1) == "project":
            raise PreviewError("Clé YAML racine complexe ou projet dupliqué interdit.")


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
    stage = Path(tempfile.mkdtemp(prefix="alliage-preview-", dir=dest.parent))
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
            _check_project_render_scope(project, objects)
            # Le rendu d'un document isolé ignore des options du projet
            # (_quarto.yml : CSS, sommaire). Ne rendre le projet que si
            # une seule ressource ordinaire peut être rendue.
            targets = []
            for name, _, _, _ in objects:
                parts = PurePosixPath(name).parts
                if any(part.startswith((".", "_")) for part in parts[:-1]):
                    continue
                filename = parts[-1]
                if filename.startswith((".", "_")) or filename in ("README.md", "AGENTS.md"):
                    continue
                if PurePosixPath(name).suffix.lower() in (".qmd", ".md", ".rmd", ".ipynb"):
                    targets.append(name)
            if targets != [source]:
                raise PreviewError("Rendu de projet refusé : ressource Quarto unique exigée.")
            # Exiger des sorties par défaut absentes AVANT le rendu :
            # un ancien HTML suivi par Git ne prouve jamais la production.
            relative_html = _path(str(PurePosixPath(source).with_suffix(".html")))
            candidates = [project / relative_html, project / "_site" / relative_html]
            if any(p.exists() or p.is_symlink() for p in candidates):
                raise PreviewError("HTML candidat préexistant : provenance du rendu non vérifiable.")
            if not shutil.which("quarto"):
                raise PreviewError("Quarto absent du PATH : aucun rendu attesté.")
            try:
                ver = subprocess.run(["quarto", "--version"], capture_output=True,
                                     text=True, timeout=15, cwd=project)
                if ver.returncode:
                    raise PreviewError("Version Quarto impossible à déterminer.")
                quarto_version = ver.stdout.strip()
                # Le rendu en mode projet applique CSS, toc et configuration.
                cmd = ["quarto", "render", "--to", "html", "--no-execute"]
                res = subprocess.run(cmd, capture_output=True, text=True, cwd=project, timeout=180)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise PreviewError("Rendu Quarto impossible ou expiré.") from exc
            if res.returncode:
                raise PreviewError("Échec Quarto : " + (res.stdout + res.stderr)[-1000:])
            # Refuser les sorties personnalisées non prises en charge :
            # seul un emplacement initialement absent et nouvellement créé
            # est admissible. Le HTML généré n'est pas un déploiement attesté.
            found = [p for p in candidates if p.is_file() and not p.is_symlink()]
            if len(found) != 1:
                # Fournir un diagnostic borné des artefacts HTML du seul
                # instantané local ; ne jamais déclarer de rendu par défaut.
                observed = sorted(str(p.relative_to(project))
                                  for p in project.rglob("*.html"))[:10]
                raise PreviewError("HTML Quarto non identifiable dans le dossier isolé "
                                   "(sorties HTML observées : " + repr(observed) + ").")
            html = found[0]
            if project.resolve() not in html.resolve().parents:
                raise PreviewError("HTML Quarto hors de l'instantané isolé.")
            rendered = {"path": str(html.relative_to(stage)), "sha256": _file_hash(html),
                        "existed_before_render": False}
            for entry in tracked:
                if _file_hash(project / _path(entry["path"])) != entry["sha256"]:
                    raise PreviewError("Un fichier Git suivi a été modifié pendant le rendu.")

        result = {"schema": "alliage.quarto-historical-preview.v0",
                  "commit": commit, "source_path": source, "source_sha256": next(x["sha256"] for x in tracked if x["path"] == source),
                  "tracked_files": tracked, "snapshot_complete_for_tracked_files": True,
                  "render_status": "RENDERED_FROM_GIT_SNAPSHOT" if render else "NOT_RENDERED",
                  "rendered_html": rendered, "quarto_version": quarto_version,
                  "publication_status": "NOT_INITIATED_BY_ALLIAGE",
                  "deployment_verified": False,
                  # Quarto peut exécuter des hooks, même avec --no-execute :
                  # les écritures extérieures et le déploiement ne sont pas audités.
                  "source_repository_modified": None,
                  "source_repository_modification_verified": False,
                  "external_render_effects": "NOT_VERIFIED" if render else "NOT_APPLICABLE",
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
