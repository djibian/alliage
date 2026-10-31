#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.5: probe one canonical Quarto teacher source at an explicit Git revision.

Discovery ONLY. Does not read render outputs, run Quarto, serve HTML, fetch Git,
switch branches, modify files, or claim an open browser page is authenticated.
The effective Quarto profile and confidentiality of its output remain unproven.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from quarto_versions import VersionError, _git, _safe_ref, _safe_source, _sha, _snapshot
from quarto_branch_delta import _assert_complete_unmodified_ancestry, _tree


class TeacherProvenanceError(ValueError):
    """Stop when local source or the declared teacher/student boundary is ambiguous."""


SHA = re.compile(r"[0-9a-f]{40}\Z")
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
PROFILE_CONTENT = {
    "professeur": b"project:\n  output-dir: dist/professeur\n",
    "eleve": b"project:\n  output-dir: dist/eleve\n",
}
# P3.5 is intentionally NOT a general YAML reader. It recognizes only a
# small, completely consumed structural subset matching the declared Quarto
# project/profile format. A fragment match is insufficient: extra keys,
# duplicate keys, flow mappings, tags, anchors, aliases, and extra YAML
# documents must fail closed rather than silently change profile semantics.
_QUOTED_GLOB = re.compile(r'    - "[A-Za-z0-9_./*?-]+"')

def _safe_quoted_glob(line: str) -> bool:
    """Reject absolute/parent/empty Git-scoped globs before future Quarto runs."""
    if _QUOTED_GLOB.fullmatch(line) is None:
        return False
    path = line[len('    - "'): -1]
    return all(part not in ("", ".", "..", ".git") for part in path.split("/"))


# Plain YAML path scalars are deliberately narrower than generic Quarto
# values. A bare "-" changes YAML sequence semantics, numeric-only values
# become numbers, and keywords like true/null/on can become bool/null.
# Paths in this qualified subset start with a letter or underscore; other
# legitimate YAML spellings must be qualified separately, not guessed.
_PATH_SCALAR = re.compile(r"[A-Za-z_][A-Za-z0-9_./-]*\Z")
_YAML_NON_STRING_SCALARS = frozenset({
    "true", "false", "null", "yes", "no", "on", "off", "y", "n",
})


def _plain_yaml_path(value: str | None) -> bool:
    """Recognize only unambiguous YAML *strings* denoting relative paths."""
    return (isinstance(value, str)
            and _PATH_SCALAR.fullmatch(value) is not None
            and value.casefold() not in _YAML_NON_STRING_SCALARS
            and all(part not in ("", ".", "..", ".git")
                    for part in value.split("/")))


def _recognize_root_config(root: bytes) -> None:
    """Validate the entire limited YAML grammar, not selected substrings.

    This does not attest Quarto's actual interpretation or a rendered page.
    Adding syntax requires dedicated adversarial tests and requalification.
    """
    if (not root or b"\x00" in root or b"\r" in root or b"\t" in root
            or root.startswith(b"\xef\xbb\xbf")):
        raise TeacherProvenanceError("Configuration Quarto racine non canonique.")
    try:
        content = root.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise TeacherProvenanceError("Configuration Quarto non UTF-8.") from exc
    sections: dict[str, list[str]] = {}
    active = None
    for line in content.split("\n"):
        if not line:
            continue
        if line != line.rstrip() or line.startswith("#"):
            raise TeacherProvenanceError("Commentaires ou espaces YAML non qualifiés.")
        # All recognized root keys have an exact spelling, value and layout.
        # Unrecognized root declarations, even valid YAML, are outside P3.5.
        if not line.startswith(" "):
            key = {"project:": "project", "profile:": "profile",
                   "format:": "format", "lang: fr": "lang"}.get(line)
            if key is None or key in sections:
                raise TeacherProvenanceError("Déclaration racine YAML inconnue ou dupliquée.")
            sections[key] = []
            active = key
        else:
            if active is None or len(line) - len(line.lstrip(" ")) not in (2, 4, 6):
                raise TeacherProvenanceError("Indentation YAML non reconnue.")
            sections[active].append(line)

    if "project" not in sections or "profile" not in sections:
        raise TeacherProvenanceError("Déclarations projet et profil requises.")

    project = sections["project"]
    if (len(project) != 6 or project[:3] !=
            ["  type: default", "  output-dir: dist", "  render:"] or
            not _safe_quoted_glob(project[3]) or
            project[4] != "  resources:" or
            not _safe_quoted_glob(project[5])):
        raise TeacherProvenanceError("Structure project Quarto non reconnue.")

    if sections["profile"] != [
            "  default: eleve", "  group:", "    - [eleve, professeur]"]:
        raise TeacherProvenanceError("Groupes de profils Quarto ambigus ou contradictoires.")
    if "lang" in sections and sections["lang"]:
        raise TeacherProvenanceError("Bloc lang Quarto ambigu.")

    # Format options are not interpreted as Quarto behavior. They are still
    # lexically/structurally validated so malformed YAML cannot slip through
    # unrelated lines and invalidate the recognized project/profile tree.
    formats = sections.get("format", [])
    current = None
    seen_formats: set[str] = set()
    seen_keys: set[str] = set()
    filter_items = 0
    filter_open = False
    allowed = {
        "html": {"toc", "embed-resources", "page-layout", "format-links", "css"},
        "odt": {"toc", "page-width", "reference-doc", "filters"},
    }
    values = {
        "toc": {"true", "false"},
        "embed-resources": {"true", "false"},
        "page-layout": {"full"},
        "format-links": {"true", "false"},
        "page-width": {"7"},
    }
    for line in formats:
        if line in ("  html:", "  odt:"):
            if filter_open and not filter_items:
                raise TeacherProvenanceError("Liste de filtres Quarto vide.")
            current = line.strip()[:-1]
            if current in seen_formats:
                raise TeacherProvenanceError("Format Quarto dupliqué.")
            seen_formats.add(current)
            seen_keys = set()
            filter_open = False
        elif line.startswith("    ") and not line.startswith("      "):
            if filter_open and not filter_items:
                raise TeacherProvenanceError("Liste de filtres Quarto vide.")
            match = re.fullmatch(r"    ([a-z-]+):(?: ([A-Za-z0-9_./-]+))?", line)
            if not match or current is None:
                raise TeacherProvenanceError("Option Quarto mal formée.")
            name, value = match.groups()
            if name not in allowed[current] or name in seen_keys:
                raise TeacherProvenanceError("Option Quarto inconnue ou dupliquée.")
            seen_keys.add(name)
            filter_open = name == "filters"
            filter_items = 0
            if filter_open:
                if value is not None:
                    raise TeacherProvenanceError("Liste de filtres Quarto non reconnue.")
            elif name in values:
                if value not in values[name]:
                    raise TeacherProvenanceError("Valeur d'option Quarto non reconnue.")
            elif not _plain_yaml_path(value):
                raise TeacherProvenanceError("Chemin Quarto YAML ambigu ou non reconnu.")
        elif line.startswith("      - "):
            value = line[len("      - "):]
            if (not filter_open or current != "odt"
                    or not _plain_yaml_path(value)):
                raise TeacherProvenanceError("Élément de liste Quarto invalide.")
            filter_items += 1
        else:
            raise TeacherProvenanceError("Structure YAML Quarto non reconnue.")
    if filter_open and not filter_items:
        raise TeacherProvenanceError("Liste de filtres Quarto vide.")
    if "format" in sections and not seen_formats:
        raise TeacherProvenanceError("Format Quarto vide.")



def _git_regular_file(repo: Path, commit: str, path: str) -> tuple[bytes, str]:
    """Read exact regular blob at the pinned commit; never inspect a worktree file."""
    raw = _git(repo, "ls-tree", "-z", commit, "--", path)
    if not raw.endswith(b"\x00") or raw.count(b"\x00") != 1:
        raise TeacherProvenanceError("Configuration Quarto manquante ou ambiguë.")
    row = raw[:-1]
    if b"\t" not in row:
        raise TeacherProvenanceError("Entrée Git de configuration invalide.")
    header, name = row.split(b"\t", 1)
    match = re.fullmatch(rb"(100644|100755) blob ([0-9a-f]{40})", header)
    if not match or name != path.encode("utf-8"):
        raise TeacherProvenanceError("Configuration Quarto non régulière ou redirigée.")
    blob = match.group(2).decode("ascii")
    data = _git(repo, "cat-file", "blob", blob)
    if len(data) > 65536:
        raise TeacherProvenanceError("Configuration Quarto trop volumineuse.")
    return data, blob


def _verify_declarations(repo: Path, commit: str) -> dict:
    """Recognize one deliberately narrow config; NOT a generic YAML interpreter.

    Whitespace, aliases, extra profile settings or changed project semantics
    require a separate qualification. Return only hashes, never YAML contents.
    """
    root, root_blob = _git_regular_file(repo, commit, "_quarto.yml")
    _recognize_root_config(root)
    profiles = {}
    for profile, exact in PROFILE_CONTENT.items():
        name = "_quarto-" + profile + ".yml"
        data, blob = _git_regular_file(repo, commit, name)
        if data != exact:
            raise TeacherProvenanceError(
                "Profil Quarto " + profile + " non reconnu ; aucune sortie attestée.")
        profiles[profile] = {"config_git_blob": blob,
                             "config_sha256": hashlib.sha256(data).hexdigest(),
                             "output_dir_declared": "dist/" + profile}
    return {"root_config_git_blob": root_blob,
            "root_config_sha256": hashlib.sha256(root).hexdigest(),
            "profiles": profiles,
            "declarations_recognized_not_effective_render_verified": True}


def probe(repo: Path, repository_id: str, source: str, working_ref: str,
          expected_sha: str) -> dict:
    """Inspect an explicit pinned Git revision and *declared* Quarto profiles.

    This is a prerequisite to binding a real professor browser document;
    no browser URL is considered trusted and no local render is performed.
    """
    if (not isinstance(repository_id, str)
            or not REPOSITORY.fullmatch(repository_id)
            or any(part in (".", "..") for part in repository_id.split("/"))):
        raise TeacherProvenanceError("Identité explicite owner/repo attendue.")
    try:
        source = _safe_source(source)
        working_ref = _safe_ref(working_ref)
    except VersionError as exc:
        raise TeacherProvenanceError(str(exc)) from exc
    if not isinstance(expected_sha, str) or not SHA.fullmatch(expected_sha):
        raise TeacherProvenanceError("SHA attendu complet (40 caractères) obligatoire.")
    try:
        repo = Path(repo).expanduser().resolve(strict=True)
        if Path(_git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve() != repo:
            raise TeacherProvenanceError("La racine exacte du dépôt est requise.")
        _assert_complete_unmodified_ancestry(repo)
        commit = _sha(repo, working_ref)
        if commit != expected_sha:
            raise TeacherProvenanceError("Référence mouvante : SHA différent de l'attendu.")
        snap = _snapshot(repo, commit, source)
        tree = _tree(repo, commit)
        config = _verify_declarations(repo, commit)
        # Deliberately do NOT inspect the mutable worktree: git status can
        # refresh index metadata and it would not prove browser provenance.
        # The Git object graph at the explicit commit is the only evidence.
        if _sha(repo, working_ref) != expected_sha:
            raise TeacherProvenanceError("Référence modifiée pendant la lecture.")
    except (VersionError, OSError, UnicodeError) as exc:
        raise TeacherProvenanceError("Lecture Git refusée : " + str(exc)) from exc
    return {
        "schema": "alliage.quarto-teacher-source-probe.v0",
        "status": "SOURCE_PINNED_PROFILES_DECLARED_RENDER_NOT_VERIFIED",
        "resource_id": f"quarto:{repository_id}:{source}",
        "repository_id_scope": "DECLARED_NOT_REMOTE_AUTHENTICATED",
        "source_path": source,
        "working_ref": working_ref,
        "working_commit": commit,
        "working_tree_git_sha": tree,
        "source_git_blob": snap["git_blob"],
        "source_sha256": snap["sha256"],
        "checkout_head_matches_ref": None,
        "checkout_clean_at_observation": None,
        "checkout_bytes_verified": False,
        "profiles": config,
        "teacher_profile": "professeur",
        "learner_profile": "eleve",
        "profile_effective_render_verified": False,
        "teacher_html_url_verified": False,
        "published_html_url_verified": False,
        "teacher_content_exposure_authorized": False,
        "student_deployment_verified": False,
        "publication_performed": False,
        "network_access_performed_by_alliage": False,
        "quarto_executed": False,
        "read_only": True,
        "next_gate": "ISOLATED_REAL_PROFESSOR_RENDER_AND_BROWSER_PROVENANCE",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Qualifier la source Git et les profils Quarto déclarés, sans rendu ni publication.")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--working-ref", required=True,
                        help="Référence complète refs/heads/... ou refs/remotes/...")
    parser.add_argument("--expected-sha", required=True,
                        help="SHA40 explicite à protéger contre une évolution de branche")
    args = parser.parse_args(argv)
    try:
        result = probe(args.repo, args.repository_id, args.source,
                       args.working_ref, args.expected_sha)
    except (TeacherProvenanceError, OSError) as exc:
        parser.exit(2, "REFUSED: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
