"""Group 2: product URL lists from public shop pages for suppliers without a usable sitemap (no login, robots.txt respected,
honest user agent, 1 request/second per host). Writes data/sitemaps/<supplier>.txt (merged with what is there).
Usage: python -I scripts/crawl_listings.py [skin_on_you harpar_grace dr_adams_pharmacy medfx]"""
import json, re, sys, time, urllib.parse, urllib.robotparser
from pathlib import Path
import httpx
ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; product-catalogue-research/1.0)"
c = httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=40)
last, robots = {}, {}

def get(u):
    h = urllib.parse.urlparse(u).netloc
    if h not in robots:
        rp = urllib.robotparser.RobotFileParser()
        try: rp.parse(c.get(f"https://{h}/robots.txt").text.splitlines())
        except Exception: rp.parse([])
        robots[h] = rp
    if not robots[h].can_fetch(UA, u): raise PermissionError("robots.txt disallows " + u)
    dt = time.time() - last.get(h, 0)
    if dt < 1: time.sleep(1 - dt)
    last[h] = time.time()
    r = c.get(u)
    if r.status_code == 429: time.sleep(10); r = c.get(u)
    r.raise_for_status(); return r

def skin_on_you():
    x = get("https://skinonyou.com/product-sitemap.xml").text
    return {u for u in re.findall(r"<loc>\s*(?:<!\[CDATA\[)?([^<\s\]]+)", x) if "/shop/" in u and not u.rstrip("/").endswith("/shop")}

def harpar_grace():
    out, page = set(), 1
    while page < 40:
        d = get(f"https://harpargrace.com/products.json?limit=250&page={page}").json().get("products", [])
        if not d: break
        out |= {f"https://harpargrace.com/products/{p['handle']}" for p in d}; page += 1
    return out

def dr_adams_pharmacy():
    base = "https://www.dradamspharmacy.co.uk"
    t = get(base + "/products").text
    cats = {u for u in re.findall(r'href="(https://www\.dradamspharmacy\.co\.uk/products/[a-z0-9-]+)"', t) if "/view/" not in u}
    out = set(re.findall(r'href="(https://www\.dradamspharmacy\.co\.uk/products/view/\d+)"', t))
    for cu in sorted(cats):
        for page in range(1, 30):
            try: t = get(cu + (f"?page={page}" if page > 1 else "")).text
            except Exception: break
            found = set(re.findall(r'href="(https://www\.dradamspharmacy\.co\.uk/products/view/\d+)"', t))
            if not found - out and page > 1: break
            out |= found
    return out

def medfx():
    out = set()
    for sm in ("https://www.medfx.co.uk/commerce-Sitemap.xml", "https://www.medfx.co.uk/Sitemap.xml", "https://medfx.co.uk/commerce-Sitemap.xml"):
        try: x = get(sm).text
        except Exception as e: print("  medfx", sm, e.__class__.__name__); continue
        out |= {u for u in re.findall(r"<loc>\s*([^<\s]+)", x) if re.search(r"--[a-z0-9.-]+/?$", u)}
    return out

SITES = {"skin_on_you": skin_on_you, "harpar_grace": harpar_grace, "dr_adams_pharmacy": dr_adams_pharmacy, "medfx": medfx}

def main():
    for name in (sys.argv[1:] or SITES):
        try: urls = SITES[name]()
        except Exception as e: print(name, "FAILED", e.__class__.__name__, e); continue
        f = ROOT / f"data/sitemaps/{name}.txt"
        old = set(f.read_text().split("\n")) - {""} if f.exists() else set()
        f.write_text("\n".join(sorted(old | urls)))
        print(name, len(urls), "product URLs")

if __name__ == "__main__": main()
