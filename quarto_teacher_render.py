#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.6A: opt-in isolated, single-document Quarto professor render from a pinned Git tree.

NOT a sandbox, a browser URL, a teacher-content release or a student deployment.
Never execute on an untrusted repository. No Git fetch/checkout/write.
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

from quarto_historical_preview import (
    MAX_BLOB, MAX_FILES, MAX_TOTAL, PreviewError, _git, _objects, _path,
)
from quarto_teacher_provenance import TeacherProvenanceError, probe


class TeacherRenderError(ValueError):
    """Explicitly refuse a misleading or unsafe proof."""


MAX_RENDERED_FILES = 2000
MAX_RENDERED_BYTES = 100 * 1024 * 1024
MAX_HTML_BYTES = 20 * 1024 * 1024
# Fail-closed subset of QMD YAML front matter for this first professor-only
# experiment. We do not try to interpret YAML using a security-sensitive
# regex blacklist: unknown keys, quoted key spellings, composed mappings,
# anchors, tags, nested blocks, comments and non-LF newlines are rejected.
# This grammar is NOT a general YAML parser, and newly required metadata must
# first be accompanied by positive fixtures and adversarial qualification.
_QMD_TEXT_KEYS = {"title", "subtitle"}
_QMD_ID_KEYS = {"activity-id", "curriculum-unit", "publication-status",
                "support-level"}
_QMD_LIST_KEYS = {"official-refs", "concepts"}
_QMD_PLAIN_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_./-]*\Z")
_QMD_DURATION = re.compile(r"[1-9][0-9]{0,2} min\Z")
_QMD_INT = re.compile(r"(?:0|[1-9][0-9]{0,2})\Z")
_QMD_PLAIN_LIST_ITEM = re.compile(r"[A-Za-z_][A-Za-z0-9_. /-]*\Z")
_YAML_NON_STRING = frozenset({"true", "false", "null", "yes", "no",
                              "on", "off", "y", "n"})



def _yaml_simple_string(value: str) -> bool:
    """Subset of YAML scalars that unambiguously decode to a single string."""
    if not value or value != value.strip():
        return False
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        inner = value[1:-1]
        return bool(inner) and '"' not in inner and "\\" not in inner and not any(
            ord(char) < 32 for char in inner)
    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        inner = value[1:-1]
        return bool(inner) and "'" not in inner and not any(
            ord(char) < 32 for char in inner)
    return (_QMD_PLAIN_ID.fullmatch(value) is not None
            and value.casefold() not in _YAML_NON_STRING)


def _validate_qmd_frontmatter(raw: bytes) -> None:
    """Consume the *entire* recognized frontmatter; reject equivalent tricks."""
    if not raw.startswith(b"---\n"):
        raise TeacherRenderError("QMD sans en-tête YAML LF qualifié.")
    close = raw.find(b"\n---\n", 4)
    if close < 0 or close > 65536:
        raise TeacherRenderError("En-tête YAML QMD incomplet ou surdimensionné.")
    head = raw[4:close]
    if b"\r" in head or b"\t" in head or b"\x00" in head:
        raise TeacherRenderError("Métadonnées YAML non canoniques.")
    try:
        text = head.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise TeacherRenderError("Métadonnées YAML non UTF-8.") from exc
    seen: set[str] = set()
    for line in text.split("\n"):
        # Only a flat mapping of explicitly enumerated metadata keys is
        # recognized. This also rejects quoted keys like "filters", key
        # duplication, tags, inline mapping, aliases and multiline payloads.
        match = re.fullmatch(r"([a-z][a-z0-9-]*): (.+)", line)
        if not match:
            raise TeacherRenderError("Structure de métadonnées QMD non reconnue.")
        key, value = match.groups()
        if key in seen:
            raise TeacherRenderError("Clé YAML QMD dupliquée.")
        seen.add(key)
        if key in _QMD_TEXT_KEYS:
            good = value.startswith(('"', "'")) and _yaml_simple_string(value)
        elif key in _QMD_ID_KEYS:
            good = (_QMD_PLAIN_ID.fullmatch(value) is not None
                    and value.casefold() not in _YAML_NON_STRING)
        elif key == "activity-order":
            good = _QMD_INT.fullmatch(value) is not None
        elif key == "duration":
            good = _QMD_DURATION.fullmatch(value) is not None
        elif key in _QMD_LIST_KEYS:
            good = False
            if value.startswith("[") and value.endswith("]"):
                items = [part.strip() for part in value[1:-1].split(",")]
                good = bool(items) and all(
                    item and (_yaml_simple_string(item)
                              and (item.startswith(("'", '"'))
                                   or _QMD_PLAIN_LIST_ITEM.fullmatch(item) is not None))
                    for item in items)
        else:
            raise TeacherRenderError("Clé QMD hors du sous-ensemble non exécutable.")
        if not good:
            raise TeacherRenderError("Valeur YAML QMD ambiguë ou non qualifiée.")


def _preflight_objects(objects: list[tuple[str, str, str, int]], source: str) -> dict:
    """Reject Quarto configuration layers and generated output not qualified by P3.5.

    Explicit --profile is not sufficient when other metadata/env overrides exist.
    This guard is a conservative *syntax scope*, not a Quarto sandbox.
    """
    names = {name for name, _, _, _ in objects}
    expected = {"_quarto.yml", "_quarto-professeur.yml", "_quarto-eleve.yml"}
    if not expected.issubset(names) or source not in names:
        raise TeacherRenderError("Source Quarto ou configurations requises absentes.")
    for name, mode, _blob, size in objects:
        leaf = PurePosixPath(name).name.lower()
        if (name.startswith("dist/") or name == "dist"
                or name.startswith(".quarto/") or name == ".quarto"
                or leaf.startswith("_quarto") and name not in expected
                or leaf.startswith("_metadata.")
                or leaf.startswith("_environment")
                or leaf == "quarto.yml" or leaf == "quarto.yaml"
                or leaf == "quarto.lua" or leaf.endswith(".qmd.local")):
            raise TeacherRenderError("Configuration ou sortie Quarto hors sous-ensemble sûr.")
        if name in expected and mode != "100644":
            raise TeacherRenderError("Configuration Quarto exécutable non admise.")
        if name == source and size > 1024 * 1024:
            raise TeacherRenderError("Source Quarto trop volumineuse.")
    return {"tracked_count": len(objects),
            "tracked_bytes": sum(item[3] for item in objects),
            "profile": "professeur",
            "source_path": source}


def _source_preflight(repo: Path, commit: str, source: str) -> None:
    """Validate the pinned QMD metadata before any private Quarto execution."""
    raw = _git(repo, "show", f"{commit}:{source}")
    if len(raw) > 1024 * 1024:
        raise TeacherRenderError("Source Quarto trop volumineuse.")
    _validate_qmd_frontmatter(raw)


def plan(repo: Path, repository_id: str, source: str, working_ref: str,
         expected_sha: str) -> dict:
    """Read-only provenance + bounded complete Git inventory; no Quarto invocation."""
    provenance = probe(repo, repository_id, source, working_ref, expected_sha)
    repo = Path(repo).expanduser().resolve(strict=True)
    objects = _objects(repo, expected_sha)
    scope = _preflight_objects(objects, source)
    _source_preflight(repo, expected_sha, source)
    # The ref must still designate the same immutable Git commit.
    if probe(repo, repository_id, source, working_ref, expected_sha)["working_tree_git_sha"] != provenance["working_tree_git_sha"]:
        raise TeacherRenderError("Référence Git modifiée pendant le préflight.")
    return {
        "schema": "alliage.quarto-professor-render-plan.v0",
        "status": "PINNED_SOURCE_AND_PROFILES_DECLARED_RENDER_NOT_RUN",
        "resource_id": provenance["resource_id"],
        "working_ref": working_ref,
        "commit": expected_sha,
        "project_tree": provenance["working_tree_git_sha"],
        "source_sha256": provenance["source_sha256"],
        "source_path": source,
        "tracked_count": scope["tracked_count"],
        "tracked_bytes": scope["tracked_bytes"],
        "render_profile_requested": "professeur",
        "render_profile_effective_verified": False,
        "teacher_html_verified": False,
        "teacher_output_exposure_authorized": False,
        "browser_url_verified": False,
        "student_deployment_verified": False,
        "quarto_executed": False,
        "publication_performed": False,
        "read_only": True,
        "external_effects": "NOT_APPLICABLE",
    }


def _safe_destination(repo: Path, dest: Path) -> Path:
    repo = Path(repo).expanduser().resolve(strict=True)
    dest = Path(dest).expanduser().absolute()
    if dest.is_symlink() or dest.exists():
        raise TeacherRenderError("Dossier de session déjà présent.")
    if not dest.parent.is_dir() or dest.parent.is_symlink():
        raise TeacherRenderError("Parent de sortie absent ou symbolique.")
    parent = dest.parent.resolve(strict=True)
    if repo == parent or repo in parent.parents:
        raise TeacherRenderError("Sortie à placer hors du dépôt source.")
    if dest.name in (".", "..") or str(dest).startswith(str(repo) + os.sep):
        raise TeacherRenderError("Sortie dans le dépôt source interdite.")
    return parent / dest.name


def _safe_tree_inventory(root: Path, subpath: Path) -> list[dict]:
    """Inventory all regular files, refuse symlinks, cap output and rehash."""
    files = []
    amount = 0
    # Path.is_symlink() on the final directory misses a symlink at
    # "project/dist". Refuse every intermediate component BEFORE walking.
    root = Path(root).absolute()
    if root.is_symlink() or not root.is_dir():
        raise TeacherRenderError("Racine projet absente ou symbolique.")
    current = root
    if (subpath.is_absolute() or not subpath.parts or
            any(part in ("", ".", "..") for part in subpath.parts)):
        raise TeacherRenderError("Chemin de sortie non canonique.")
    for component in subpath.parts:
        current = current / component
        if current.is_symlink() or not current.is_dir():
            raise TeacherRenderError("Répertoire intermédiaire absent ou symbolique.")
        if not current.resolve(strict=True).is_relative_to(root.resolve(strict=True)):
            raise TeacherRenderError("Sortie Quarto hors racine physique.")
    target = current
    visited = 0
    for p in target.rglob("*"):
        visited += 1
        if visited > 4 * MAX_RENDERED_FILES or p.is_symlink():
            raise TeacherRenderError("Sortie Quarto trop grande ou symbolique.")
        if p.is_dir():
            continue
        if not p.is_file() or len(files) >= MAX_RENDERED_FILES:
            raise TeacherRenderError("Sortie Quarto spéciale ou excessive.")
        size = p.stat().st_size
        amount += size
        if size > MAX_BLOB or amount > MAX_RENDERED_BYTES:
            raise TeacherRenderError("Fichiers générés excessifs.")
        files.append({"path": p.relative_to(root).as_posix(),
                      "bytes": size,
                      "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    files.sort(key=lambda x: x["path"])
    if not files:
        raise TeacherRenderError("Sortie professeur vide.")
    return files


def _single_teacher_html(files: list[dict], source_path: str,
                         claimed_html: dict | None = None) -> dict:
    """Reapply exactly the HTML identity and size requirements at every gate."""
    from quarto_versions import VersionError, _safe_source
    try:
        canonical = _safe_source(source_path)
    except (VersionError, TypeError) as exc:
        raise TeacherRenderError("Source QMD du manifeste non canonique.") from exc
    expected_html = ("dist/professeur/"
                     + PurePosixPath(canonical).with_suffix(".html").as_posix())
    html_files = [item for item in files
                  if isinstance(item, dict)
                  and isinstance(item.get("path"), str)
                  and item["path"].lower().endswith(".html")]
    if (len(html_files) != 1 or html_files[0]["path"] != expected_html
            or not isinstance(html_files[0].get("bytes"), int)
            or html_files[0]["bytes"] > MAX_HTML_BYTES
            or (claimed_html is not None and claimed_html != html_files[0])):
        raise TeacherRenderError("HTML professeur unique ou identité non conforme.")
    return html_files[0]


def verify_session(session: Path) -> dict:
    """Re-verify output from disk; does NOT authenticate the original renderer."""
    session = Path(session).expanduser().absolute()
    if session.is_symlink() or not session.is_dir():
        raise TeacherRenderError("Session absente ou symbolique.")
    manifest = session / "manifest.json"
    if not manifest.is_file() or manifest.is_symlink():
        raise TeacherRenderError("Manifeste absent ou symbolique.")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if (data.get("schema") != "alliage.quarto-professor-render.v0"
            or data.get("publication_performed") is not False
            or data.get("student_deployment_verified") is not False):
        raise TeacherRenderError("Manifeste Quarto non qualifié.")
    project = session / "project"
    if project.is_symlink() or not project.is_dir():
        raise TeacherRenderError("Répertoire projet absent ou symbolique.")
    if not project.resolve(strict=True).is_relative_to(session.resolve(strict=True)):
        raise TeacherRenderError("Projet hors session physique.")
    output = Path("dist/professeur")
    actual = _safe_tree_inventory(project, output)
    if actual != data.get("rendered_files"):
        raise TeacherRenderError("Intégrité des fichiers professeur perdue.")
    html = data.get("rendered_html")
    if not isinstance(html, dict):
        raise TeacherRenderError("Manifeste HTML non conforme.")
    verified = _single_teacher_html(actual, data.get("source_path"), html)
    return {"status": "LOCAL_PROFESSOR_FILES_REHASHED",
            "file_count": len(actual), "html_sha256": verified["sha256"],
            "publication_performed": False, "student_deployment_verified": False}


def _verify_tracked_copy(project: Path, expected: dict[str, str], *,
                         diagnose_integrity: bool = False) -> None:
    """Fail closed if Quarto rewrites a tracked blob in the throwaway copy.

    Optional *local-only* incident detail records relative paths and hashes,
    never file contents. It is NOT a permission to accept changed inputs.
    """
    anomalies: list[dict[str, str]] = []
    for name, digest in expected.items():
        target = project / _path(name)
        if target.is_symlink():
            kind, actual = "SYMLINK", None
        elif not target.is_file():
            kind, actual = "MISSING_OR_NONREGULAR", None
        else:
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            kind = "CONTENT_CHANGED" if actual != digest else None
        if kind is not None:
            anomalies.append({"path": name, "kind": kind,
                              "expected_sha256": digest,
                              "observed_sha256": actual})
    if anomalies:
        message = "Fichier Git suivi modifié par Quarto."
        if diagnose_integrity:
            message += (" Diagnostic local privé (aucun contenu) : "
                        + json.dumps({"count": len(anomalies),
                                      "first": anomalies[0]},
                                     ensure_ascii=True, sort_keys=True))
        raise TeacherRenderError(message)


def render(repo: Path, repository_id: str, source: str, working_ref: str,
           expected_sha: str, out: Path, *, trusted_quarto: bool = False,
           diagnose_integrity: bool = False) -> dict:
    """Execute trusted local Quarto once on a separate Git tree copy.

    Deliberately not a sandbox. Privileged hooks/extensions can still access
    the host, even with --no-execute. No claim of zero external side effects.
    """
    if not trusted_quarto:
        raise TeacherRenderError("Opt-in explicite --trusted-quarto obligatoire.")
    proof = plan(repo, repository_id, source, working_ref, expected_sha)
    repo = Path(repo).expanduser().resolve(strict=True)
    dest = _safe_destination(repo, out)
    if not shutil.which("quarto"):
        raise TeacherRenderError("Quarto indisponible : rendu réel non qualifié.")
    stage = Path(tempfile.mkdtemp(prefix="alliage-p36-private-", dir=dest.parent))
    stage.chmod(0o700)
    try:
        project = stage / "project"
        project.mkdir(mode=0o700)
        objects = _objects(repo, expected_sha)
        _preflight_objects(objects, source)
        expected: dict[str, str] = {}
        for name, mode, blob, size in objects:
            file = project / _path(name)
            file.parent.mkdir(parents=True, exist_ok=True)
            contents = _git(repo, "cat-file", "blob", blob)
            if len(contents) != size or contents.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                raise TeacherRenderError("Objet Git non conforme ou LFS non résolu.")
            file.write_bytes(contents)
            if mode == "100755":
                file.chmod(0o700)
            else:
                file.chmod(0o600)
            expected[name] = hashlib.sha256(contents).hexdigest()
        # Profile and engine must be selected explicitly, regardless of ambient
        # QUARTO_PROFILE. Sanitized child environment prevents inherited secrets.
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
               "HOME": str(stage), "XDG_CACHE_HOME": str(stage / "cache"),
               "QUARTO_PROFILE": "professeur", "LANG": "C.UTF-8",
               "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}
        cmd = ["quarto", "render", source, "--to", "html",
               "--profile", "professeur", "--no-execute"]
        try:
            result = subprocess.run(cmd, cwd=project, env=env,
                                    capture_output=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise TeacherRenderError("Rendu Quarto échoué ou expiré.") from exc
        if result.returncode != 0:
            # Never leak the potentially private Quarto error log into public
            # GitHub or the browser: data stay only in the private session.
            raise TeacherRenderError("Rendu Quarto non réussi (diagnostic masqué).")
        _verify_tracked_copy(project, expected, diagnose_integrity=diagnose_integrity)
        # The professor output must be the ONLY generated dist subtree.
        dist = project / "dist"
        if not dist.is_dir() or dist.is_symlink():
            raise TeacherRenderError("Sortie dist absente ou redirigée.")
        if sorted(x.name for x in dist.iterdir()) != ["professeur"]:
            raise TeacherRenderError("Profil élève ou sortie Quarto inattendue.")
        actual = _safe_tree_inventory(project, Path("dist/professeur"))
        html = _single_teacher_html(actual, source)
        for p in project.rglob("*"):
            if p.is_symlink():
                raise TeacherRenderError("Lien symbolique créé pendant le rendu.")
            if p.is_file():
                rel = p.relative_to(project).as_posix()
                if (rel not in expected and not rel.startswith("dist/professeur/")
                        and not rel.startswith(".quarto/")):
                    raise TeacherRenderError("Fichier créé hors sortie professeur.")
        manifest = {**proof,
                    "schema": "alliage.quarto-professor-render.v0",
                    "status": "PROFESSOR_RENDER_OBSERVED_LOCAL_ONLY",
                    "render_profile_requested": "professeur",
                    "render_profile_effective_verified": False,
                    "teacher_html_verified": True,
                    "rendered_html": html,
                    "rendered_files": actual,
                    "quarto_executed": True,
                    "read_only": False,
                    "source_checkout_modified": "NOT_VERIFIED",
                    "external_effects": "NOT_VERIFIED_NOT_SANDBOXED",
                    "publication_performed": False,
                    "student_deployment_verified": False}
        (stage / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(stage / "manifest.json", 0o600)
        os.replace(stage, dest)
        return manifest
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description="P3.6A Quarto professeur isolé ; jamais publié.")
    cli.add_argument("--repo", required=True, type=Path)
    cli.add_argument("--repository-id", required=True)
    cli.add_argument("--source", required=True)
    cli.add_argument("--working-ref", required=True)
    cli.add_argument("--expected-sha", required=True)
    mode = cli.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--render", action="store_true")
    cli.add_argument("--out", type=Path)
    cli.add_argument("--trusted-quarto", action="store_true")
    cli.add_argument("--diagnose-integrity", action="store_true",
                     help="Afficher localement le chemin Git du premier fichier altéré, sans son contenu.")
    args = cli.parse_args(argv)
    if args.check and (args.out or args.trusted_quarto or args.diagnose_integrity):
        cli.error("--check ne permet ni --out, ni --trusted-quarto, ni diagnostic")
    if args.render and (not args.out or not args.trusted_quarto):
        cli.error("--render exige --out ET --trusted-quarto")
    try:
        if args.check:
            result = plan(args.repo, args.repository_id, args.source,
                          args.working_ref, args.expected_sha)
        else:
            result = render(args.repo, args.repository_id, args.source,
                            args.working_ref, args.expected_sha, args.out,
                            trusted_quarto=True,
                            diagnose_integrity=args.diagnose_integrity)
    except (TeacherRenderError, TeacherProvenanceError, PreviewError,
            OSError, UnicodeError, ValueError) as exc:
        cli.exit(2, "REFUSED: " + str(exc) + "\n")
    print(json.dumps(result if args.check else {
        "status": result["status"], "commit": result["commit"],
        "rendered_html_sha256": result["rendered_html"]["sha256"],
        "session_path": str(args.out),
        "render_profile_effective_verified": result["render_profile_effective_verified"],
        "publication_performed": False, "student_deployment_verified": False
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
