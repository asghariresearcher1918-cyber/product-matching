"""Unified master catalogue - merges all 15 category product files into one normalised schema for the web team.
Common columns: uid, category, equivalence_group, brand, product, key_spec, manufacturer, pack, market, verified,
suppliers, listings, source. Also merges every listing map into one listing->code index.
Outputs: catalogue/final/master_catalogue.csv, master_listing_index.csv, output/master_catalogue.xlsx
Usage: python -I scripts/master_catalogue.py"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"


def g(r, *keys):
    for k in keys:
        if r.get(k): return r[k]
    return ""


def join(*parts, sep=" "):
    return sep.join(str(p) for p in parts if p not in ("", None, "0", 0))


# (file, category label, tag, row->unified mapper)
def _vials(n, vol=""):
    n = n or "1"
    unit = "vials" if n not in ("1", "") else "vial"
    return f"{n} x {vol} {unit}" if vol else f"{n} {unit}"   # liquid toxins show ml/vial; powders reconstitute on use
def toxin(r): return dict(group=g(r, "equivalence_group"), brand=g(r, "brand"), product=join(g(r, "brand"), g(r, "molecule")),
                          spec=("100 units/ml - " if g(r, "brand") == "Relfydess" else "") + _vials(g(r, "vials_per_pack"), g(r, "volume_ml")),
                          man=g(r, "manufacturer"), pack=g(r, "vials_per_pack"), market="",
                          verified="reference-matched" if g(r, "status") == "reference" else g(r, "status"), source=g(r, "source"))
def biostim(r): return dict(group=g(r, "equivalence_group"), brand=g(r, "brand"), product=join(g(r, "brand"), g(r, "variant")),
                            spec=g(r, "pack_size"), man=g(r, "manufacturer"), pack=g(r, "vials_per_pack"), market="",
                            verified=g(r, "agent_verified"), source=g(r, "source"))
def fat(r): return dict(group=g(r, "equivalence_group"), brand=g(r, "brand"), product=join(g(r, "brand"), g(r, "variant")),
                        spec=_vials(g(r, "vials_per_pack"), (g(r, "volume_ml") or "").replace("ml", "") + "ml" if g(r, "volume_ml") else ""),
                        man=g(r, "manufacturer"), pack=g(r, "vials_per_pack"), market="",
                        verified="reference-matched" if "reference" in g(r, "agent_verified") else g(r, "agent_verified"), source=g(r, "source"))
def _mkt(v): return "" if v in ("UK/std", "UK", "std", "") else v
def _packspec(n, vol, unit="ml", lido=False):
    """Market-style presentation: '2 x 1ml with lidocaine'."""
    n = n or "1"
    base = f"{n} x {vol}{unit}" if vol else (f"{n} x" if n != "1" else "")
    return (base + (" with lidocaine" if lido else "")).strip()
def filler(r): return dict(group=g(r, "equivalence_group"), brand=g(r, "brand"), product=join(g(r, "brand"), g(r, "line")),
                           spec=_packspec(g(r, "syringes_per_pack"), g(r, "volume_ml"), "ml", g(r, "lidocaine") in ("yes", "Y", "True")),
                           man=g(r, "manufacturer"), pack=g(r, "syringes_per_pack"), market=_mkt(g(r, "market")), verified=g(r, "brand_verified"), source=g(r, "source"))
def thread(r): return dict(group=g(r, "equivalence_group"), brand=g(r, "brand"), product=join(g(r, "brand"), g(r, "thread_type"), g(r, "material")),
                           spec=join(g(r, "gauge"), g(r, "length"), g(r, "delivery"), "x" + g(r, "pcs_per_pack") if g(r, "pcs_per_pack") else ""),
                           man=g(r, "manufacturer"), pack=g(r, "pcs_per_pack"), market="", verified=g(r, "brand_verified"), source="")
def weight(r): return dict(group=g(r, "equivalence_group"), brand=g(r, "brand"), product=join(g(r, "brand"), g(r, "molecule")),
                           spec=join(g(r, "strength_mg") + "mg" if g(r, "strength_mg") else "", g(r, "route")),
                           man=g(r, "drug_class"), pack=g(r, "vials_or_pens_per_pack"), market="", verified=g(r, "licence"), source=g(r, "source"))
def medicine(r): return dict(group=g(r, "equivalence_group"), brand=g(r, "brands"), product=g(r, "molecule"),
                             spec=join(g(r, "strength"), g(r, "form")), man="", pack="", market=g(r, "category"), verified="", source=g(r, "source"))
def booster(r): return dict(group=g(r, "active_class"), brand=g(r, "brand"), product=join(g(r, "brand"), g(r, "line")),
                            spec=_packspec(g(r, "pack"), (g(r, "volume") or "").replace("ml", ""), "ml"), man=g(r, "manufacturer"),
                            pack=g(r, "pack"), market=_mkt(g(r, "market")), verified="", source="")
def skincare(r): return dict(group=g(r, "function"), brand=g(r, "brand"), product=join(g(r, "brand"), g(r, "name")),
                             spec=g(r, "size"), man="", pack="", market="", verified="", source="")
def needle(r): return dict(group=g(r, "subtype"), brand=g(r, "brands"), product=join(g(r, "subtype"), g(r, "gauge"), g(r, "length"), g(r, "volume"), g(r, "luer")),
                           spec=join(g(r, "gauge"), g(r, "length"), g(r, "volume"), g(r, "luer"), "x" + g(r, "pack") if g(r, "pack") not in ("", "1") else ""),
                           man="", pack=g(r, "pack"), market="", verified="", source="")
def consumable(r): return dict(group=g(r, "subtype"), brand=g(r, "brands"), product=join(g(r, "subtype"), g(r, "name")),
                               spec=g(r, "size"), man="", pack=g(r, "pack"), market="", verified="", source="")
def device(r): return dict(group=g(r, "subtype"), brand=g(r, "brand"), product=join(g(r, "brand"), g(r, "name")),
                           spec=g(r, "kind"), man="", pack="", market="", verified="", source="")
def simple(r): return dict(group=g(r, "subtype"), brand=g(r, "brand"), product=join(g(r, "brand"), g(r, "name")),
                           spec=g(r, "size"), man="", pack="", market="", verified="", source="")

FILES = [
 ("toxin_products.csv", "Toxin", "TOX", toxin),
 ("filler_products.csv", "Dermal filler", "FIL", filler),
 ("booster_products.csv", "Skin booster / PN / mesotherapy", "BST", booster),
 ("biostim_products.csv", "Biostimulator", "BIO", biostim),
 ("fat_products.csv", "Fat dissolving", "FAT", fat),
 ("thread_products.csv", "PDO threads", "THR", thread),
 ("weight_products.csv", "Weight-loss medicine", "WGT", weight),
 ("medicine_products.csv", "Medicines", "MED", medicine),
 ("skincare_products.csv", "Skincare, haircare & peels", "SKN", skincare),
 ("needle_products.csv", "Needles, cannulas & syringes", "NDL", needle),
 ("consumable_products.csv", "Clinic consumables & PPE", "CON", consumable),
 ("device_products.csv", "Devices & equipment", "DEV", device),
 ("bty_products.csv", "Beauty (nails/brows/lashes/PMU/makeup)", "BTY", simple),
 ("sup_products.csv", "Supplements", "SUP", simple),
 ("vac_products.csv", "Vaccine", "VAC", simple),
]
MAPS = [
 ("toxin_listing_map.csv", "Toxin", "TOX"), ("filler_listing_map.csv", "Dermal filler", "FIL"),
 ("booster_listing_map.csv", "Skin booster / PN / mesotherapy", "BST"), ("biostim_listing_map.csv", "Biostimulator", "BIO"),
 ("fat_listing_map.csv", "Fat dissolving", "FAT"), ("thread_listing_map.csv", "PDO threads", "THR"),
 ("weight_listing_map.csv", "Weight-loss medicine", "WGT"), ("medicine_listing_map.csv", "Medicines", "MED"),
 ("skincare_listing_map.csv", "Skincare, haircare & peels", "SKN"), ("needle_listing_map.csv", "Needles, cannulas & syringes", "NDL"),
 ("consumable_listing_map.csv", "Clinic consumables & PPE", "CON"), ("device_listing_map.csv", "Devices & equipment", "DEV"),
 ("bty_listing_map.csv", "Beauty (nails/brows/lashes/PMU/makeup)", "BTY"), ("sup_listing_map.csv", "Supplements", "SUP"),
 ("vac_listing_map.csv", "Vaccine", "VAC"),
]
COLS = ["uid", "category", "equivalence_group", "brand", "product", "key_spec", "manufacturer", "pack", "market", "verified", "suppliers", "listings", "source"]


def main():
    master = []
    for fn, cat, tag, fx in FILES:
        p = FINAL / fn
        if not p.exists():
            print("MISSING", fn); continue
        for r in csv.DictReader(open(p, encoding="utf-8")):
            u = fx(r)
            sup = g(r, "suppliers", "supplier_n")
            master.append({"uid": f"{tag}:{r['code']}", "category": cat, "equivalence_group": u["group"],
                           "brand": u["brand"], "product": (u["product"] or r["code"]).strip(), "key_spec": u["spec"].strip(),
                           "manufacturer": u["man"], "pack": u["pack"], "market": u["market"], "verified": u["verified"],
                           "suppliers": int(sup or 0), "listings": int(g(r, "listings") or 0), "source": u["source"]})
    # display name priority: authoritative brand reference > real supplier listing title > parsed
    cnpath = FINAL / "canonical_names.csv"
    if cnpath.exists():
        cn = {r["uid"]: r["name"] for r in csv.DictReader(open(cnpath, encoding="utf-8")) if r["name"]}
        for m in master:
            if m["uid"] in cn:
                m["product"] = cn[m["uid"]]
    rnpath = FINAL / "reference_names.csv"
    if rnpath.exists():
        rn = {r["uid"]: r["name"] for r in csv.DictReader(open(rnpath, encoding="utf-8")) if r["name"]}
        for m in master:
            if m["uid"] in rn:
                m["product"] = rn[m["uid"]]; m["verified"] = "reference-matched"
    # one COMPLETE title. Reference-matched -> our clean name + presentation. Non-reference -> the pharmacy's own
    # title (already complete), left as-is so we never duplicate the size/pack it already contains.
    for m in master:
        sp = m.get("key_spec", "")
        if (m.get("verified") == "reference-matched" and sp and sp.lower() not in m["product"].lower()
                and m["category"] != "Biostimulator"):   # biostim name is already the complete commercial name
            m["product"] = f'{m["product"]} ({sp})'
    master.sort(key=lambda m: (m["category"], m["equivalence_group"], m["brand"], m["product"]))
    with open(FINAL / "master_catalogue.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(master)

    # unified listing index. Authoritative titles restored from the cached page (data/title_overrides.csv) replace
    # the scraper-damaged ones here, so the display name canonical_names.py derives carries the right punctuation.
    tov = {}
    tp = ROOT / "data/title_overrides.csv"
    if tp.exists():
        tov = {r["id"]: r["title"] for r in csv.DictReader(open(tp, encoding="utf-8")) if r.get("title")}
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "scripts"))
    from read_rules import strip_shop_code
    _tail = re.compile(r"[\(\[]?\s*[A-Za-z]{0,4}\d[A-Za-z0-9]*\s*[\)\]]?\s*$")   # ends in a code-like token?
    idx = []
    for fn, cat, tag in MAPS:
        p = FINAL / fn
        if not p.exists(): continue
        for r in csv.DictReader(open(p, encoding="utf-8")):
            if not r.get("code"): continue
            lid = r.get("id", "")
            title = tov.get(lid, r.get("title", ""))
            if _tail.search(title):                 # only read the page when a trailing shop-code is possible
                title = strip_shop_code(title, lid)
            # NOTE: sterile/non-sterile is NOT forced into the name. It stays only if the shop's own title has it
            # (clean() preserves it); otherwise it is surfaced in the product DESCRIPTION (see build_site_v2).
            idx.append({"uid": f"{tag}:{r['code']}", "category": cat, "supplier": r.get("supplier", ""),
                        "listing_title": title, "url": r.get("url", ""), "confidence": r.get("confidence", "")})
    with open(FINAL / "master_listing_index.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["uid", "category", "supplier", "listing_title", "url", "confidence"]); w.writeheader(); w.writerows(idx)

    # Excel
    F = "Arial"; HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
    def head(ws, cols, w):
        ws.append(cols)
        for j, x in enumerate(w, 1):
            c = ws.cell(row=1, column=j); c.font, c.fill = HF, HFILL; c.alignment = Alignment(wrap_text=True, vertical="top"); ws.column_dimensions[get_column_letter(j)].width = x
        ws.freeze_panes = "A2"
    def fmt(ws):
        for c in ws[ws.max_row]: c.font = Font(name=F, size=9); c.alignment = Alignment(wrap_text=True, vertical="top")
    def link(ws, col, url):
        if url and url.startswith("http"):
            c = ws.cell(row=ws.max_row, column=col); c.hyperlink = url; c.font = Font(name=F, size=9, color="0563C1", underline="single")
    wb = Workbook(); rd = wb.active; rd.title = "Read me"
    total_sup = sum(m["listings"] for m in master)
    multi = sum(1 for m in master if m["suppliers"] > 1)
    def line(t, sz=10, b=False):
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=sz, bold=b)
    line("Master catalogue - all categories", 13, True)
    line(f"{len(master)} product codes covering {total_sup} supplier listings across 15 categories.", 10)
    line(f"{multi} codes are stocked by more than one supplier (price-comparison candidates); the rest are single-supplier (list only).", 10)
    line("One row per product code. equivalence_group = how products are grouped for search/suggestions within a category "
         "(molecule / active class / brand line / function / spec). key_spec = the comparable spec (strength, volume, gauge, size). "
         "'market' flags variants like hologram / ROI. 'verified' carries each category's confidence/licence note.", 10)
    line("Sheets: All products (filter here) | By category | Compare (multi-supplier only). "
         "The full listing->code index is in catalogue/final/master_listing_index.csv.", 10, True)
    line("uid = TAG:code, unique across the catalogue (TAG = category short code).", 9)
    rd.column_dimensions["A"].width = 165

    def products_sheet(ws, rows):
        head(ws, ["UID", "Category", "Equivalence group", "Brand", "Product", "Key spec", "Manufacturer", "Pack", "Market", "Verified", "Suppliers", "Listings", "Source"],
             [16, 24, 26, 18, 38, 20, 18, 6, 8, 12, 9, 8, 16])
        for m in rows:
            ws.append([m[c] for c in COLS]); fmt(ws); link(ws, 13, m["source"])
        ws.auto_filter.ref = f"A1:M{ws.max_row}"
    products_sheet(wb.create_sheet("All products"), master)
    products_sheet(wb.create_sheet("Compare (multi-supplier)"), [m for m in master if m["suppliers"] > 1])

    cs = wb.create_sheet("By category")
    head(cs, ["Category", "Codes", "Listings", "Multi-supplier", "Single-supplier"], [36, 9, 10, 15, 15])
    agg = collections.defaultdict(lambda: [0, 0, 0])
    for m in master:
        a = agg[m["category"]]; a[0] += 1; a[1] += m["listings"]; a[2] += (1 if m["suppliers"] > 1 else 0)
    for fn, cat, tag, fx in FILES:
        if cat in agg:
            a = agg[cat]; cs.append([cat, a[0], a[1], a[2], a[0] - a[2]]); fmt(cs)
    cs.append(["TOTAL", len(master), total_sup, multi, len(master) - multi]); fmt(cs)
    for c in cs[cs.max_row]: c.font = Font(name=F, size=9, bold=True)

    p = ROOT / "output/master_catalogue.xlsx"; wb.save(p); print(p)
    print(f"{len(master)} codes | {total_sup} listings | {multi} multi-supplier | index {len(idx)} rows")


if __name__ == "__main__":
    main()
