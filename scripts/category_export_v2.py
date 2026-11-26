"""Comprehensive per-category workbook for the v2 taxonomy (one category at a time, smallest first).
Adds the owner-requested database columns: SKU / product code, Brand (or 'no brand'), Volume, Qty per pack,
Product link, real commercial code (if present), Prescription (Yes/No), and public Price (only when the page shows
one without login). Keeps the earlier tabs (Products, Listings per product, For your review, Name reference).
Usage: python -I scripts/category_export_v2.py "Botulinum Toxins"   (a v2 top-level label or a C## id)"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
try:
    from page_facts import page_text, labelled_fields
except Exception:
    def page_text(_i): return ""
    def labelled_fields(_t): return {}
from build_site_v2 import TOP, POM_TOP, top_of

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"
F = "Arial"
HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
LINK = Font(name=F, size=9, color="0563C1", underline="single")
SM, WRAP = Font(name=F, size=9), Alignment(wrap_text=True, vertical="top")

# listing-map file -> tag (uid = tag:code), so we can find each listing's page id + url for extraction
MAPS = [("toxin", "TOX"), ("filler", "FIL"), ("booster", "BST"), ("biostim", "BIO"), ("fat", "FAT"),
        ("thread", "THR"), ("weight", "WGT"), ("medicine", "MED"), ("skincare", "SKN"), ("needle", "NDL"),
        ("consumable", "CON"), ("device", "DEV"), ("bty", "BTY"), ("sup", "SUP"), ("vac", "VAC")]

_CODE = re.compile(r"\b(?:sku|product code|item code|quickfind(?: code)?|ref(?:erence)?(?: code| no)?|mpn|ean|barcode)\b\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9\-_/.]{2,24})", re.I)
_LOGIN = re.compile(r"log ?in to view|login to (?:view|see)|sign in to (?:view|see)|price on request|\bp\.?o\.?a\.?\b|request a quote|trade price", re.I)
_PRICE = re.compile(r"£\s?(\d{1,4}(?:\.\d{2})?)")


def listing_index():
    """uid -> [ {id,url,supplier,title,confidence} ]"""
    idx = collections.defaultdict(list)
    for stem, tag in MAPS:
        p = FINAL / f"{stem}_listing_map.csv"
        if not p.exists():
            continue
        for m in csv.DictReader(open(p, encoding="utf-8")):
            code = m.get("code", "")
            if not code:
                continue
            idx[f"{tag}:{code}"].append({"id": m.get("id", ""), "url": m.get("url", ""),
                                         "supplier": m.get("supplier", ""), "title": m.get("title", ""),
                                         "confidence": m.get("confidence", ""),
                                         "opt_price": m.get("opt_price", ""), "opt_sku": m.get("opt_sku", "")})
    return idx


_SKU_JUNK = {"price", "none", "view", "login", "call", "instock", "qty", "add", "yes", "no", "sale", "new", "stock"}
_GAUGE = re.compile(r"^\d{1,2}\s?g$", re.I)           # '30G' = needle gauge, not a SKU
_PENCE = re.compile(r"£\s?(\d{1,4}\.\d{2})\b")        # a real price almost always carries pence (£90.00, £126.50)
_THRESH = re.compile(r"(?:free|over|spend|orders?|delivery|shipping|p&p|postage)\s*£?\s?\d", re.I)


def _clean_codes(txt):
    out = []
    for c in _CODE.findall(txt):
        cl = c.lower().strip(".-_/")
        if cl in _SKU_JUNK or _GAUGE.match(c) or not re.search(r"\d", c) or len(re.sub(r"\D", "", c)) < 2:
            continue                                   # real code: has >=2 digits, not junk/gauge
        if c not in out:
            out.append(c)
    return out


def extract(pid):
    """(sku/code, commercial_code, public_price) from the product page; price only when genuinely public."""
    if not pid:
        return "", "", ""
    txt = page_text(pid)
    if not txt:
        return "", "", ""
    codes = _clean_codes(txt)
    sku = codes[0] if codes else ""
    comm = codes[1] if len(codes) > 1 else ""
    price = ""
    if not _LOGIN.search(txt):
        for m in _PENCE.finditer(txt):                 # only trust £ values with pence, and not a delivery threshold
            before = txt[max(0, m.start() - 24):m.start()]
            if float(m.group(1)) >= 1 and not _THRESH.search(before):
                price = "£" + m.group(1); break
    return sku, comm, price


def head(ws, cols, widths):
    ws.append(cols)
    for j, w in enumerate(widths, 1):
        c = ws.cell(row=1, column=j); c.font, c.fill, c.alignment = HF, HFILL, WRAP
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A2"


def vol_of(*texts):
    for t in texts:
        m = re.search(r"(\d+(?:\.\d+)?\s*(?:ml|mg|iu|units?|u\b|speywood))", t or "", re.I)
        if m:
            return m.group(1)
    return ""


def qty_of(name):
    """Pack quantity read from the product/title when the DB has no vials_per_pack (consumables etc.):
    'First Aid Kit 110 Piece' -> 110, '(125pcs)' -> 125, 'Pack of 50' -> 50, "10's" -> 10. Avoids blade/person numbers."""
    for rx in (r"pack of\s*(\d+)", r"box of\s*(\d+)", r"(\d+)\s*(?:pieces?|pcs|ct\b|count|pairs?|sheets?|wipes?|swabs?|rolls?|tabs?|tablets?|caps?|sachets?)\b",
               r"\b(\d+)\s*['’]s\b", r"(\d+)\s*pack\b", r"x\s*(\d+)\b"):
        m = re.search(rx, name or "", re.I)
        if m:
            n = int(m.group(1))
            if 2 <= n <= 10000:
                return str(n)
    return ""


def main():
    target = sys.argv[1]
    want = target if target.startswith("C") or target == "WLM" else next((k for k, (lbl, _ic) in TOP.items() if lbl == target), None)
    assert want, f"unknown category '{target}'"
    label = TOP[want][0]

    prods = {r["uid"]: r for r in csv.DictReader(open(FINAL / "master_catalogue.csv", encoding="utf-8"))}
    tax = {r["uid"]: r for r in csv.DictReader(open(FINAL / "taxonomy_v2.csv", encoding="utf-8"))
           if top_of(r["primary_category_id"]) == want}
    idx = listing_index()

    wb = Workbook()
    # ---------- Products ----------
    ps = wb.active; ps.title = "Products"
    head(ps, ["Product", "Taxonomy (primary › sub)", "Brand", "Volume", "Qty / pack", "Prescription",
              "Suppliers", "Listings", "Public price (if shown)", "Name reference (name source)"],
         [38, 34, 18, 12, 10, 12, 10, 9, 16, 40])
    pom = want in POM_TOP
    rows_out = []
    for uid, t in sorted(tax.items(), key=lambda kv: (kv[1]["subcategory_id"], kv[1]["product"])):
        p = prods.get(uid, {})
        brand = p.get("brand", "") or "— no brand —"
        src = (p.get("source", "") or "").strip()
        sups = sorted({l["supplier"] for l in idx.get(uid, []) if l["supplier"]})
        nameref = src if src.startswith("http") else ("pharmacy consensus: " + ", ".join(sups) if sups else "pharmacy consensus")
        # public price across this product's listings (POM prices are login-gated -> never shown without login)
        price = ""
        if not pom:
            for l in idx.get(uid, []):
                pr = ("£" + l["opt_price"]) if l.get("opt_price") else extract(l["id"])[2]   # structured option price first
                if pr:
                    price = pr; break
        crumb = f'{want} {label}' + (f' › {t["subcategory"]} ({t["subcategory_id"]})' if t["subcategory"] else "")
        ps.append([t["product"], crumb, brand, vol_of(p.get("key_spec", ""), t["product"]), p.get("pack", "") or qty_of(t["product"]),
                   "Yes (POM)" if pom else "No", p.get("suppliers", ""), p.get("listings", ""), price, nameref])
        for c in ps[ps.max_row]: c.font, c.alignment = SM, WRAP
        if nameref.startswith("http"):
            c = ps.cell(row=ps.max_row, column=10); c.hyperlink = nameref; c.font = LINK
        rows_out.append((uid, t, p))
    ps.auto_filter.ref = f"A1:J{ps.max_row}"

    # ---------- Listings per product (enhanced: SKU, code, link, price, prescription) ----------
    ls = wb.create_sheet("Listings per product")
    head(ls, ["Product", "Pharmacy", "Listing title", "SKU / product code", "Commercial code", "Prescription",
              "Public price", "Product link (click)", "Match confidence", "Name reference"],
         [30, 18, 34, 18, 16, 11, 11, 40, 13, 34])
    for uid, t, p in rows_out:
        src = (p.get("source", "") or "").strip()
        nameref = src if src.startswith("http") else "pharmacy consensus"
        for l in sorted(idx.get(uid, []), key=lambda l: l["supplier"]):
            sku, comm, price = extract(l["id"])
            if l.get("opt_sku"):
                sku = l["opt_sku"]              # structured option SKU/price beat the page-scraped guess
            if l.get("opt_price"):
                price = "£" + l["opt_price"]
            if pom:
                price = ""                      # POM price is login-gated -> not public
            ls.append([t["product"], l["supplier"], l["title"], sku, comm, "Yes (POM)" if pom else "No",
                       price, "open", l["confidence"], nameref])
            for c in ls[ls.max_row]: c.font, c.alignment = SM, WRAP
            if l["url"].startswith("http"):
                c = ls.cell(row=ls.max_row, column=8); c.hyperlink = l["url"]; c.value = l["url"]; c.font = LINK
            if nameref.startswith("http"):
                c = ls.cell(row=ls.max_row, column=10); c.hyperlink = nameref; c.font = LINK
    ls.auto_filter.ref = f"A1:J{ls.max_row}"

    # ---------- For your review (flagged items for owner decision) ----------
    rv = wb.create_sheet("For your review")
    head(rv, ["Product", "Equivalence / subcategory", "Why flagged (please decide)", "Brand", "Suppliers", "Listings"],
         [38, 28, 50, 18, 10, 9])
    flagged = 0
    for uid, t, p in rows_out:
        grp = (p.get("equivalence_group", "") or "").lower()
        man = (p.get("manufacturer", "") or "").strip().lower()
        why = []
        if "hybrid" in grp:
            why.append("HYBRID (two agent classes) — confirm category")
        if "unconfirmed" in grp or "ask the supplier" in grp:
            why.append("active agent not stated — confirm with supplier")
        if "not a" in grp:
            why.append("grouped separately — confirm placement")
        if want in ("C01", "C02", "C03", "C04") and man in ("", "not stated", "not named", "korea", "unknown"):
            why.append("no manufacturer/importer — name from pharmacy consensus")   # only for branded injectables
        if why:
            flagged += 1
            rv.append([t["product"], p.get("equivalence_group", "") or t["subcategory"], " ; ".join(why),
                       p.get("brand", "") or "— no brand —", p.get("suppliers", ""), p.get("listings", "")])
            for c in rv[rv.max_row]: c.font, c.alignment = SM, WRAP
    # listing-level review rows (pack/volume/bundle conflicts that could not be auto-resolved) from this category's maps
    STEM_V2 = {"toxin": "C02", "filler": "C01", "booster": "C03", "biostim": "C03", "fat": "C04", "thread": "C05",
               "weight": "WLM", "medicine": "C08", "skincare": "C06", "needle": "C10", "consumable": "C10",
               "device": "C12", "bty": "C14", "sup": "C09", "vac": "C08"}
    for stem, _tag in MAPS:
        if STEM_V2.get(stem) != want:
            continue
        p = FINAL / f"{stem}_listing_map.csv"
        if not p.exists():
            continue
        for m in csv.DictReader(open(p, encoding="utf-8")):
            if not str(m.get("matched", "")).startswith("review"):
                continue
            flagged += 1
            rv.append([m.get("title", ""), m.get("matched", ""), m.get("decision", "") or "confirm this listing",
                       m.get("supplier", ""), "", "listing needs a human decision"])
            for c in rv[rv.max_row]: c.font, c.alignment = SM, WRAP
            u = m.get("url", "")
            if u.startswith("http"):
                c = rv.cell(row=rv.max_row, column=1); c.hyperlink = u; c.font = LINK

    if not flagged:
        rv.append(["(nothing to review — every product matched a reference)", "", "", "", "", ""])
        for c in rv[rv.max_row]: c.font, c.alignment = SM, WRAP

    name = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    out = ROOT / f"output/v2_{name}.xlsx"
    wb.save(out)
    print(f"saved {out} | {len(rows_out)} products | category {want} {label}")


if __name__ == "__main__":
    main()
