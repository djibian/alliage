#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Produce a local *read-only* Firefox navigation page from P3.1 manifests.

This file does not invoke Quarto, modify Git, start a server, or publish.
Validation is a point-in-time check: Firefox does not rehash files on display.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import quote


class NavigationError(ValueError):
    """Refuse an ambiguous, altered, or unauthorized preview session."""


SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
VERSION = re.compile(r"V[1-9][0-9]?\Z")
SCHEMA = "alliage.quarto-navigation.v0"


def _relative(name: object) -> Path:
    if not isinstance(name, str) or not name or name.startswith("/") or "\\" in name:
        raise NavigationError("Chemin d'aperçu invalide.")
    parts = PurePosixPath(name).parts
    if (not parts or any(p in ("", ".", "..", ".git") for p in parts)
            or any("\x00" in p or ":" in p for p in parts)):
        raise NavigationError("Chemin d'aperçu non autorisé.")
    # pathlib folds ./, duplicate slashes and inner /./ segments.
    # Manifest paths must be canonical BEFORE hashing or comparing them.
    if name != str(PurePosixPath(name)):
        raise NavigationError("Chemin d'aperçu non canonique.")
    return Path(*parts)


def _regular_within(base: Path, name: object) -> Path:
    relative = _relative(name)
    result = base / relative
    current = base
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise NavigationError("Lien symbolique interdit dans l'aperçu.")
    if not result.is_file() or result.stat().st_size > 20 * 1024 * 1024 or base.resolve() not in result.resolve().parents:
        raise NavigationError("Fichier d'aperçu absent ou hors session.")
    return result


def _matches(path: Path, expected: object) -> bool:
    if not isinstance(expected, str) or not SHA256.fullmatch(expected):
        raise NavigationError("Empreinte SHA-256 absente ou incorrecte.")
    return hashlib.sha256(path.read_bytes()).hexdigest() == expected



def _verify_rendered_files(folder: Path, rendered: dict, inventory: object) -> bool:
    """Verify every regular output under _site, with no untracked extras.

    Backward compatible with older P3.1 manifests (return False). The new
    resource-first entry refuses that unverifiable legacy case.
    """
    if inventory is None:
        return False
    if not isinstance(inventory, list) or not 1 <= len(inventory) <= 2000:
        raise NavigationError("Inventaire des dépendances Quarto invalide.")
    site = folder / "project" / "_site"
    if site.is_symlink() or not site.is_dir():
        raise NavigationError("Dossier de sortie Quarto absent ou symbolique.")
    expected = {}
    total = 0
    for item in inventory:
        if not isinstance(item, dict):
            raise NavigationError("Dépendance rendue invalide.")
        name = item.get("path")
        if not isinstance(name, str) or not name.startswith("project/_site/"):
            raise NavigationError("Chemin de dépendance Quarto invalide.")
        canonical = str(_relative(name))
        if canonical != name or name in expected:
            raise NavigationError("Dépendance Quarto dupliquée ou non canonique.")
        file = _regular_within(folder, name)
        size = item.get("bytes")
        if type(size) is not int or size < 0 or size != file.stat().st_size:
            raise NavigationError("Taille de dépendance Quarto différente.")
        total += size
        if total > 100 * 1024 * 1024:
            raise NavigationError("Dépendances Quarto trop volumineuses.")
        if not _matches(file, item.get("sha256")):
            raise NavigationError("Dépendance Quarto générée modifiée.")
        expected[name] = item["sha256"]
    if rendered["path"] not in expected or expected[rendered["path"]] != rendered.get("sha256"):
        raise NavigationError("HTML absent des dépendances Quarto attestées.")
    observed = set()
    for path in site.rglob("*"):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise NavigationError("Sortie Quarto symbolique ou non régulière.")
        if path.is_file():
            observed.add("project/" + path.relative_to(folder / "project").as_posix())
            if len(observed) > 2000:
                raise NavigationError("Sorties Quarto trop nombreuses.")
    if observed != set(expected):
        raise NavigationError("Inventaire des sorties Quarto incomplet ou altéré.")
    return True


def _load_version(session: Path, version: str) -> dict:
    folder = session / version
    if folder.is_symlink() or not folder.is_dir():
        raise NavigationError("Dossier de révision absent ou symbolique.")
    manifest_path = _regular_within(folder, "manifest.json")
    if manifest_path.stat().st_size > 2_000_000:
        raise NavigationError("Manifeste trop volumineux.")
    try:
        report = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise NavigationError("Manifeste non lisible.") from exc
    if not isinstance(report, dict) or report.get("schema") != "alliage.quarto-historical-preview.v0":
        raise NavigationError("Schéma de manifeste Quarto non pris en charge.")
    commit = report.get("commit")
    if not isinstance(commit, str) or not SHA40.fullmatch(commit):
        raise NavigationError("Commit Git absent ou incomplet.")
    if (report.get("render_status") != "RENDERED_FROM_GIT_SNAPSHOT"
            or report.get("publication_status") != "NOT_INITIATED_BY_ALLIAGE"
            or report.get("deployment_verified") is not False
            or report.get("external_render_effects") != "NOT_VERIFIED"):
        raise NavigationError("Statut de rendu ou de publication ambigu.")
    rendered = report.get("rendered_html")
    if (not isinstance(rendered, dict) or rendered.get("existed_before_render") is not False):
        raise NavigationError("Provenance HTML non validée.")
    source = report.get("source_path")
    if not isinstance(source, str) or not source.endswith(".qmd"):
        raise NavigationError("Source Quarto absente.")
    _relative(source)
    expected_html = str(PurePosixPath(source).with_suffix(".html"))
    allowed_html = {"project/" + expected_html, "project/_site/" + expected_html}
    if not isinstance(rendered.get("path"), str) or rendered["path"] not in allowed_html:
        raise NavigationError("HTML différent de la source Quarto attestée.")
    if not isinstance(report.get("quarto_version"), str) or not report["quarto_version"]:
        raise NavigationError("Version du moteur Quarto non attestée.")
    html_file = _regular_within(folder, rendered["path"])
    if not _matches(html_file, rendered.get("sha256")):
        raise NavigationError("HTML historique modifié depuis son rendu.")
    tracked = report.get("tracked_files")
    if not isinstance(tracked, list) or not 1 <= len(tracked) <= 2000:
        raise NavigationError("Inventaire de fichiers Git invalide.")
    present = {}
    for item in tracked:
        if not isinstance(item, dict) or "path" not in item:
            raise NavigationError("Entrée Git invalide.")
        p = item["path"]
        canonical = str(_relative(p))
        if p != canonical:
            raise NavigationError("Chemin Git non canonique.")
        if canonical in present:
            raise NavigationError("Fichier Git dupliqué dans le manifeste.")
        path = _regular_within(folder, "project/" + canonical)
        if not _matches(path, item.get("sha256")):
            raise NavigationError("Dépendance Git modifiée depuis le rendu.")
        present[canonical] = item["sha256"]
    # P3.1 refuses rendering whenever either candidate HTML already exists
    # before Quarto runs. A tracked candidate therefore contradicts the
    # manifest's existed_before_render=false, even with correct SHA-256.
    forbidden_preexisting_html = {expected_html, "_site/" + expected_html}
    if forbidden_preexisting_html.intersection(present):
        raise NavigationError("Manifeste contradictoire : HTML candidat suivi par Git.")
    if source not in present or present[source] != report.get("source_sha256"):
        raise NavigationError("Identité de la source non démontrée.")
    assets_verified = _verify_rendered_files(folder, rendered, report.get("rendered_files"))
    return {"id": version, "commit": commit, "source_sha256": present[source],
            "source_path": source, "rendered_html_path": rendered["path"],
            "rendered_files_verified": assets_verified,
            "rendered_css_verified": assets_verified and any(
                item["path"] == "project/_site/styles.css"
                for item in report["rendered_files"]),
            "html": "./" + quote(version + "/" + rendered["path"], safe="/"),
            "quarto_version": report["quarto_version"],
            "publication_status": "NOT_INITIATED_BY_ALLIAGE"}


def build_navigation(session: Path, versions: list[str], reference: str) -> Path:
    """Create one new navigation.html beside immutable P3.1 revision folders."""
    session = Path(session).expanduser().absolute()
    root = (Path.home() / "alliage-experiences" / "historique").resolve()
    if (session.is_symlink() or not session.is_dir()
            or session.resolve().parent != root or not session.name.startswith("p31-final-")):
        raise NavigationError("La session doit être un dossier p31-final-* du laboratoire local.")
    if not isinstance(versions, list) or not 2 <= len(versions) <= 20:
        raise NavigationError("Entre deux et vingt versions requises.")
    if any(not isinstance(v, str) or not VERSION.fullmatch(v) for v in versions):
        raise NavigationError("Noms de versions pilotes invalides.")
    if len(set(versions)) != len(versions) or reference not in versions:
        raise NavigationError("Versions dupliquées ou référence inconnue.")
    target = session / "navigation.html"
    if target.exists() or target.is_symlink():
        raise NavigationError("La page de navigation existe déjà : aucun écrasement.")
    entries = [_load_version(session, item) for item in versions]
    if len({e["commit"] for e in entries}) != len(entries):
        raise NavigationError("Les révisions doivent avoir des SHA distincts.")
    if len({e["quarto_version"] for e in entries}) != 1:
        raise NavigationError("Versions du moteur Quarto différentes : comparaison refusée.")
    # The reference is chosen by the user; it is NOT claimed to be the
    # actual current Git branch or the version deployed to learners.
    payload = {"schema": SCHEMA, "reference_id": reference,
               "entries": entries, "deployment_verified": False,
               "reference_is_working_tree": False,
               "verification": "POINT_IN_TIME_ONLY"}
    serial = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # JSON in a script element must never allow an HTML closing tag.
    serial = serial.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    initial = next(e for e in entries if e["id"] == reference)
    src = html.escape(initial["html"], quote=True)
    markup = ('<!doctype html>\n<html lang="fr">\n<head><meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
              '<title>Alliage — historique Quarto local</title>\n'
              '<style>html,body{height:100%;margin:0;font:14px system-ui,sans-serif;}'
              '#alliage-preview-frame{width:100%;height:100vh;border:0;display:block;}'
              '#alliage-fallback{position:fixed;z-index:10;left:8px;bottom:8px;'
              'font-size:12px;background:#fff;color:#222;padding:5px;opacity:.7;}</style>\n'
              '</head><body>\n'
              '<iframe id="alliage-preview-frame" title="Aperçu historique Quarto"'
              ' referrerpolicy="no-referrer" src="' + src + '"></iframe>\n'
              '<p id="alliage-fallback">Alliage : extension Firefox requise pour naviguer.'
              " Alliage n'a déclenché aucune publication. Aucun déploiement vérifié.</p>\n"
              '<script type="application/json" id="alliage-history-data">' + serial + '</script>\n'
              '</body></html>\n')
    # Exclusive create; no alteration of prior snapshots or their manifests.
    with target.open("x", encoding="utf-8") as out:
        out.write(markup)
    return target


def main() -> int:
    ap = argparse.ArgumentParser(description="Préparer une navigation Firefox locale attestée.")
    ap.add_argument("--session", type=Path, required=True)
    ap.add_argument("--versions", nargs="+", default=["V1", "V2", "V3"])
    ap.add_argument("--reference", default="V3",
                    help="Révision de référence explicitement choisie, pas un HEAD Git prouvé.")
    args = ap.parse_args()
    try:
        target = build_navigation(args.session, args.versions, args.reference)
    except (OSError, NavigationError) as exc:
        ap.exit(2, "REFUSED: " + str(exc) + "\n")
    print(target.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
