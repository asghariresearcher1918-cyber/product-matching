"""Platform-independent structured-product reader. Most e-commerce platforms (Shopify, WooCommerce, Magento, many
custom builds) embed Schema.org JSON-LD 'Product' in the page HTML; reading THAT is far more reliable than parsing
each shop's visual layout or guessing og:image. One reader covers every pharmacy that emits it; the rest fall back
to microdata / og: meta, and truly JS-only (SPA) pages need rendering.

product_struct(pid) -> {name, images[], sku, brand, price, currency, availability, mpn, gtin, source} or {} .
Usage (module): from structured import product_struct"""
import glob, html as _html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _cached_html(pid):
    for pat in (f"cache/*/{pid}.rendered.html", f"cache/*/{pid}.html"):
        f = glob.glob(str(ROOT / pat))
        if f:
            return f[0]
    return None


def _iter_products(obj):
    """Yield every dict that looks like a Schema.org Product, walking @graph / arrays / nesting."""
    if isinstance(obj, list):
        for x in obj:
            yield from _iter_products(x)
    elif isinstance(obj, dict):
        t = obj.get("@type", "")
        t = " ".join(t) if isinstance(t, list) else str(t)
        if "Product" in t:
            yield obj
        for k in ("@graph", "mainEntity", "hasVariant", "isVariantOf"):
            if k in obj:
                yield from _iter_products(obj[k])


def _first(*vals):
    for v in vals:
        if v not in (None, "", [], {}):
            return v
    return ""


def _images(p):
    im = p.get("image")
    out = []
    if isinstance(im, str):
        out = [im]
    elif isinstance(im, list):
        out = [x.get("url") if isinstance(x, dict) else x for x in im]
    elif isinstance(im, dict):
        out = [im.get("url", "")]
    return [u for u in out if isinstance(u, str) and u.startswith("http")]


def _offer(p):
    o = p.get("offers")
    if isinstance(o, list):
        o = o[0] if o else {}
    if not isinstance(o, dict):
        return "", "", ""
    price = _first(o.get("price"), o.get("lowPrice"), (o.get("priceSpecification") or {}).get("price") if isinstance(o.get("priceSpecification"), dict) else "")
    avail = str(o.get("availability", "")).rsplit("/", 1)[-1]
    cur = o.get("priceCurrency", "")
    return str(price), cur, avail


def product_struct(pid):
    f = _cached_html(pid)
    if not f:
        return {}
    try:
        h = open(f, encoding="utf-8", errors="ignore").read()
    except Exception:
        return {}
    best = {}
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', h, re.I | re.S):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except Exception:
            try:
                data = json.loads(raw.replace("\n", " "))
            except Exception:
                continue
        for p in _iter_products(data):
            name = _first(p.get("name"))
            if not isinstance(name, str) or not name.strip():
                continue
            imgs = _images(p)
            price, cur, avail = _offer(p)
            brand = p.get("brand")
            brand = brand.get("name", "") if isinstance(brand, dict) else (brand or "")
            cand = {"name": _html.unescape(name.strip()), "images": imgs,
                    "sku": str(_first(p.get("sku"), p.get("mpn"))), "brand": str(brand),
                    "price": price, "currency": cur, "availability": avail,
                    "mpn": str(p.get("mpn", "")), "gtin": str(_first(p.get("gtin13"), p.get("gtin"), p.get("gtin12"))),
                    "source": "json-ld"}
            # prefer the richest product block (one that has an image and a price)
            score = (bool(cand["images"]), bool(cand["price"]), bool(cand["sku"]))
            if sum(score) > sum((bool(best.get("images")), bool(best.get("price")), bool(best.get("sku")))):
                best = cand
    return best


if __name__ == "__main__":
    import sys
    print(json.dumps(product_struct(sys.argv[1]), ensure_ascii=False, indent=1))
