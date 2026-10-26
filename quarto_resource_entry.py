#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Opt-in URL to a real, unmodified Quarto preview page with a local history toolbar.

Experimental P3.2 extension surface, NOT canonical published resource identity.
Revalidates the P3.1 manifests point-in-time and writes no files. URL queries
are untrusted browser transport, NOT cryptographic attestations in Firefox.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote

from quarto_navigation import NavigationError, _load_version


def resource_entry_url(session: Path, *, reference: str = "V1",
                       observed: str = "V2", resource_id: str) -> str:
    """Return a file:// URL to the observed actual HTML, with optional UI metadata.

    Called only after P3.2 has built navigation.html from the same manifests.
    The browser overlay only displays the snapshot bytes; it never modifies
    the HTML or reads the resource's Git repository. It cannot verify integrity
    once the file is open.
    """
    session = Path(session).expanduser().absolute()
    root = (Path.home() / "alliage-experiences" / "historique").resolve()
    if (session.is_symlink() or not session.is_dir()
            or session.resolve().parent != root
            or not session.name.startswith("p31-final-observed-")
            or not (session / "navigation.html").is_file()
            or (session / "navigation.html").is_symlink()):
        raise NavigationError("Session de ressource historique locale non autorisée.")
    if reference != "V1" or observed != "V2" or not isinstance(resource_id, str):
        raise NavigationError("Pilote de ressource limité à V1 et V2.")
    if not re.fullmatch(r"quarto:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+:activite\\.qmd", resource_id):
        raise NavigationError("Identité de ressource Quarto pilote obligatoire.")

    # _load_version verifies rendered HTML, its SHA-256 and all tracked inputs
    # anew. Never infer a commit from the current checkout or a mutable ref.
    entries = [_load_version(session, name) for name in (reference, observed)]
    if entries[0]["commit"] == entries[1]["commit"]:
        raise NavigationError("Les SHA des aperçus doivent être différents.")
    if entries[0]["quarto_version"] != entries[1]["quarto_version"]:
        raise NavigationError("Moteurs Quarto différents.")

    # Only two pinned local revisions are ever navigated in the initial pilot.
    # No arbitrary file path, repository URL or remote site is accepted from
    # the query; the extension derives fixed paths from the current page.
    payload = {
        "schema": "alliage.quarto-resource-history.v0",
        "resource_id": resource_id,
        "reference_id": reference,
        "observed_id": observed,
        "entries": [{"id": e["id"], "commit": e["commit"]} for e in entries],
        "verification": "POINT_IN_TIME_ONLY",
        "deployment_verified": False,
        "publication_performed": False,
    }
    target = session / observed / "project/_site/activite.html"
    if not target.is_file() or target.is_symlink():
        raise NavigationError("HTML historique observé absent.")
    query = quote(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), safe="")
    return target.as_uri() + "?alliage-history-v0=" + query
