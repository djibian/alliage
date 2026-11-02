# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.6E: reject known navigation mechanisms in *fictional* Quarto HTML.

This is an admission guard, NOT an HTML sanitizer, general browser parser,
or proof of absent exfiltration. No bytes are changed. CSP and Firefox
must still be tested independently. Never enable real professor sessions.
"""
from __future__ import annotations

from html.parser import HTMLParser
import re


class NavigationAdmissionError(ValueError):
    """A known browser navigation or eager-load trigger was detected."""


# Allow only same-document fragments, with deliberately small ASCII slugs.
# This is more restrictive than normal Quarto and may refuse valid content.
_FRAGMENT = re.compile(r"#[A-Za-z0-9_.:~-]*\Z", re.ASCII)
_BANNED_TAGS = frozenset({
    "base", "form", "iframe", "frame", "frameset", "object", "embed",
    "portal", "fencedframe",
})
_BANNED_REL = frozenset({
    "preconnect", "dns-prefetch", "prefetch", "prerender",
    "preload", "modulepreload", "pingback", "manifest",
})


class _NavigationGuard(HTMLParser):
    """Reject only the explicitly enumerated dangerous HTML constructs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _BANNED_TAGS:
            raise NavigationAdmissionError("Élément de navigation actif.")
        properties: dict[str, str | None] = {}
        for name, value in attrs:
            name = name.lower()
            if name in properties:
                # Ambiguous browser attribute precedence must not grant access.
                raise NavigationAdmissionError("Attribut HTML dupliqué.")
            properties[name] = value

        if tag == "meta" and (
            (properties.get("http-equiv") or "").strip().lower() == "refresh"
        ):
            raise NavigationAdmissionError("Redirection meta refresh.")
        if tag in ("a", "area"):
            if any(name in properties for name in (
                "ping", "download", "target", "formaction",
            )):
                raise NavigationAdmissionError("Navigation secondaire interdite.")
            if "href" in properties or "xlink:href" in properties:
                href = properties.get("href", properties.get("xlink:href"))
                if not isinstance(href, str) or not _FRAGMENT.fullmatch(href):
                    raise NavigationAdmissionError("Navigation hors document.")
        if "formaction" in properties:
            raise NavigationAdmissionError("Formulaire dynamique interdit.")

        if tag == "link":
            rel = (properties.get("rel") or "").lower().split()
            if set(rel) & _BANNED_REL:
                raise NavigationAdmissionError("Préchangement réseau interdit.")
            href = properties.get("href")
            if href is not None:
                # Embedded Quarto CSS is allowed without introducing hosts.
                # The browser CSP decides whether this passive resource loads.
                if not (rel == ["stylesheet"]
                        and href.lower().startswith("data:text/css,")):
                    raise NavigationAdmissionError("Lien head non autorisé.")


def require_static_navigation(html: bytes) -> None:
    """Refuse a selected class of navigation features; never rewrite bytes.

    HTMLParser is not specified to match Firefox's HTML5 error recovery.
    This check cannot establish the absence of all network exfiltration.
    """
    if type(html) is not bytes:
        raise NavigationAdmissionError("Octets HTML invalides.")
    try:
        text = html.decode("utf-8", errors="strict")
        parser = _NavigationGuard()
        parser.feed(text)
        parser.close()
    except (UnicodeError, ValueError) as exc:
        raise NavigationAdmissionError("HTML non admis.") from exc
