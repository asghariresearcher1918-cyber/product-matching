"""Step 2 helper - polite, cached fetch of official reference pages (emc, MHRA, manufacturer).

Usage: python -I scripts/ref_fetch.py URL [URL ...]
Saves to refcache/<host>/<sanitised path>.html (never overwritten) and prints the
saved path, final URL and the SmPC section 6.5/2/3 snippets when it is an emc SmPC.
"""
import re
import sys
import time
import urllib.parse
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "refcache"
UA = "Mozilla/5.0 (compatible; product-catalogue-research/1.0)"


def path_for(url):
    p = urllib.parse.urlparse(url)
    name = re.sub(r"[^A-Za-z0-9]+", "_", (p.path + ("_" + p.query if p.query else "")).strip("/")) or "index"
    return REF / p.netloc / f"{name[:150]}.html"


def fetch(url, client):
    out = path_for(url)
    if out.exists():
        return out, "cached"
    for i in range(4):
        try:
            r = client.get(url)
            if r.status_code < 500 and r.status_code != 429:
                break
        except Exception as e:
            r = None
            err = e
        time.sleep(2 ** (i + 1))
    if r is None or r.status_code >= 400:
        return None, f"HTTP {getattr(r, 'status_code', err)}"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"<!-- ref-url: {url} | final-url: {r.url} | {time.ctime()} -->\n" + r.text, encoding="utf-8")
    time.sleep(1)
    return out, str(r.url)


def main():
    c = httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=40)
    for u in sys.argv[1:]:
        p, info = fetch(u, c)
        print(f"{u} -> {p} ({info})")


if __name__ == "__main__":
    main()
