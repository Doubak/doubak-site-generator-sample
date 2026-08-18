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

Usage: fix-sitemap.py <path-to-sitemap>
"""

import html
import re
import sys
from urllib.parse import quote, urlsplit, urlunsplit

# `/page/1.html` is the stub itself; `/page/1/` is what an `index.html` stub
# becomes once generate-sitemap rewrites it to a directory URL. The anchor
# keeps real pages such as `/broadcast/page/10/` out of the match.
STUB = re.compile(r"/page/1(?:\.html|/)$")

URL_BLOCK = re.compile(r"<url>\s*<loc>(.*?)</loc>.*?</url>\s*", re.DOTALL)

# Every character RFC 3986 allows in a path, minus the five XML markup
# characters. Leaving those to be percent-encoded means the result never needs
# XML escaping on the way back into the document.
PATH_SAFE = "/-._~!$()*+,;=:@"


def encode(url):
    """Percent-encode the path of an already XML-escaped URL."""
    parts = urlsplit(html.unescape(url))
    return urlunsplit(parts._replace(path=quote(parts.path, safe=PATH_SAFE)))


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

    with open(path, "w", encoding="utf-8") as f:
        f.write(fixed_sitemap)

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
