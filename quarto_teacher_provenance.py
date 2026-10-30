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
ROOT_PROFILE = re.compile(
    r"(?m)^profile:\n  default: eleve\n  group:\n    - \[eleve, professeur\](?:\n|$)")
ROOT_PROJECT = re.compile(
    r"(?m)^project:\n  type: default\n  output-dir: dist(?:\n|$)")


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
    if (root.count(b"\x00") or b"\r" in root or b"\t" in root
            or b"<<:" in root or re.search(rb"(?m)^\\s*[&*][A-Za-z0-9_-]+", root)):
        raise TeacherProvenanceError("Configuration racine ambiguë.")
    try:
        text = root.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise TeacherProvenanceError("Configuration Quarto non UTF-8.") from exc
    if (len(ROOT_PROFILE.findall(text)) != 1
            or len(ROOT_PROJECT.findall(text)) != 1
            or len(re.findall(r"(?m)^project:\s*$", text)) != 1
            or len(re.findall(r"(?m)^profile:\s*$", text)) != 1):
        raise TeacherProvenanceError("Profils enseignant/élève ou sortie racine non reconnus.")
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
