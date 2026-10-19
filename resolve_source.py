#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Alliage P2a — localise une sélection DOM dans une source Quarto, sans écriture.

Périmètre volontairement réduit : paragraphes/listes sur une seule ligne QMD,
avec Markdown simple. Échec fermé dès que la correspondance n'est pas unique
ou que le fichier local ne correspond pas à Git HEAD.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse


class LocalizationError(Exception):
    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True,
        encoding="utf-8", check=False,
    )
    if result.returncode:
        raise LocalizationError("GIT_ERROR", f"Git indisponible ou source non versionnée : {result.stderr.strip()[:300]}")
    return result.stdout.strip()


def expected_source_from_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise LocalizationError("INVALID_PAGE_URL", "L'URL de la page n'est pas une URL HTTP(S) valide.")
    # Contrat du premier prototype : la page publiée est sous /pedagogie/.
    prefix = "/pedagogie/"
    path = unquote(parsed.path)
    if not path.startswith(prefix) or not path.endswith(".html"):
        raise LocalizationError("UNSUPPORTED_PAGE_URL", "La page doit se terminer en .html sous /pedagogie/.")
    return path[len(prefix):-len(".html")] + ".qmd"


@dataclass(frozen=True)
class Projection:
    text: str
    offsets: tuple[int, ...]  # codepoint index in original whole QMD for each visible char
    line_number: int


def project_line(line: str, absolute_start: int, line_number: int) -> Projection | None:
    """Projection prudente d'une ligne Quarto simple vers le texte visible.

    Les transformations non gérées sont détectées par comparaison exacte au
    bloc HTML ; elles ne provoquent jamais une correspondance approximative.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith(("::: ", ":::", "<!--", "-->", "```", "~~~")):
        return None
    if re.fullmatch(r"-{3,}|\*{3,}", stripped):
        return None

    match = re.match(r"^\s*(?:[-+*]\s+(?:\[[ xX]\]\s+)?|\d+[.)]\s+|#{1,6}\s+)?", line)
    begin = match.end() if match else 0
    chars: list[str] = []
    offsets: list[int] = []
    i = begin
    # Supprimer les balises Markdown courantes sans substituer de texte.
    while i < len(line):
        if line.startswith("**", i) or line.startswith("__", i):
            i += 2
            continue
        if line[i] in "`":
            i += 1
            continue
        # Hyperliens markdown [libellé](url) : ne garder que le libellé.
        if line[i] == "[":
            end_label = line.find("]", i + 1)
            if end_label >= 0 and line[end_label + 1:end_label + 2] == "(":
                end_url = line.find(")", end_label + 2)
                if end_url >= 0:
                    for k in range(i + 1, end_label):
                        chars.append(line[k]); offsets.append(absolute_start + k)
                    i = end_url + 1
                    continue
        # Syntaxe d'échappement \* : n'afficher que le caractère échappé.
        if line[i] == "\\" and i + 1 < len(line) and line[i+1] in r"\\`*_{}[]()>#+-.!":
            i += 1
        chars.append(line[i]); offsets.append(absolute_start + i)
        i += 1
    while chars and chars[-1].isspace():
        chars.pop(); offsets.pop()
    while chars and chars[0].isspace():
        chars.pop(0); offsets.pop(0)
    return Projection("".join(chars), tuple(offsets), line_number)


def projections(qmd: str):
    in_frontmatter = qmd.startswith("---\n")
    in_fence = False
    absolute = 0
    for no, line in enumerate(qmd.splitlines(keepends=True), start=1):
        clean = line.strip()
        if in_frontmatter:
            if no != 1 and clean == "---":
                in_frontmatter = False
            absolute += len(line)
            continue
        if clean.startswith("```") or clean.startswith("~~~"):
            in_fence = not in_fence
            absolute += len(line)
            continue
        if not in_fence:
            p = project_line(line, absolute, no)
            if p and p.text:
                yield p
        absolute += len(line)


def locate(repo_root: Path, source_relative: str, capture: dict, require_sha: str | None = None) -> dict:
    repo_root = repo_root.expanduser().resolve()
    rel = Path(source_relative)
    try:
        actual_rel = str((repo_root / rel).resolve().relative_to(repo_root))
    except ValueError:
        raise LocalizationError("INVALID_PATH", "La source doit rester à l'intérieur du dépôt.")
    derived_rel = expected_source_from_url(capture.get("page", {}).get("url", ""))
    if actual_rel != derived_rel:
        raise LocalizationError("PAGE_SOURCE_MISMATCH", f"Le fichier attendu pour cette URL est : {derived_rel}")
    if capture.get("schema") != "pedagolab.selection.v0":
        raise LocalizationError("UNSUPPORTED_SCHEMA", "Ce programme attend pedagolab.selection.v0.")
    dom, quote = capture.get("dom", {}), capture.get("quote", {})
    full = dom.get("blockText")
    exact = quote.get("exact")
    a, b = dom.get("startUtf16"), dom.get("endUtf16")
    if not isinstance(full, str) or not isinstance(exact, str) or not exact:
        raise LocalizationError("INVALID_CAPTURE", "Texte du bloc ou citation manquant.")
    if type(a) is not int or type(b) is not int or a < 0 or b <= a:
        raise LocalizationError("INVALID_CAPTURE", "Positions DOM invalides.")
    # Les offsets DOM sont UTF-16 ; ne jamais les interpréter comme des index Python.
    utf16 = full.encode("utf-16-le")
    if 2 * b > len(utf16):
        raise LocalizationError("INVALID_CAPTURE", "Positions DOM hors du texte.")
    try:
        selected = utf16[2*a:2*b].decode("utf-16-le")
    except UnicodeDecodeError:
        raise LocalizationError("INVALID_CAPTURE", "Sélection coupant un caractère UTF-16.")
    if selected != exact or dom.get("exactMatchesBlockSlice") is not True:
        raise LocalizationError("DOM_MISMATCH", "Le passage sélectionné diverge des coordonnées DOM.")
    prefix = quote.get("prefix", "")
    suffix = quote.get("suffix", "")
    if not isinstance(prefix, str) or not isinstance(suffix, str):
        raise LocalizationError("INVALID_CAPTURE", "Contexte de citation invalide.")
    before = utf16[:2*a].decode("utf-16-le")
    after = utf16[2*b:].decode("utf-16-le")
    if not before.endswith(prefix):
        raise LocalizationError("CONTEXT_MISMATCH", "Préfixe discordant.")
    if not after.startswith(suffix):
        raise LocalizationError("CONTEXT_MISMATCH", "Suffixe discordant.")
    file_path = repo_root / actual_rel
    if not file_path.is_file():
        raise LocalizationError("FILE_MISSING", "Le fichier .qmd n'existe pas dans ce dépôt local.")
    head = git(repo_root, "rev-parse", "HEAD")
    if require_sha and head != require_sha:
        raise LocalizationError("UNEXPECTED_COMMIT", f"HEAD={head}, attendu={require_sha}.")
    tracked_blob = git(repo_root, "rev-parse", f"HEAD:{actual_rel}")
    current_blob = git(repo_root, "hash-object", "--", str(file_path))
    if current_blob != tracked_blob:
        raise LocalizationError("DIRTY_SOURCE", "Le .qmd a changé localement depuis HEAD : refus de l'ancrage.")
    contents = file_path.read_text(encoding="utf-8")
    candidates: list[tuple[Projection, int]] = []
    for p in projections(contents):
        if p.text == full:
            begin = p.text.find(exact)
            while begin >= 0:
                end = begin + len(exact)
                if p.text[:begin].endswith(prefix) and p.text[end:].startswith(suffix):
                    candidates.append((p, begin))
                begin = p.text.find(exact, begin + 1)
    if not candidates:
        raise LocalizationError("SOURCE_NOT_FOUND", "Aucun bloc source d'une seule ligne ne correspond exactement au bloc HTML.")
    if len(candidates) > 1:
        raise LocalizationError("AMBIGUOUS_SOURCE", f"{len(candidates)} passages sources indiscernables : modification interdite.")
    projection, start = candidates[0]
    source_start = projection.offsets[start]
    source_end = projection.offsets[start + len(exact) - 1] + 1
    if contents[source_start:source_end] != exact:
        raise LocalizationError("INLINE_MARKUP", "Le texte choisi traverse du balisage Markdown : cas non pris en charge.")
    # Les coordonnées source sont définies explicitement en octets UTF-8.
    start_utf8 = len(contents[:source_start].encode("utf-8"))
    end_utf8 = len(contents[:source_end].encode("utf-8"))
    source_lines = contents.splitlines(keepends=True)
    offset_of_line = sum(len(x) for x in source_lines[:projection.line_number-1])
    return {
        "schema": "pedagolab.source-anchor.v0",
        "status": "LOCATED_READ_ONLY",
        "page": {"url": capture["page"]["url"], "revision_verified": False},
        "source": {
            "repository": str(repo_root),
            "path": actual_rel,
            "commit": head,
            "git_blob": current_blob,
            "sha256": hashlib.sha256(contents.encode("utf-8")).hexdigest(),
            "line": projection.line_number,
            "start_column": source_start - offset_of_line + 1,
            "end_column_exclusive": source_end - offset_of_line + 1,
            "start_utf8": start_utf8,
            "end_utf8_exclusive": end_utf8,
            "exact": exact,
        },
        "safety": {"write_permitted": False, "reason": "Correspondance avec le rendu publié et contrôle de modification non implémentés."},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Localise une sélection d’Alliage dans un .qmd versionné (lecture seule).")
    parser.add_argument("--repo", type=Path, required=True, help="Dossier local de djibian/pedagogie")
    parser.add_argument("--selection", type=Path, required=True, help="Ancre JSON copiée depuis l'extension")
    parser.add_argument("--expect-commit", help="SHA Git facultatif à imposer")
    args = parser.parse_args()
    try:
        capture = json.loads(args.selection.read_text(encoding="utf-8"))
        source = expected_source_from_url(capture["page"]["url"])
        result = locate(args.repo, source, capture, args.expect_commit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (LocalizationError, KeyError, ValueError, OSError, json.JSONDecodeError) as exc:
        reason = exc.reason if isinstance(exc, LocalizationError) else "INVALID_INPUT"
        print(json.dumps({"schema": "pedagolab.source-anchor.v0", "status": "UNRESOLVED", "reason": reason,
                          "detail": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
