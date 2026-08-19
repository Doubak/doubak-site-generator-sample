#!/usr/bin/env python3
"""Post-process the generated sitemap for this site.

generate-sitemap produces a correct sitemap for the common case, but this site
needs two adjustments it cannot express through the action's own inputs:

1. Drop paginator redirect stubs. The site generator emits a "page 1" alias
   next to every paginated listing (`/book/page/1.html`, `/tags/科幻/page/1/`,
   ...). Those files are not pages: each is a two-line stub with a
   `<meta http-equiv="refresh">` and a canonical link back to the real
   listing. Sitemaps are meant to carry canonical URLs, so ~700 redirects here
   only spend crawl budget and fill Search Console with "Page with redirect".
   generate-sitemap can exclude by path prefix only, and these stubs live
   under 700-odd separate tag directories, so they are filtered out here.

2. Percent-encode non-ASCII paths. Roughly 600 tag pages are named in Chinese,
   Japanese, or accented Latin (`/tags/一战.html`, `/tags/pokémon.html`).
   generate-sitemap writes those code points raw, but the sitemap protocol
   requires RFC 3986 escaping. The escaped form addresses exactly the same
   file, and validators stop complaining.

Usage: fix_sitemap.py <path-to-sitemap>
"""

import os
import re
import sys
import tempfile
from urllib.parse import quote
from xml.sax.saxutils import unescape

# `/page/1.html` is the stub itself; `/page/1/` is what an `index.html` stub
# becomes once generate-sitemap rewrites it to a directory URL. The anchor
# keeps real pages such as `/broadcast/page/10/` out of the match.
STUB = re.compile(r"/page/1(?:\.html|/)$")

URL_BLOCK = re.compile(r"<url>\s*<loc>(.*?)</loc>.*?</url>\s*", re.DOTALL)

# Every character RFC 3986 allows in a path, minus the five XML markup
# characters and `%`.
#
# Dropping the markup characters means anything that would need XML escaping
# gets percent-encoded instead, so the result is safe to drop straight back
# into the document without re-escaping.
#
# Dropping `%` means a literal percent in a filename becomes `%25`, which is
# what it must be. That is only correct because generate-sitemap writes
# filenames verbatim and never percent-encodes anything itself, so nothing
# reaching this script is already encoded. It does mean the script is not
# idempotent: it runs once, on freshly generated output.
PATH_SAFE = "/-._~!$()*+,;=:@"

# Scheme and authority of a <loc>. Everything after it is the path, including
# any `?` or `#`, which in a static file archive are characters in a filename
# rather than query or fragment delimiters — and so must be encoded, not
# treated as structure.
ORIGIN = re.compile(r"[a-z][a-z0-9+.-]*://[^/]*", re.I)

# generate-sitemap XML-escapes filenames on the way in, so undo that before
# percent-encoding. saxutils handles exactly the five XML entities (and does
# `&amp;` last, so a filename containing the literal text "&amp;" survives).
XML_ENTITIES = {"&apos;": "'", "&quot;": '"'}


def encode(url):
    """Percent-encode everything after the host of an XML-escaped <loc>."""
    url = unescape(url, XML_ENTITIES)
    origin = ORIGIN.match(url)
    if origin is None:
        return url
    return origin.group(0) + quote(url[origin.end():], safe=PATH_SAFE)


def write_atomically(path, content):
    """Replace `path` with `content` without opening `path` for writing.

    generate-sitemap is a Docker action and its container runs as root, so the
    sitemap it leaves in the workspace is owned by root:root while every later
    step runs as the unprivileged `runner` user. Opening that file "w" fails
    with EACCES. Writing a sibling file and renaming over it needs permission
    on the *directory* instead, which the runner has — and it makes the
    replacement atomic, so a crash mid-write cannot leave a truncated sitemap.
    """
    directory = os.path.dirname(os.path.abspath(path))
    tmp = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=directory,
        prefix=".sitemap-", suffix=".tmp", delete=False)
    try:
        with tmp:
            tmp.write(content)
        # NamedTemporaryFile creates with 0600; the sitemap is a public file
        # served to crawlers, so give it the mode the generator would have.
        os.chmod(tmp.name, 0o644)
        os.replace(tmp.name, path)
    except BaseException:
        os.unlink(tmp.name)
        raise


def main(path):
    with open(path, encoding="utf-8") as f:
        sitemap = f.read()

    dropped = 0
    encoded = 0

    def rewrite(match):
        nonlocal dropped, encoded
        loc = match.group(1)
        if STUB.search(loc):
            dropped += 1
            return ""
        fixed = encode(loc)
        if fixed == loc:
            return match.group(0)
        encoded += 1
        return match.group(0).replace(f"<loc>{loc}</loc>", f"<loc>{fixed}</loc>", 1)

    fixed_sitemap, seen = URL_BLOCK.subn(rewrite, sitemap)

    if seen == 0:
        print(f"WARNING: no <url> entries found in {path}; leaving it as is.")
        return 0

    write_atomically(path, fixed_sitemap)

    print(
        f"Dropped {dropped} paginator redirect stubs, "
        f"percent-encoded {encoded} URLs, "
        f"{seen - dropped} URLs remain."
    )
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
