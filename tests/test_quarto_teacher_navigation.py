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

    def test_auditor_counterexamples_mathml_href_and_svg_smil(self):
        # Two independent auditor blockers: namespace-agnostic URL-bearing
        # MathML and script-free SVG SMIL mutation of effective a.href.
        counterexamples = (
            b'<!doctype html><math href="https://example.invalid/fiction">'
            b'<mi>Cliquer</mi></math>',
            b'<math><mi href="/outside">Cliquer</mi></math>',
            b'<math><mi xlink:href="//example.invalid/">Lien</mi></math>',
            b'<svg width="200" height="50"><a href="#safe">'
            b'<set attributeName="href" to="/outside" begin="0s" '
            b'fill="freeze"/><text x="10" y="30">Cliquer</text></a></svg>',
            b'<svg><a href="#safe"><animate attributeName="href" '
            b'values="#safe;/outside" dur="0.05s" fill="freeze"/></a></svg>',
            b'<svg><a href="#safe"><animateTransform attributeName="transform" '
            b'type="rotate" from="0" to="90" dur="1s"/></a></svg>',
            b'<svg><a href="#safe"><animateMotion dur="1s"/></a></svg>',
            b'<svg><a href="#safe"><set attributeName="href" '
            b'to="https://example.invalid/fiction"/></a></svg>',
            b'<svg><use href="#safe"/></svg>',
            b'<svg><image xlink:href="#safe"/></svg>',
            b'<div href="#safe">Unrecognized href-bearing element</div>',
            b'<link rel="stylesheet" href="data:text/css,%0A" '
            b'xlink:href="https://example.invalid/">',
        )
        for html in counterexamples:
            with self.subTest(html=html[:125]):
                with self.assertRaises(NavigationAdmissionError):
                    require_static_navigation(html)

    def test_auditor_html5_markup_recovery_counterexamples(self):
        # Python HTMLParser can swallow an entire suffix as an unterminated
        # comment while the browser HTML5 tokenizer creates active nodes.
        # Reject the syntax family before relying on parser callbacks.
        fixtures = (
            b'<!doctype html><!----!><math href="https://example.invalid/fiction">'
            b'<mi>Cliquer</mi></math><!---->',
            b'<!doctype html><!----!><svg><a href="#safe">'
            b'<set attributeName="href" to="/outside" begin="0s" '
            b'fill="freeze"/></a></svg><!---->',
            b'<![CDATA[><math href="https://example.invalid/fiction">'
            b'<mi>Cliquer</mi></math>',
            b'<!-- benign-looking comment --><a href="#chapter">safe</a>',
            b'<!DOCTYPE html><!ENTITY x SYSTEM "https://example.invalid/">',
            b'<!doctype html><?fiction external?>',
            b'<!doctype html><!doctype html><a href="#safe">safe</a>',
            b'<!doctype html><!-- unclosed comment',
        )
        for html in fixtures:
            with self.subTest(prefix=html[:95]):
                with self.assertRaises(NavigationAdmissionError):
                    require_static_navigation(html)

    def test_exact_html_doctype_and_safe_fragment_remain_accepted(self):
        safe = (
            b'<!DOCTYPE html>\n<html lang="fr"><head>'
            b'<meta charset="utf-8"><title>Fiction</title></head>'
            b'<body><a href="#target">interne</a><h1 id="target">Titre</h1>'
            b'<link rel="stylesheet" href="data:text/css,body%7Bcolor:black%7D">'
            b'</body></html>'
        )
        self.assertIsNone(require_static_navigation(safe))

    def test_rejects_non_utf8_and_non_bytes(self):
        for content in (b"\xff", "not bytes", bytearray(b"<html>")):
            with self.subTest(value=type(content).__name__):
                with self.assertRaises(NavigationAdmissionError):
                    require_static_navigation(content)


if __name__ == "__main__":
    unittest.main()
