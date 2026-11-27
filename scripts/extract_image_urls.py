"""Extract each catalogued listing's own product-image URLs from its cached page (no network, no download) so the
site can show images by referencing the pharmacy's CDN directly. For a reference product we use ONE listing's
own gallery (distinct angles, de-duplicated) rather than merging every supplier's near-duplicate photo.

Output: catalogue/final/listing_images.csv  (id, supplier, image_urls   # '|'-joined, de-duplicated, up to 4)
Usage: python -I scripts/extract_image_urls.py"""
import csv, glob, re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_images import _cached_html, SKIP_SUPPLIERS, _norm, _base, IMG_RE, MAX_IMAGES

ROOT = Path(__file__).resolve().parent.parent

_OG = re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', re.I)
_JSONLD = re.compile(r'"image"\s*:\s*\[?\s*"([^"]+)"')
_CDN = re.compile(r'(?:https?:)?\\?/\\?/[^\s"\'<>]+?/(?:cdn/shop/products|cdn/shop/files|wp-content/uploads)/[^\s"\'<>]+?\.(?:jpg|jpeg|png|webp)', re.I)


def image_urls_fast(html):
    """Regex-only image extraction (no BeautifulSoup) — ~10x faster for a URL-only pass over thousands of pages."""
    urls, seen = [], set()

    def add(u):
        if not u:
            return
        u = _norm(u)
        if not IMG_RE.search(re.sub(r"\?.*$", "", u)):
            return
        if re.search(r"/(logo|icon|sprite|payment|badge|flag|avatar|banner)", u, re.I):
            return
        # filename-based placeholders: a shop logo / coming-soon / no-image used in place of a product photo
        if re.search(r"(logo|placeholder|coming[-_]?soon|no[-_]?image|default[-_]?image|image[-_]?coming)", u.rsplit("/",1)[-1], re.I):
            return
        b = _base(u)
        if b in seen:
            return
        seen.add(b)
        urls.append(u)

    m = _OG.search(html)
    if m:
        add(m.group(1))
    for mm in _JSONLD.finditer(html):
        add(mm.group(1))
    for mm in _CDN.finditer(html):
        add(mm.group(0))
    return urls[:MAX_IMAGES]


def main():
    ids = {}
    for f in glob.glob(str(ROOT / "catalogue/final/*_listing_map.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r.get("id") and r["id"] not in ids:
                ids[r["id"]] = r.get("supplier", "")
    html_of = {}                                   # prebuild pid -> cached HTML path (one listing of each dir)
    for f in glob.glob(str(ROOT / "cache/*/*.html")):
        name = Path(f).name
        pid = name.split(".rendered.html")[0].split(".html")[0]
        html_of.setdefault(pid, f)
    rows, n_with = [], 0
    for pid, sup in ids.items():
        hf = html_of.get(pid)
        if not hf or Path(hf).parent.name in SKIP_SUPPLIERS:
            continue
        try:
            urls = image_urls_fast(open(hf, encoding="utf-8", errors="ignore").read())
        except Exception:
            urls = []
        if urls:
            n_with += 1
        rows.append({"id": pid, "supplier": sup, "image_urls": "|".join(urls)})
    out = ROOT / "catalogue/final/listing_images.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "supplier", "image_urls"])
        w.writeheader(); w.writerows(rows)
    print(f"wrote {out}: {len(rows)} listings, {n_with} with at least one image URL")


if __name__ == "__main__":
    main()
