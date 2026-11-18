"""Add products that suppliers list in their public sitemaps but our input list lacks -> data/products_added.csv
New ids A00001... (the owner file already uses R and N); title = readable slug until the page is scraped (extract/categorise use the page title). Idempotent.
Usage: python -I scripts/add_from_sitemaps.py"""
import csv, re, urllib.parse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from inputs import load_rows
SKIP = re.compile(r"/test-product|/sample|/gift-?card|/blog[/-]|/news/|/article", re.I)
norm = lambda u: urllib.parse.urlparse(u).path.rstrip("/").lower()

def main():
    rows = load_rows()
    have = {(r["supplier"], norm(r["url"])) for r in rows}
    sups = {re.sub(r"[^a-z0-9]+", "_", r["supplier"].lower()): r["supplier"] for r in rows}
    p = ROOT / "data/products_added.csv"
    old = list(csv.DictReader(open(p, encoding="utf-8"))) if p.exists() else []
    n = max([int(r["id"][1:]) for r in old] or [0])
    new = []
    for f in sorted((ROOT / "data/sitemaps").glob("*.txt")):
        sup = sups.get(f.stem)
        if not sup: continue
        for u in [u for u in f.read_text().split("\n") if u]:
            if (sup, norm(u)) in have or SKIP.search(u): continue
            have.add((sup, norm(u))); n += 1
            slug = urllib.parse.unquote(urllib.parse.urlparse(u).path.rstrip("/").split("/")[-1]).replace(".html", "")
            new.append(dict(id=f"A{n:05d}", supplier=sup, title=re.sub(r"[-_]+", " ", slug), url=u, source="supplier public catalogue (sitemap / shop listing)"))
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "supplier", "title", "url", "source"]); w.writeheader(); w.writerows(old + new)
    import collections
    print(len(new), "added", collections.Counter(r["supplier"] for r in new))

if __name__ == "__main__": main()
