"""Public completeness check: for each supplier, read robots.txt -> sitemaps -> product URLs, and compare with our input list.
Polite: honest user agent, robots.txt respected, 1 request/second per host, no login. Skips hosts in SKIP.
Usage: python -I scripts/sitemap_survey.py  -> output/supplier_coverage.csv + data/sitemaps/<supplier>.txt"""
import collections, csv, gzip, re, sys, time, urllib.parse, urllib.robotparser
from pathlib import Path
import httpx
ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; product-catalogue-research/1.0)"
SKIP = {"refinepharma.com"}  # access to this host needs the owner's permission rule (blocked in this session)
PRODUCT = re.compile(r"/(product|products|shop|p|item)s?/[^/?#]+/?$|/products/view/\d+|/product/\d+|\.html$", re.I)
last = {}
c = httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=40)

def get(url):
    host = urllib.parse.urlparse(url).netloc
    dt = time.time() - last.get(host, 0)
    if dt < 1: time.sleep(1 - dt)
    last[host] = time.time()
    url = url.replace("&amp;", "&").replace("http://", "https://", 1)
    r = c.get(url)
    if r.status_code == 429: time.sleep(8); r = c.get(url)
    r.raise_for_status()
    b = r.content
    if url.endswith(".gz") or b[:2] == b"\x1f\x8b": b = gzip.decompress(b)
    return b.decode("utf-8", "ignore")

def main():
    rows = list(csv.DictReader(open(ROOT / "products_input.csv", encoding="utf-8-sig")))
    by = collections.defaultdict(list)
    for r in rows: by[r["supplier"]].append(r)
    out = []; (ROOT / "data/sitemaps").mkdir(parents=True, exist_ok=True)
    for sup, rs in sorted(by.items()):
        host = collections.Counter(urllib.parse.urlparse(r["url"]).netloc for r in rs).most_common(1)[0][0]
        base = f"https://{host}"
        rec = dict(supplier=sup, host=host, our_listings=len(rs), sitemap_products="", in_sitemap_not_ours="", ours_not_in_sitemap="", note="")
        if host in SKIP:
            rec["note"] = "skipped - needs owner permission"; out.append(rec); print(sup, rec["note"]); continue
        try:
            robots = get(base + "/robots.txt")
        except Exception as e:
            robots = ""; rec["note"] = f"robots.txt: {e.__class__.__name__}; "
        rp = urllib.robotparser.RobotFileParser(); rp.parse(robots.splitlines())
        maps = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots) + [base + "/sitemap.xml", base + "/sitemap_index.xml"]
        seen, urls, todo = set(), set(), list(dict.fromkeys(maps))
        while todo and len(seen) < 60:
            sm = todo.pop(0)
            if sm in seen: continue
            seen.add(sm)
            if robots and not rp.can_fetch(UA, sm): continue
            try: x = get(sm)
            except Exception: continue
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", x)
            if "<sitemapindex" in x:
                todo += [l for l in locs if re.search(r"product|commerce|item|catalog|shop", l, re.I) and not re.search(r"taxonom|categor|tag|blog|news|author|image|pages_", l, re.I)]
            else:
                urls |= {l.replace("&amp;", "&") for l in locs if PRODUCT.search(urllib.parse.urlparse(l).path)}
        norm = lambda u: urllib.parse.urlparse(u).path.rstrip("/").lower()
        ours = {norm(r["url"]) for r in rs}; theirs = {norm(u) for u in urls}
        (ROOT / f"data/sitemaps/{re.sub(r'[^a-z0-9]+', '_', sup.lower())}.txt").write_text("\n".join(sorted(urls)))
        rec.update(sitemap_products=len(theirs), in_sitemap_not_ours=len(theirs - ours) if theirs else "", ours_not_in_sitemap=len(ours - theirs) if theirs else "",
                   note=rec["note"] + (f"{len(seen)} sitemap files read" if theirs else "no product sitemap found"))
        out.append(rec); print(sup, rec)
    with open(ROOT / "output/supplier_coverage.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

if __name__ == "__main__": main()
