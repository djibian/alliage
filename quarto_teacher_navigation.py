# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.6E: fictional HTML5-DOM admission guard, not browser confinement.

Inspect the DOM built by an HTML5 parser, including SVG/MathML namespaces.
Do not modify the P3.6A-verified bytes. This cannot prevent all network
requests/navigation and MUST NEVER authorize a real professor session.
"""
from __future__ import annotations

import re

try:
    import html5lib
except ImportError as exc:
    raise RuntimeError(
        "P3.6E requiert html5lib 1.1 : refus sans analyse HTML5."
    ) from exc


class NavigationAdmissionError(ValueError):
    """A navigation-capable construction was found in fictitious HTML."""


_FRAGMENT = re.compile(r"#[A-Za-z0-9_.:~-]*\Z", re.ASCII)
_INITIAL_DOCTYPE = re.compile(r"\A\s*<!doctype\s+html\s*>", re.IGNORECASE)
_DECLARATION_OPENER = re.compile(r"<!|<\?|<%", re.IGNORECASE)
_HTML = "http://www.w3.org/1999/xhtml"
_SVG = "http://www.w3.org/2000/svg"
_MATHML = "http://www.w3.org/1998/Math/MathML"
_XLINK = "http://www.w3.org/1999/xlink"
_BANNED_TAGS = frozenset({
    "base", "form", "iframe", "frame", "frameset", "object", "embed",
    "portal", "fencedframe", "set", "animate", "animatemotion",
    "animatetransform", "animatecolor", "discard",
})
_BANNED_REL = frozenset({
    "preconnect", "dns-prefetch", "prefetch", "prerender", "preload",
    "modulepreload", "pingback", "manifest",
})


def _require_unambiguous_markup(text: str) -> None:
    """Restricted fiction-only syntax; Quarto's simple comments are allowed.

    This is a conservative supplementary check, not the DOM parser. Forbid
    ambiguous comments/declarations because HTML5 recovery can differ across
    browser/parser versions even when the DOM library is standards-oriented.
    """
    doctype = _INITIAL_DOCTYPE.match(text)
    offset = doctype.end() if doctype else 0
    while True:
        match = _DECLARATION_OPENER.search(text, offset)
        if match is None:
            return
        start = match.start()
        if not text.startswith("<!--", start):
            raise NavigationAdmissionError("Déclaration HTML ambiguë.")
        end = text.find("-->", start + 4)
        if end < 0:
            raise NavigationAdmissionError("Commentaire HTML non terminé.")
        body = text[start + 4:end]
        if "<" in body or ">" in body or "--" in body:
            raise NavigationAdmissionError("Commentaire HTML ambigu.")
        offset = end + 3


def _qualified_name(name: str) -> tuple[str, str]:
    if name.startswith("{"):
        namespace, _, local = name[1:].partition("}")
        return namespace, local.lower()
    return "", name.lower()


def _check_element(element) -> None:
    if not isinstance(element.tag, str):
        return  # HTML5 comment node; lexical preflight validated its shape.
    namespace, tag = _qualified_name(element.tag)
    if namespace not in (_HTML, _SVG, _MATHML):
        raise NavigationAdmissionError("Espace de noms HTML non admis.")
    if tag in _BANNED_TAGS:
        raise NavigationAdmissionError("Élément de navigation actif.")

    attributes = {}
    href_attrs = []
    for qualified, value in element.attrib.items():
        attr_ns, local = _qualified_name(qualified)
        key = ("xlink:" + local) if attr_ns == _XLINK else local
        if key in attributes:
            raise NavigationAdmissionError("Attribut HTML ambigu.")
        attributes[key] = value
        if local == "href":
            href_attrs.append((attr_ns, value))

    if tag == "meta" and namespace == _HTML and (
        (attributes.get("http-equiv") or "").strip().lower() == "refresh"
    ):
        raise NavigationAdmissionError("Redirection meta refresh.")
    if "formaction" in attributes:
        raise NavigationAdmissionError("Formulaire dynamique interdit.")

    is_anchor = ((tag == "a" and namespace in (_HTML, _SVG))
                 or (tag == "area" and namespace == _HTML))
    is_stylesheet_link = tag == "link" and namespace == _HTML

    if is_anchor:
        if any(key in attributes for key in (
            "ping", "download", "target", "formaction",
        )):
            raise NavigationAdmissionError("Navigation secondaire interdite.")
        if len(href_attrs) > 1:
            raise NavigationAdmissionError("Destinations ambiguës.")
        for attr_ns, href in href_attrs:
            if attr_ns not in ("", _XLINK) or not _FRAGMENT.fullmatch(href):
                raise NavigationAdmissionError("Navigation hors document.")
        return

    if is_stylesheet_link:
        rel = (attributes.get("rel") or "").lower().split()
        if set(rel) & _BANNED_REL:
            raise NavigationAdmissionError("Préchargement réseau interdit.")
        if any(attr_ns != "" for attr_ns, _ in href_attrs):
            raise NavigationAdmissionError("Destination de lien ambiguë.")
        if href_attrs and not (
            rel == ["stylesheet"]
            and href_attrs[0][1].lower().startswith("data:text/css,")
        ):
            raise NavigationAdmissionError("Lien head non autorisé.")
        return

    if href_attrs:
        # MathML global href, SVG use/image and unknown href-bearing tags.
        raise NavigationAdmissionError("Destination hors liste autorisée.")


def require_static_navigation(html: bytes) -> None:
    """Check the browser-shaped HTML5 DOM; refuse, never rewrite, any bytes.

    The preflight and HTML5 DOM validation are NOT a sanitizer, a complete
    network policy or proof of equivalence to Firefox. Only fictional input.
    """
    if type(html) is not bytes:
        raise NavigationAdmissionError("Octets HTML invalides.")
    try:
        text = html.decode("utf-8", errors="strict")
        _require_unambiguous_markup(text)
        parser = html5lib.HTMLParser(
            tree=html5lib.getTreeBuilder("etree"),
            namespaceHTMLElements=True,
        )
        root = parser.parse(text)
        # The HTML5 tokenizer resolves duplicate attributes by precedence.
        # Refuse them explicitly instead of relying on that precedence.
        if any(code == "duplicate-attribute"
               for _, code, _ in parser.errors):
            raise NavigationAdmissionError("Attribut HTML dupliqué.")
        for element in root.iter():
            _check_element(element)
    except (UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise NavigationAdmissionError("HTML non admis.") from exc
