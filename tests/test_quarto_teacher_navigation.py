# SPDX-License-Identifier: AGPL-3.0-or-later
"""P3.6E: synthetic navigation admission tests (never real teacher data)."""
from __future__ import annotations

import unittest
from quarto_teacher_navigation import NavigationAdmissionError, require_static_navigation


class StaticNavigationAdmissionTests(unittest.TestCase):
    def test_allows_only_same_document_fragments_and_embedded_quarto_css(self):
        cases = [
            b'<!doctype html><title>Fiction</title><p>Static text</p>',
            b'<a href="#partie-1">Vers le titre</a><h2 id="partie-1">Titre</h2>',
            b'<a href="#">Haut</a><a>Sans lien</a>',
            b'<link rel="stylesheet" href="data:text/css,%0Ah2%7Bcolor:red%7D">',
            b'<style>h1{color:red}</style><img src="data:image/png;base64,AAAA">',
            b'<a href="&#35;chapter">Fragment encod\xc3\xa9</a>',
        ]
        for content in cases:
            with self.subTest(html=content[:55]):
                self.assertIsNone(require_static_navigation(content))

    def test_rejects_external_or_ambiguous_navigation(self):
        cases = [
            b'<a href="https://example.invalid/collect?data=fiction">External</a>',
            b'<a href="http://127.0.0.1:8888/other">Other local port</a>',
            b'<a href="//example.invalid/">Protocol-relative</a>',
            b'<a href="/another-page">Absolute path</a>',
            b'<a href="other.html">Relative page</a>',
            b'<a href="javascript:alert(1)">Script</a>',
            b'<a href="data:text/html,fiction">Data-navigation</a>',
            b'<a href="#fragment" target="_blank">New window</a>',
            b'<a href="#fragment" ping="https://example.invalid/log">Ping</a>',
            b'<a href="#frag" download>Download</a>',
            b'<a href="#frag" href="https://example.invalid/">Duplicate attr</a>',
            b'<area xlink:href="https://example.invalid/">SVG map</area>',
            b'<svg><a href="#safe" xlink:href="https://example.invalid/">X</a></svg>',
            b'<svg><a href="#safe" xlink:href="#other">Ambiguous</a></svg>',
            b'<meta http-equiv="refresh" content="0;url=https://example.invalid/">',
            b'<META HTTP-EQUIV="ReFrEsH" CONTENT="0; URL=//example.invalid/">',
            b'<base href="https://example.invalid/">',
            b'<form action="https://example.invalid/"><input></form>',
            b'<button formaction="https://example.invalid/">Go</button>',
            b'<iframe src="https://example.invalid/">',
            b'<frame src="https://example.invalid/">',
            b'<object data="https://example.invalid/">',
            b'<embed src="https://example.invalid/">',
            b'<link rel="preconnect" href="https://example.invalid/">',
            b'<link rel="dns-prefetch" href="//example.invalid">',
            b'<link rel="preload" href="https://example.invalid/file">',
            b'<link rel="stylesheet" href="https://example.invalid/site.css">',
            b'<link rel="alternate" href="https://example.invalid/">',
            b'<a href="#allowed&#10;https://example.invalid/">newline injection</a>',
            b'<a href="">Self reload</a>',
        ]
        for html in cases:
            with self.subTest(html=html[:100]):
                with self.assertRaises(NavigationAdmissionError):
                    require_static_navigation(html)

    def test_rejects_non_utf8_and_non_bytes(self):
        for content in (b"\xff", "not bytes", bytearray(b"<html>")):
            with self.subTest(value=type(content).__name__):
                with self.assertRaises(NavigationAdmissionError):
                    require_static_navigation(content)


if __name__ == "__main__":
    unittest.main()
