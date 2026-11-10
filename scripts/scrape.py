"""Step 1a - polite, resumable scraper.

Usage: python -I scripts/scrape.py [--ids pilot_ids.txt] [--supplier "Fox Pharma"]

- Raw HTML -> cache/<supplier_slug>/<id>.html (never overwritten; existing ids skipped)
- Max 1 request/second per domain, retry with exponential backoff, robots.txt respected
- Falls back to Playwright when the static HTML has no usable product content
- Failures -> scrape_errors.csv (append; a later successful run supersedes them)
"""
import argparse
import csv
import os
import re
import sys
import time
import urllib.parse
import urllib.robotparser
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
ERRORS = ROOT / "scrape_errors.csv"
LOG = ROOT / "logs" / "scrape.log"
UA = "Mozilla/5.0 (compatible; product-catalogue-research/1.0)"
MIN_INTERVAL = 1.0  # seconds between requests to one domain
MAX_TRIES = 4


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def log(msg):
    LOG.parent.mkdir(exist_ok=True)
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class Polite:
    def __init__(self):
        self.last = {}
        self.robots = {}
        self.client = httpx.Client(
            headers={"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"},
            follow_redirects=True,
            timeout=30,
        )

    def wait(self, host):
        dt = time.time() - self.last.get(host, 0)
        if dt < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - dt)
        self.last[host] = time.time()

    def allowed(self, url):
        p = urllib.parse.urlparse(url)
        host = p.netloc
        if host not in self.robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                self.wait(host)
                r = self.client.get(f"{p.scheme}://{host}/robots.txt")
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except Exception as e:  # unreachable robots -> treat as allow-all, but log
                log(f"robots.txt unreachable for {host}: {e}")
                rp.parse([])
            self.robots[host] = rp
        return self.robots[host].can_fetch(UA, url)

    def get(self, url):
        host = urllib.parse.urlparse(url).netloc
        err = None
        for i in range(MAX_TRIES):
            self.wait(host)
            try:
                r = self.client.get(url)
                if r.status_code in (429, 500, 502, 503, 504):
                    err = f"HTTP {r.status_code}"
                else:
                    return r, None
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
            time.sleep(2 ** (i + 1))
        return None, err


def looks_empty(html):
    """Heuristic: static HTML lacks product content -> try a real browser."""
    low = html.lower()
    if len(html) < 3000:
        return True
    markers = ("product", "add to cart", "add to basket", "application/ld+json", "og:title")
    return not any(m in low for m in markers)


def render(url):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(user_agent=UA)
        pg.goto(url, wait_until="networkidle", timeout=60000)
        html = pg.content()
        b.close()
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    ap.add_argument("--supplier")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(ROOT / "products_input.csv", encoding="utf-8-sig")))
    if a.ids:
        want = {l.strip() for l in open(ROOT / a.ids) if l.strip()}
        rows = [r for r in rows if r["id"] in want]
    if a.supplier:
        rows = [r for r in rows if r["supplier"] == a.supplier]
    # interleave suppliers so the per-domain delay overlaps less with idle time
    rows.sort(key=lambda r: (r["supplier"], r["id"]))
    s = Polite()
    new_err = ERRORS.exists()
    ef = open(ERRORS, "a", newline="", encoding="utf-8")
    ew = csv.writer(ef)
    if not new_err:
        ew.writerow(["id", "supplier", "url", "error", "when"])
    done = skipped = failed = 0
    for r in rows:
        out = CACHE / slug(r["supplier"]) / f"{r['id']}.html"
        if out.exists():
            skipped += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        url = r["url"]
        if not s.allowed(url):
            ew.writerow([r["id"], r["supplier"], url, "disallowed by robots.txt", time.ctime()])
            failed += 1
            log(f"ROBOTS {r['id']} {url}")
            continue
        resp, err = s.get(url)
        if resp is None or resp.status_code >= 400:
            err = err or f"HTTP {resp.status_code}"
            ew.writerow([r["id"], r["supplier"], url, err, time.ctime()])
            ef.flush()
            failed += 1
            log(f"FAIL {r['id']} {err} {url}")
            continue
        html = resp.text
        method = "httpx"
        if looks_empty(html):
            try:
                html = render(url)
                method = "playwright"
            except Exception as e:
                log(f"playwright failed {r['id']}: {e}")
        meta = f"<!-- scraped-url: {url} | final-url: {resp.url} | method: {method} | {time.ctime()} -->\n"
        tmp = out.with_suffix(".tmp")
        tmp.write_text(meta + html, encoding="utf-8")
        os.replace(tmp, out)
        done += 1
        log(f"OK {r['id']} {method} {len(html)}B {r['supplier']}")
    ef.close()
    log(f"scrape finished: new={done} skipped(cached)={skipped} failed={failed}")


if __name__ == "__main__":
    sys.exit(main())
