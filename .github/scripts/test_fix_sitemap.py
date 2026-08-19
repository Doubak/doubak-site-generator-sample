#!/usr/bin/env python3
"""Tests for fix_sitemap.py.

Stdlib only, no dependencies to install:

    python3 .github/scripts/test_fix_sitemap.py
"""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fix_sitemap

BASE = "https://sample.doubak.com/"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def sitemap(*locs):
    body = "\n".join(
        f"<url>\n<loc>{loc}</loc>\n<lastmod>2026-08-15T09:12:18+10:00</lastmod>\n</url>"
        for loc in locs
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n"
    )


class TestStub(unittest.TestCase):
    """The paginator-stub matcher."""

    def test_matches_the_page_1_aliases(self):
        # Both shapes the generator emits: a bare file, and a directory index
        # that generate-sitemap has already rewritten to a trailing slash.
        for path in ("/book/page/1.html", "/tags/科幻/page/1/"):
            with self.subTest(path=path):
                self.assertIsNotNone(fix_sitemap.STUB.search(BASE + path))

    def test_leaves_real_pages_alone(self):
        # The regression this anchor exists for: page 1x is a real page, and
        # an unanchored match would silently eat 10-19, 100-199, ...
        for path in (
            "/broadcast/page/10/",
            "/broadcast/page/11.html",
            "/broadcast/page/152/",
            "/movie/page/2.html",
            "/page/1.html/deeper.html",
        ):
            with self.subTest(path=path):
                self.assertIsNone(fix_sitemap.STUB.search(BASE + path))


class TestEncode(unittest.TestCase):
    """Percent-encoding of a single <loc>."""

    def assertEncodes(self, filename, expected):
        self.assertEqual(fix_sitemap.encode(BASE + filename), BASE + expected)

    def test_leaves_already_safe_urls_untouched(self):
        for path in ("", "search.html", "movie/10001418.html", "book/page/2/"):
            with self.subTest(path=path):
                self.assertEncodes(path, path)

    def test_encodes_non_ascii(self):
        self.assertEncodes("tags/一战.html", "tags/%E4%B8%80%E6%88%98.html")
        self.assertEncodes("tags/pok%C3%A9mon.html".replace("%C3%A9", "é"),
                           "tags/pok%C3%A9mon.html")

    def test_keeps_plus_literal(self):
        # `+` is legal in a path and means a plus, not a space. Three real tag
        # pages rely on this.
        self.assertEncodes("tags/a+b.html", "tags/a+b.html")

    def test_encodes_xml_escaped_characters(self):
        # generate-sitemap writes `AT&T.html` as `AT&amp;T.html`; unescaping
        # must happen before encoding, and the result must not reintroduce a
        # bare `&` into the document.
        self.assertEncodes("tags/AT&amp;T.html", "tags/AT%26T.html")
        self.assertEncodes("tags/it&apos;s.html", "tags/it%27s.html")
        self.assertEncodes("tags/a&quot;b.html", "tags/a%22b.html")
        self.assertEncodes("tags/&lt;x&gt;.html", "tags/%3Cx%3E.html")

    def test_unescapes_ampersand_last(self):
        # A file whose name literally contains the text "&amp;" is written
        # doubly escaped. One unescape pass must yield the literal text back.
        # `;` stays literal because it is a legal path sub-delimiter, and that
        # is harmless: `&` is encoded, so no entity can form out of `amp;`.
        self.assertEncodes("tags/x&amp;amp;y.html", "tags/x%26amp;y.html")
        self.assertEqual(
            unquote(fix_sitemap.encode(BASE + "tags/x&amp;amp;y.html")[len(BASE):]),
            "tags/x&amp;y.html")

    def test_treats_question_mark_and_hash_as_filename_characters(self):
        # Regression: urlsplit read these as query/fragment delimiters and
        # truncated the path, leaving the tail unencoded.
        self.assertEncodes("tags/what?.html", "tags/what%3F.html")
        self.assertEncodes("tags/no#1.html", "tags/no%231.html")

    def test_encodes_literal_percent(self):
        # generate-sitemap never percent-encodes, so a `%` here is always a
        # literal character in a filename and has to become %25.
        self.assertEncodes("tags/100%.html", "tags/100%25.html")
        self.assertEncodes("tags/pre%20encoded.html", "tags/pre%2520encoded.html")

    def test_output_is_xml_safe_without_further_escaping(self):
        for filename in ("tags/AT&amp;T.html", "tags/&lt;x&gt;.html",
                         "tags/it&apos;s.html", "tags/一战.html"):
            with self.subTest(filename=filename):
                encoded = fix_sitemap.encode(BASE + filename)
                self.assertFalse(set(encoded) & set("&<>\"'"), encoded)

    def test_passes_through_anything_that_is_not_a_url(self):
        self.assertEqual(fix_sitemap.encode("not a url"), "not a url")

    def test_does_not_touch_the_host(self):
        self.assertTrue(
            fix_sitemap.encode(BASE + "tags/一战.html").startswith(BASE))


class TestRoundTrip(unittest.TestCase):
    """The invariant that matters: every URL must lead back to its file."""

    def test_encoded_path_decodes_to_the_original_filename(self):
        for filename in (
            "tags/一战.html", "tags/pokémon.html", "tags/a+b.html",
            "tags/100%.html", "tags/pre%20encoded.html", "tags/what?.html",
            "tags/no#1.html", "movie/10001418.html", "book/page/2/",
        ):
            with self.subTest(filename=filename):
                encoded = fix_sitemap.encode(BASE + filename)
                self.assertEqual(unquote(encoded[len(BASE):]), filename)

    def test_round_trip_survives_xml_escaping(self):
        for escaped, literal in (
            ("tags/AT&amp;T.html", "tags/AT&T.html"),
            ("tags/it&apos;s.html", "tags/it's.html"),
        ):
            with self.subTest(escaped=escaped):
                encoded = fix_sitemap.encode(BASE + escaped)
                self.assertEqual(unquote(encoded[len(BASE):]), literal)


class TestMain(unittest.TestCase):
    """End to end, over a whole sitemap file."""

    def run_on(self, content):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sitemap.xml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            # main() reports what it did on stdout; keep it out of test output.
            with contextlib.redirect_stdout(io.StringIO()):
                fix_sitemap.main(path)
            with open(path, encoding="utf-8") as f:
                return f.read()

    def locs(self, content):
        root = ET.fromstring(content)
        return [u.find(NS + "loc").text for u in root.findall(NS + "url")]

    def test_drops_stubs_and_encodes_the_rest(self):
        out = self.run_on(sitemap(
            BASE,
            BASE + "book/page/1/",
            BASE + "book/page/2/",
            BASE + "tags/一战.html",
            BASE + "broadcast/page/10.html",
        ))
        self.assertEqual(self.locs(out), [
            BASE,
            BASE + "book/page/2/",
            BASE + "tags/%E4%B8%80%E6%88%98.html",
            BASE + "broadcast/page/10.html",
        ])

    def test_output_stays_well_formed_and_keeps_lastmod(self):
        out = self.run_on(sitemap(BASE + "tags/AT&amp;T.html"))
        root = ET.fromstring(out)
        url = root.findall(NS + "url")
        self.assertEqual(len(url), 1)
        self.assertEqual(url[0].find(NS + "lastmod").text,
                         "2026-08-15T09:12:18+10:00")

    def test_leaves_a_sitemap_with_no_entries_alone(self):
        empty = sitemap()
        self.assertEqual(self.run_on(empty), empty)

    def test_is_idempotent_for_urls_needing_no_change(self):
        once = self.run_on(sitemap(BASE, BASE + "movie/10001418.html"))
        self.assertEqual(self.run_on(once), once)


class TestCommandLine(unittest.TestCase):

    def test_rejects_a_missing_argument(self):
        result = subprocess.run(
            [sys.executable, fix_sitemap.__file__],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
