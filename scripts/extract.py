"""Step 1b - extract structured fields from cached HTML -> pages.jsonl

One extractor per platform (WooCommerce, Shopify, JSON-LD/custom), plus a generic
fallback. Re-runnable: always rebuilds pages.jsonl from cache (cache is read-only here).
Pages whose cache shows a redirect away from the product (e.g. to a listing page) are
written to scrape_errors.csv instead of being guessed.

Usage: python -I scripts/extract.py [--ids pilot_ids.txt]
"""
import argparse
import csv
import html as htmllib
import json
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def clean(t):
    return re.sub(r"\s+", " ", htmllib.unescape(t or "")).strip()


def text_of(el):
    return clean(el.get_text(" ", strip=True)) if el else ""


def jsonld_products(soup):
    out = []
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            d = json.loads(sc.string or sc.get_text() or "")
        except Exception:
            continue
        stack = d if isinstance(d, list) else [d]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                t = x.get("@type")
                if t == "Product" or (isinstance(t, list) and "Product" in t):
                    out.append(x)
                for k in ("@graph", "mainEntity", "itemListElement"):
                    if isinstance(x.get(k), list):
                        stack.extend(x[k])
                    elif isinstance(x.get(k), dict):
                        stack.append(x[k])
            elif isinstance(x, list):
                stack.extend(x)
    return out


def jsonld_breadcrumb(soup):
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            d = json.loads(sc.string or "")
        except Exception:
            continue
        items = d.get("@graph", [d]) if isinstance(d, dict) else d
        for x in items:
            if isinstance(x, dict) and x.get("@type") == "BreadcrumbList":
                names = []
                for it in x.get("itemListElement", []):
                    n = it.get("name") or (it.get("item") or {}).get("name") if isinstance(it.get("item"), dict) else it.get("name")
                    if n:
                        names.append(clean(n))
                return " > ".join(names)
    return ""


def meta(soup, prop):
    m = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
    return clean(m.get("content")) if m and m.get("content") else ""


def detect_platform(raw):
    low = raw[:400000].lower()
    if "cdn.shopify.com" in low or "shopify.theme" in low:
        return "shopify"
    if "woocommerce" in low:
        return "woocommerce"
    return "custom"


# ---------------- platform extractors ----------------

def ex_woocommerce(soup, raw):
    r = {}
    h1s = [text_of(h) for h in soup.select("h1.product_title, h1.entry-title, h1")]
    h1s = [h for h in h1s if h and h.lower() not in ("shop", "products")]
    r["page_title"] = h1s[0] if h1s else ""
    r["short_description"] = text_of(soup.select_one(".woocommerce-product-details__short-description"))
    r["description"] = text_of(
        soup.select_one("#tab-description, .woocommerce-Tabs-panel--description, .product-description, .elementor-widget-woocommerce-product-content, .pd-desc-full, .pd-desc-preview, [data-tab=description] .wysiwyg")
    )
    for tr in soup.select(".pd-specs-table tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) >= 2:
            r.setdefault("_specs", {})[text_of(cells[0])] = text_of(cells[1])
    attrs = {}
    for tr in soup.select("table.woocommerce-product-attributes tr, table.shop_attributes tr"):
        k, v = text_of(tr.find("th")), text_of(tr.find("td"))
        if k:
            attrs[k] = v
    attrs.update(r.pop("_specs", {}))
    r["attributes"] = attrs
    opts = {}
    for sel in soup.select("table.variations select, form.variations_form select"):
        name = sel.get("data-attribute_name") or sel.get("name") or "option"
        vals = [clean(o.get_text()) for o in sel.find_all("option") if o.get("value")]
        if vals:
            opts[name] = vals
    form = soup.select_one("form.variations_form")
    if form and form.get("data-product_variations") not in (None, "false"):
        try:
            vs = json.loads(htmllib.unescape(form["data-product_variations"]))
            opts["_variations"] = [
                {"attributes": v.get("attributes"), "sku": v.get("sku"), "in_stock": v.get("is_in_stock"),
                 "image": (v.get("image") or {}).get("src"), "description": clean(BeautifulSoup(v.get("variation_description") or "", "lxml").get_text(" "))}
                for v in vs
            ]
        except Exception:
            pass
    r["options"] = opts
    r["stock_text"] = text_of(soup.select_one("p.stock, .stock")) or meta(soup, "twitter:data2")
    r["breadcrumb"] = text_of(soup.select_one(".woocommerce-breadcrumb, nav.breadcrumb, .breadcrumbs"))
    img = soup.select_one(".woocommerce-product-gallery__image a, .woocommerce-product-gallery__image img")
    r["image_url"] = (img.get("href") or img.get("data-large_image") or img.get("src")) if img else ""
    r["categories"] = text_of(soup.select_one(".product_meta .posted_in"))
    r["sku"] = text_of(soup.select_one(".product_meta .sku"))
    return r


def ex_shopify(soup, raw):
    r = {}
    r["page_title"] = text_of(soup.select_one("h1"))
    r["description"] = text_of(soup.select_one(".product__description, .product-single__description, .rte, [itemprop=description]"))
    opts = {}
    m = re.search(r'<script[^>]+type="application/json"[^>]*data-product-json[^>]*>(.*?)</script>', raw, re.S)
    pj = None
    if m:
        try:
            pj = json.loads(m.group(1))
        except Exception:
            pj = None
    if pj is None:
        m = re.search(r"var meta = (\{.*?\});\s*\n", raw, re.S)
        if m:
            try:
                pj = json.loads(m.group(1)).get("product")
            except Exception:
                pj = None
    if pj and pj.get("variants"):
        opts["_variations"] = [
            {"title": v.get("title") or v.get("public_title") or v.get("name"), "sku": v.get("sku"),
             "in_stock": v.get("available")} for v in pj["variants"]
        ]
    for fs in soup.select("variant-radios fieldset, variant-selects .product-form__input, select[name^=options]"):
        lab = text_of(fs.find("legend") or fs.find("label")) or fs.get("name") or "option"
        vals = [clean(i.get("value")) for i in fs.select("input[type=radio], option") if i.get("value")]
        if vals:
            opts[lab] = vals
    r["options"] = opts
    r["attributes"] = {}
    r["stock_text"] = text_of(soup.select_one(".product-form__submit, .product__inventory, .sold-out"))
    r["breadcrumb"] = text_of(soup.select_one("nav.breadcrumb, .breadcrumbs"))
    r["image_url"] = meta(soup, "og:image")
    return r


def ex_custom(soup, raw):
    r = {}
    r["page_title"] = text_of(soup.select_one("h1"))
    # remove obvious chrome, keep main text
    for t in soup(["script", "style", "noscript", "header", "footer", "nav", "form[role=search]"]):
        t.decompose()
    main = soup.select_one("main, #main, .product, .product-details, .product-page, #content, .content") or soup.body
    d = text_of(main)
    m = END_MARKERS.search(d, min(len(r["page_title"]) + 5, len(d)))
    r["description"] = (d[: m.start()] if m else d)[:6000]
    r["attributes"] = {}
    opts = {}
    for sel in (main.select("select") if main else []):
        vals = [clean(o.get_text()) for o in sel.find_all("option") if clean(o.get_text())]
        name = sel.get("name") or sel.get("id") or "option"
        if vals and not re.search(r"qty|quantity|patient|country|sort", name, re.I):
            opts[name] = vals
    r["options"] = opts
    st = re.search(r"(out of stock|in stock|currently unavailable|available on request|discontinued)", r["description"], re.I)
    r["stock_text"] = st.group(1) if st else ""
    r["breadcrumb"] = ""
    img = soup.select_one("img.js-main-image, .product-image img, .product-gallery img")
    if img is None:  # Salesforce B2B (ACRE): product media served from /sfsites/c/cms/delivery/media
        img = next((i for i in soup.find_all("img") if "cms/delivery/media" in (i.get("src") or "") and "default-product-image" not in i.get("src", "")
                    and "logo" not in (i.get("alt") or "").lower()), None)
    src = (img.get("data-src") or img.get("src") or "") if img else ""
    r["image_url"] = "" if re.search(r"image-soon|placeholder|no-image", src, re.I) else src
    return r


END_MARKERS = re.compile(
    r"(You May Also ?Like|Related products|Customers also|Recently Viewed|Subscribe to our newsletter|Delivery Options|"
    r"Join our newsletter|Site Links|Your Cart Your cart is empty|We use cookies)", re.I)


def main_text(raw, title):
    soup = BeautifulSoup(raw, "lxml")
    for t in soup(["script", "style", "noscript", "header", "footer", "nav", "svg"]):
        t.decompose()
    for t in soup.select(".related, .upsells, .cross-sells, #mega-menu, .menu, .cart-drawer, .newsletter, .site-header, .site-footer"):
        t.decompose()
    txt = text_of(soup.body or soup)
    if title:
        key = title[:40].lower()
        positions = [m.start() for m in re.finditer(re.escape(key), txt.lower())]
        # last heading-like occurrence before the bulk of the product text
        if positions:
            txt = txt[positions[0]:]
    m = END_MARKERS.search(txt, min(len(title or "") + 5, len(txt)))
    if m:
        txt = txt[: m.start()]
    return txt[:8000]


def extract(raw):
    soup = BeautifulSoup(raw, "lxml")
    plat = detect_platform(raw)
    prods = jsonld_products(soup)
    bc = jsonld_breadcrumb(soup)
    og_img = meta(soup, "og:image")
    og_title = meta(soup, "og:title")
    title_tag = text_of(soup.find("title"))
    r = {"shopify": ex_shopify, "woocommerce": ex_woocommerce}.get(plat, ex_custom)(BeautifulSoup(raw, "lxml"), raw)
    r["platform"] = plat
    if prods:
        p = prods[0]
        r.setdefault("jsonld", {})
        r["jsonld"] = {k: p.get(k) for k in ("name", "sku", "description", "category") if p.get(k)}
        img = p.get("image")
        if isinstance(img, list):
            img = img[0] if img else ""
        if isinstance(img, dict):
            img = img.get("url", "")
        if not r.get("image_url") and img:
            r["image_url"] = img
        if not r.get("description") and p.get("description"):
            r["description"] = clean(BeautifulSoup(p["description"], "lxml").get_text(" "))
        offers = p.get("offers")
        if isinstance(offers, dict):
            offers = [offers]
        if isinstance(offers, list) and offers and not r.get("stock_text"):
            av = offers[0].get("availability", "")
            r["stock_text"] = av.rsplit("/", 1)[-1]
    if not r.get("breadcrumb"):
        r["breadcrumb"] = bc
    if not r.get("image_url"):
        r["image_url"] = og_img
    if not r.get("page_title"):
        r["page_title"] = og_title or title_tag
    r["main_text"] = main_text(raw, r["page_title"])
    r["og_title"] = og_title
    r["html_title"] = title_tag
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(ROOT / "products_input.csv", encoding="utf-8-sig")))
    if a.ids:
        want = {l.strip() for l in open(ROOT / a.ids) if l.strip()}
        rows = [r for r in rows if r["id"] in want]
    # existing error log: keep fetch errors, regenerate extraction errors
    errs = []
    ep = ROOT / "scrape_errors.csv"
    if ep.exists():
        errs = [e for e in csv.DictReader(open(ep, encoding="utf-8")) if not e["error"].startswith("extract:")]
    n = 0
    with open(ROOT / "pages.jsonl", "w", encoding="utf-8") as out:
        for row in rows:
            f = CACHE / slug(row["supplier"]) / f"{row['id']}.html"
            if not f.exists():
                continue
            rf = f.with_suffix(".rendered.html")  # JS-only sites (e.g. ACRE/Salesforce): browser-rendered copy
            if rf.exists():
                raw = rf.read_text(encoding="utf-8", errors="replace")
                raw = re.sub(r"^<!-- ref-url: (\S+) \| final-url: (\S+) \| rendered", r"<!-- scraped-url: \1 | final-url: \2 | method: playwright", raw, count=1)
            else:
                raw = f.read_text(encoding="utf-8", errors="replace")
            m = re.match(r"<!-- scraped-url: (\S+) \| final-url: (\S+) \| method: (\S+)", raw)
            final = m.group(2) if m else row["url"]
            if m and final.rstrip("/") != row["url"].rstrip("/") and re.search(r"/(all-products|shop|products|search|login|account)/?$|[?&]s=", final):
                errs.append({"id": row["id"], "supplier": row["supplier"], "url": row["url"],
                             "error": f"extract: redirected to listing page {final} (product removed or login-only)", "when": time.ctime()})
                continue
            rec = {"id": row["id"], "supplier": row["supplier"], "input_title": row["title"], "url": row["url"],
                   "final_url": final, "fetch_method": m.group(3) if m else ""}
            rec.update(extract(raw))
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    # dedupe errors: keep only ids not successfully extracted
    ok = {json.loads(l)["id"] for l in open(ROOT / "pages.jsonl", encoding="utf-8")}
    seen, final_errs = set(), []
    for e in errs:
        if e["id"] in ok or (e["id"], e["error"]) in seen:
            continue
        seen.add((e["id"], e["error"]))
        final_errs.append(e)
    with open(ep, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "supplier", "url", "error", "when"])
        w.writeheader()
        w.writerows(final_errs)
    print(f"pages.jsonl: {n} rows; scrape_errors.csv: {len(final_errs)} rows")


if __name__ == "__main__":
    main()
