"""Restore authoritative product titles (with the punctuation the scraper dropped: parentheses, colons, hyphens in
ranges, ®) from each listing's CACHED page og:title / h1, for EVERY category.

Safety gate: the cached title is used ONLY when it is the SAME product as our stored title — i.e. after removing all
punctuation, spaces and case ('loose' form) the two are equal (or our stored loose form is contained in the cached
one with only a little extra). This makes it impossible to swap in a different product's name; it only adds back
punctuation / correct casing. SKU-prefixed or generic cached titles that fail the gate are skipped.

Output: data/title_overrides.csv  (id,title,source)  — consumed by canonical_names.py (display name only; no codes
change). Usage: python -I scripts/build_title_overrides.py
"""
import csv, glob, os, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEEP = {r["id"] for r in csv.DictReader(open(ROOT / "data/title_overrides.csv", encoding="utf-8"))} \
    if (ROOT / "data/title_overrides.csv").exists() else set()

OG = re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', re.I)
H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
TITLE = re.compile(r"<title[^>]*>([^<]+)", re.I)


def cached_title(html):
    for rx in (OG, H1, TITLE):
        m = rx.search(html)
        if m:
            t = re.sub(r"<[^>]+>", " ", m.group(1))
            t = (t.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
                 .replace("&nbsp;", " ").replace("&pound;", "£"))
            return re.sub(r"\s+", " ", t).strip()
    return ""


def clean(t, shop):
    s = t
    s = re.sub(r"^\s*buy\s+(online\s+)?", "", s, flags=re.I)        # "Buy "/"Buy Online " prefix
    s = re.sub(r"^\s*\d{3,}\s*[:\-]\s*", "", s)                      # leading "610221 : " numeric SKU prefix
    s = re.sub(r"^\s*[A-Za-z]{2,5}\d{2,}\s*[:\-]\s*", "", s)        # leading "SBS105 : " alpha-num SKU prefix
    s = re.sub(r"\s*\((?:size|pack)\s*[:\-][^)]*\)\s*", " ", s, flags=re.I)  # "(Size - 1)" noise ANYWHERE
    s = re.sub(r"\s*\|\s*.*$", "", s)                                # trailing " | Shop …"
    if shop:                                                         # trailing " - Shop" / " – Shop"
        s = re.sub(r"\s*[\-–—]\s*" + re.escape(shop) + r"\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*[\-–—]\s*(church pharmacy|fox pharma|healthxchange|ask pharmacy)\s*$", "", s, flags=re.I)
    s = re.sub(r"\s*\((?:size|pack)\s*[:\-].*?\)\s*$", "", s, flags=re.I)   # trailing "(Size - 1)" noise
    s = re.sub(r"\s+", " ", s).strip()
    w = s.split()                                                   # drop a trailing category word that merely
    if len(w) >= 2 and w[-1].isalpha():                            # repeats one already present ("… Sachets Sachet")
        sing = lambda x: re.sub(r"s$", "", x.lower())
        if sing(w[-1]) in {sing(x) for x in w[:-1]}:
            s = " ".join(w[:-1])
    return s


def loose(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def main():
    cache = {os.path.basename(f)[:-5]: f for f in glob.glob(str(ROOT / "cache/*/*.html"))}
    rows, kept_manual = [], []
    seen = set()
    n_cand = n_use = 0
    for mp in sorted(glob.glob(str(ROOT / "catalogue/final/*_listing_map.csv"))):
        for r in csv.DictReader(open(mp, encoding="utf-8")):
            rid, stored, shop = r.get("id", ""), r.get("title", ""), r.get("supplier", "")
            if not rid or rid in seen:
                continue
            seen.add(rid)
            if rid in KEEP:            # a manually-curated override already exists -> keep it untouched
                continue
            f = cache.get(rid)
            if not f or not stored.strip():
                continue
            ct = clean(cached_title(open(f, encoding="utf-8", errors="ignore").read()), shop)
            if len(ct) < 5 or len(ct) > 170:
                continue
            # only touch SCRAPER-DAMAGED titles: ours is entirely lower-case (the signature of the punctuation/case
            # stripping). Titles that already carry capitals + punctuation (MedFX, Fox, Wimpole, …) are left alone.
            if stored != stored.lower() or not re.search(r"[a-z]", stored):
                continue
            n_cand += 1
            ls, lc = loose(stored), loose(ct)
            if not ls or not lc:
                continue
            # SAME product? loose-equal, or stored fully contained with only a little extra (a dropped word / unit)
            same = (ls == lc) or (ls in lc and len(lc) - len(ls) <= 12) or (lc in ls and len(ls) - len(lc) <= 4)
            if not same:
                continue
            # the cached form must actually ADD punctuation or proper casing (else there is nothing to restore)
            adds = bool(re.search(r"[()®™:+/]", ct) or re.search(r"\d-\d", ct) or ct.lower() != ct)
            if not adds:
                continue
            n_use += 1
            rows.append({"id": rid, "title": ct, "source": f"cache og:title ({shop})"})
    # merge with any existing manual overrides, then write
    existing = list(csv.DictReader(open(ROOT / "data/title_overrides.csv", encoding="utf-8"))) \
        if (ROOT / "data/title_overrides.csv").exists() else []
    allrows = existing + rows
    with open(ROOT / "data/title_overrides.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "title", "source"]); w.writeheader(); w.writerows(allrows)
    print(f"candidates with cache title: {n_cand}")
    print(f"NEW overrides added (same product + adds punctuation): {n_use}")
    print(f"total overrides in file (incl. {len(existing)} existing): {len(allrows)}")


if __name__ == "__main__":
    main()
