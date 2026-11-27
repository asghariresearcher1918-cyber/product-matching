"""Detect listings whose cached product page is actually a DIFFERENT product (the shop reused/redirected the URL),
by comparing the listing title against the page's own <title>. Zero overlap of meaningful words = likely a wrong
page, so everything read from it (image, pack, description) is wrong. Output: output/page_mismatch.csv.

Usage: python -I scripts/audit_page_mismatch.py"""
import csv, glob, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STOP = set("the a an of and or for with to in on at by from pack box set kit x ml mg g cm mm size new sterile "
           "non disposable medical uk pharmacy product products buy online ltd 1 2 3 4 5 10".split())


def words(s):
    return {w for w in re.findall(r"[a-z0-9]{3,}", (s or "").lower()) if w not in STOP}


def page_title(f):
    try:
        h = open(f, encoding="utf-8", errors="ignore").read(200000)
    except Exception:
        return ""
    m = re.search(r"<title[^>]*>([^<]+)</title>", h, re.I)
    t = m.group(1) if m else ""
    t = re.sub(r"\s*[|\-–—].*$", "", t)                 # drop the '… — Shop name' suffix
    return t.strip()


def rel(a, b):                                           # related if equal, or one is a >=4-char prefix of the other
    for x in a:
        for y in b:
            if x == y or (len(x) >= 4 and y.startswith(x)) or (len(y) >= 4 and x.startswith(y)):
                return True
    return False


def main():
    # the image URL we picked for each listing (og:image / first gallery image) — the most reliable product id on
    # a Shopify page is the image's own filename, which is what exposed the wrong 'hot cold pack' -> sani-cloth image.
    img = {}
    p = ROOT / "catalogue/final/listing_images.csv"
    if p.exists():
        for r in csv.DictReader(open(p, encoding="utf-8")):
            u = [x for x in (r.get("image_urls") or "").split("|") if x.startswith("http")]
            if u:
                img[r["id"]] = u[0]
    rows = []
    for mp in glob.glob(str(ROOT / "catalogue/final/*_listing_map.csv")):
        for r in csv.DictReader(open(mp, encoding="utf-8")):
            pid, title = r.get("id", ""), r.get("title", "")
            u = img.get(pid)
            if not pid or not title or not u or "/cdn/shop/" not in u:   # only judge Shopify image filenames
                continue
            fname = re.sub(r"[_-]\d{2,4}x\d{0,4}.*$", "", re.sub(r"\?.*$", "", u).rsplit("/", 1)[-1])
            iw = words(fname.replace("_", "-"))
            lw = words(title)
            if not lw or not iw:
                continue
            if not rel(lw, iw):                          # listing name shares no word with its own image's filename
                rows.append({"id": pid, "supplier": r.get("supplier", ""), "listing_title": title,
                             "image_filename": fname, "url": r.get("url", ""),
                             "map": Path(mp).stem.replace("_listing_map", "")})
    out = ROOT / "output/page_mismatch.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "supplier", "listing_title", "image_filename", "url", "map"])
        w.writeheader(); w.writerows(rows)
    print(f"wrote {out}: {len(rows)} suspected listing/page mismatches")
    from collections import Counter
    for sup, n in Counter(r["supplier"] for r in rows).most_common(12):
        print(f"  {n:4}  {sup}")


if __name__ == "__main__":
    main()
