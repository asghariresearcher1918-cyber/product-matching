"""Final toxin catalogue (phase 1, category 1) built from the official UK SmPCs on emc, and every toxin listing mapped to a code.
Deterministic rules (no AI): brand -> fixed content per vial from the SmPC; pack count from the title/page; pack not stated -> 1 vial (flagged).
Outputs: catalogue/final/toxin_products.csv, catalogue/final/toxin_listing_map.csv, output/category_01_toxin.xlsx
Usage: python -I scripts/toxin_catalogue.py"""
import collections, csv, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from openpyxl import Workbook
from page_facts import page_text, labelled_fields, image_text
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
EMC = "https://www.medicines.org.uk/emc/product/{}/smpc"

# brand: (molecule = equivalence group, manufacturer / MAH, unit type, vial strengths in units, official pack counts, emc ids, licence use, extra)
BRANDS = {
    "Botox":      ("onabotulinumtoxinA", "AbbVie Ltd", "Allergan units", {50: 6185, 100: 859, 200: 436}, [1, 2, 3, 6], "aesthetic + therapeutic", ""),
    "Bocouture":  ("incobotulinumtoxinA", "Merz Pharmaceuticals GmbH", "units", {50: 600, 100: 7418}, [1, 2, 3, 6], "aesthetic", ""),
    "Xeomin":     ("incobotulinumtoxinA", "Merz Pharmaceuticals GmbH", "units", {50: 4609, 100: 6202, 200: 2162}, [1, 2, 3, 4, 6], "therapeutic (aesthetic use off-label; aesthetic brand = Bocouture)", ""),
    "Azzalure":   ("abobotulinumtoxinA", "Ipsen Ltd (Galderma)", "Speywood units", {125: 6584}, [1, 2], "aesthetic", ""),
    "Alluzience": ("abobotulinumtoxinA", "Ipsen Biopharm Ltd (Galderma)", "Speywood units", {125: 13798}, [1, 2], "aesthetic", "ready-to-use solution, 125 units in 0.625 mL (200 units/mL)"),
    "Dysport":    ("abobotulinumtoxinA", "Ipsen Ltd", "Speywood units", {300: 964, 500: 7261}, [1, 2], "therapeutic (aesthetic use off-label; aesthetic brand = Azzalure)", ""),
    "Relfydess":  ("relabotulinumtoxinA", "Ipsen Biopharm Ltd (Galderma)", "units", {150: 100710}, [1, 10], "aesthetic", "ready-to-use solution, 150 units in 1.5 mL (100 units/mL)"),
    "Letybo":     ("letibotulinumtoxinA", "Croma-Pharma GmbH", "units", {50: 13707}, [1, 2], "aesthetic", "also multipacks of 2 and 6 single packs"),
    "Nuceiva":    ("prabotulinumtoxinA", "Evolus Pharma B.V.", "units", {50: 14178}, [1], "aesthetic", "licence PLGB - Great Britain only (not Northern Ireland)"),
}
BRAND_RX = [(b, re.compile(rx)) for b, rx in [("Bocouture", r"bocouture"), ("Xeomin", r"xeomin"), ("Alluzience", r"alluzience"), ("Azzalure", r"azzalure"),
            ("Dysport", r"dysport"), ("Relfydess", r"relfydess"), ("Letybo", r"letybo"), ("Nuceiva", r"nuceiva"), ("Botox", r"\bbotox|vistabel")]]
NOT_PRODUCT = [("accessory -> Clinic consumables", r"opener|bottle opener|cap opener"),
               ("diluent -> Medicine - injectable", r"bacteriostatic|saline"),
               ("Speywood-unit syringes -> Needles, cannulas & syringes", r"syringe x ?10|syringe 100x")]


def code(brand, units, n, mkt=""):
    return f"{brand.upper()}-{units}U-{n}X" + (f"-{mkt}" if mkt else "")


PACKS = [(r"\b10\s*x\s*1\.5|\bx\s*10\b|10 vials|pack of 10", 10), (r"\b6\s*x\b|\bx\s*6\b|6 vials", 6), (r"\b3\s*x\b|\bx\s*3\b|3 vials", 3),
         (r"\b2\s*x\b|\bx\s*2\b|\bdual\b|\btwin\b|\bdouble\b|2 vials|\(2 x|vials x2|box of 2|\bx2\b", 2),
         (r"\bsingle\b|\b1\s*x\b|\bx\s*1\b|1 vial", 1)]


WORD = {"one": 1, "single": 1, "two": 2, "twin": 2, "dual": 2, "double": 2}
PAGE_PACK = [  # explicit statements only - SmPC text copied onto pages ("pack size of 1 or 2 vials") must not count
    r"box contains (\d{1,2})\s*x", r"\b(\d{1,2})\s*x\s*\d{2,3}\s*(?:u|iu|units?)\b", r"\b(\d{1,2})\s*vials?\s*x\s*\d", r"\b(\d{1,2})\s*x\s*1\.5\s*ml",
    r"\b(single|one|twin|dual|double)[- ](?:vial|pack)(?!\s+contains)", r"\(\s*(single) vial\s*\)", r"contents:?\s*(\d{1,2})\s*vials?\b"]


def _n(g):
    return WORD.get(g.lower(), None) if not g.isdigit() else int(g)


def pack_count(title, pid, brand=None, units=None):
    """Owner rule: title -> every tab of the page -> text on the product image -> default 1 vial."""
    for rx, n in PACKS:
        if re.search(rx, title): return n, "pack from title", "title"
    txt = page_text(pid).lower()
    f = labelled_fields(txt)
    for k in ("size and care info", "box contents", "pack contents", "contents", "pack size", "size", "product options", "product option"):
        v = f.get(k, "")
        m = re.match(r"(\d{1,2})\s*(?:x|vials?)\b", v) or re.match(r"(single|one|twin|dual)\b", v)
        if m: return _n(m.group(1)), f"pack from page tab '{k}': {v[:30]}", "page"
    others = [rx for b, rx in BRAND_RX if b != brand]
    for rx in PAGE_PACK:
        for m in re.finditer(rx, txt):
            win = txt[max(0, m.start() - 40): m.end() + 20]
            if not _n(m.group(1)) or any(o.search(win) for o in others): continue  # another product's text (related items)
            note = ""
            if units and re.search(r"(\d{2,3})\s*(?:iu|u\b|units?)", win) and str(units) not in win:
                note = f" - WARNING: page text says '{re.search(r'(\d{2,3})\s*(?:iu|u\b|units?)', win).group(0)}', title says {units}"
            return _n(m.group(1)), f"pack from page text: '{txt[max(0, m.start() - 15): m.end() + 10]}'{note}", "page"
    o = image_text(pid).lower()
    m = re.search(r"\b(\d{1,2})\s*vials?\b", o) or re.search(r"\b(\d{1,2})\s*x\s*\d{2,3}\s*(?:u|iu|units?)\b", o)
    if m: return int(m.group(1)), f"pack from product image: '{o[max(0, m.start() - 10): m.end() + 5]}'", "image"
    return 1, "nothing on title, page tabs or image - 1 vial (owner rule)", "default"


def market(t):
    if re.search(r"\broi\b|ireland", t): return "ROI"
    return ""


def strength(brand, t):
    vials = BRANDS[brand][3]
    if len(vials) == 1: return next(iter(vials)), "fixed by SmPC"
    found = [int(x) for x in re.findall(r"(\d{2,3})\s*(?:iu|u\b|units?|unit)", t)] + [int(x) for x in re.findall(r"\b(50|100|200|300|500)\b", t)]
    found = [x for x in found if x in vials]
    if found: return found[0], "strength from title"
    return None, "strength not stated"


def main():
    rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8")) if r["category"] == "Toxin" and r["scope"] == "Phase 1"]
    ids = {r["id"] for r in rows}
    pages = {}
    for l in open(ROOT / "pages.jsonl", encoding="utf-8"):
        pg = json.loads(l)
        if pg["id"] in ids: pages[pg["id"]] = (pg.get("main_text") or "")[:400]
    maps = []
    for r in rows:
        title = (r["title"] + " | " + r["page_title"]).lower(); page = pages.get(r["id"], "").lower()
        t = title + " | " + page
        np_ = next((lab for lab, rx in NOT_PRODUCT if re.search(rx, t)), None)
        b = next((b for b, rx in BRAND_RX if rx.search(t)), None)
        if np_ or not b:
            maps.append(dict(r, code="", brand=b or "", decision=np_ or "no brand found - review", confidence="review")); continue
        u, why_u = strength(b, t)
        n, why_n, how = pack_count(title, r["id"], b, u)
        mk = market(title)
        if "split pack" in title: why_n += " (split pack: single vial from a multi-vial box)"
        if mk: why_n += f"; market variant {mk} (Ireland pack)"
        if u is None:
            maps.append(dict(r, code="", brand=b, decision=why_u + " - review", confidence="review")); continue
        if how != "default": conf = "high"
        else:
            txt = page_text(r["id"]).lower()
            readable = r["page_status"] == "read" and len(txt) > 300 and "can only be viewed once your account" not in txt
            conf = "rule" if readable else "supplier to confirm"
            why_n = ("page fully read, pack not stated anywhere - 1 vial (owner rule, confirmed 2026-11-18)" if readable
                     else "no readable product page (link redirects / login / site refuses access) - 1 vial assumed, ask the supplier")
        maps.append(dict(r, code=code(b, u, n, mk), brand=b, decision=f"{why_u}; {why_n}", confidence=conf))

    # products: every official strength (1-vial pack at least) + every pack seen in the market
    seen = collections.defaultdict(list)
    for m in maps:
        if m["code"]: seen[m["code"]].append(m)
    prods = {}
    for b, (mol, mah, ut, vials, packs, use, extra) in BRANDS.items():
        for u, emc in vials.items():
            for n in packs:
                c = code(b, u, n)
                if n == 1 or c in seen:
                    prods[c] = dict(code=c, brand=b, molecule=mol, equivalence_group=f"Botulinum toxin A - {mol}", manufacturer=mah, units_per_vial=u,
                                    unit_type=ut, vials_per_pack=n, total_units=u * n, licensed_use=use, official_pack_sizes=", ".join(map(str, packs)),
                                    note=extra, source=EMC.format(emc), status="official (SmPC)",
                                    suppliers=len({m["supplier"] for m in seen.get(c, [])}), listings=len(seen.get(c, [])))
    for c in seen:
        if c not in prods and re.search(r"-ROI$", c) and c[:-4] in {code(b, u, n) for b, v in BRANDS.items() for u in v[3] for n in v[4]}:
            base = dict(prods.get(c[:-4]) or next(p for p in prods.values() if p["code"].startswith(c.split("-")[0] + "-")))
            b, u, n = c.split("-")[0].title(), int(c.split("-")[1][:-1]), int(c.split("-")[2][:-1])
            base.update(code=c, units_per_vial=u, vials_per_pack=n, total_units=u * n, note=(base["note"] + "; " if base["note"] else "") + "Ireland (ROI) market pack - same product, different market label",
                        suppliers=len({m["supplier"] for m in seen[c]}), listings=len(seen[c]))
            prods[c] = base
        elif c not in prods: print("WARNING code not official:", c)
    for c in list(prods):
        if c in seen: prods[c]["suppliers"], prods[c]["listings"] = len({m["supplier"] for m in seen[c]}), len(seen[c])
    out = ROOT / "catalogue/final"; out.mkdir(parents=True, exist_ok=True)
    pc = list(next(iter(prods.values())).keys())
    with open(out / "toxin_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc); w.writeheader(); w.writerows(prods.values())
    mc = ["id", "supplier", "title", "url", "brand", "code", "confidence", "decision", "page_status"]
    with open(out / "toxin_listing_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=mc, extrasaction="ignore"); w.writeheader(); w.writerows(maps)

    # Excel for the owner
    F = "Arial"; HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
    def head(ws, cols, widths):
        ws.append(cols)
        for j, x in enumerate(widths, 1):
            c = ws.cell(row=1, column=j); c.font, c.fill = HF, HFILL; c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.column_dimensions[get_column_letter(j)].width = x
        ws.freeze_panes = "B2"
    def fmt(ws):
        for c in ws[ws.max_row]: c.font = Font(name=F, size=9); c.alignment = Alignment(wrap_text=True, vertical="top")
    def link(ws, col, url):
        c = ws.cell(row=ws.max_row, column=col); c.hyperlink = url; c.font = Font(name=F, size=9, color="0563C1", underline="single")
    wb = Workbook(); rd = wb.active; rd.title = "Read me"
    cnt = collections.Counter(m["confidence"] for m in maps)
    for t, b in [("Category 1 - Botulinum toxins: final catalogue", True),
                 (f"{len(prods)} product codes from the official UK SmPCs (emc) for 9 brands. {len(maps)} supplier listings: "
                  f"high {cnt['high']} (pack found on title, page tabs or image) | rule {cnt['rule']} (page fully read, nothing stated - 1 vial, owner rule) | "
                  f"supplier to confirm {cnt['supplier to confirm']} (no readable page) | review {cnt['review']}.", False),
                 ("Code = BRAND-UNITS PER VIAL-VIALS PER PACK, e.g. AZZALURE-125U-2X. Units are not interchangeable between brands (Allergan vs Speywood units),", False),
                 ("so price per unit is compared only within the same brand; brands with the same molecule share an equivalence group (shown together in search).", False),
                 ("Sheets: Products (the catalogue) | Listings (each supplier listing -> code) | Review (listings without a code) | Not stocked (official packs no supplier lists).", False),
                 ("Your check: column 'OK?' in Listings - mark any wrong code.", True)]:
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=12 if b else 10, bold=b)
    rd.column_dimensions["A"].width = 150
    ps = wb.create_sheet("Products")
    cols = ["code", "brand", "equivalence_group", "manufacturer", "units_per_vial", "unit_type", "vials_per_pack", "total_units", "licensed_use",
            "official_pack_sizes", "suppliers", "listings", "note", "source"]
    head(ps, [c.replace("_", " ").capitalize() for c in cols], [24, 11, 34, 26, 8, 13, 8, 8, 30, 10, 9, 8, 34, 14])
    for p in sorted(prods.values(), key=lambda p: (p["brand"], p["units_per_vial"], p["vials_per_pack"])):
        ps.append([p[c] if c != "source" else "SmPC (emc)" for c in cols]); fmt(ps); link(ps, len(cols), p["source"])
        if not p["listings"]: ps.cell(row=ps.max_row, column=11).fill = PatternFill("solid", fgColor="F8CBAD")
    ls = wb.create_sheet("Listings")
    head(ls, ["Code", "Supplier", "Listing (link)", "Confidence", "How decided", "OK?"], [24, 20, 60, 11, 46, 8])
    for m in sorted([m for m in maps if m["code"]], key=lambda m: (m["code"], m["supplier"])):
        ls.append([m["code"], m["supplier"], m["title"], m["confidence"], m["decision"], ""]); fmt(ls); link(ls, 3, m["url"])
        ls.cell(row=ls.max_row, column=4).fill = PatternFill("solid", fgColor={"high": "C6EFCE", "rule": "DDEBF7", "supplier to confirm": "FFF2CC"}[m["confidence"]])
    ls.auto_filter.ref = f"A1:F{ls.max_row}"
    rv = wb.create_sheet("Review")
    head(rv, ["Supplier", "Listing (link)", "Brand", "Why no code"], [20, 60, 12, 50])
    for m in [m for m in maps if not m["code"]]:
        rv.append([m["supplier"], m["title"], m["brand"], m["decision"]]); fmt(rv); link(rv, 2, m["url"])
    ns = wb.create_sheet("Not stocked")
    head(ns, ["Brand", "Strength", "Official pack sizes", "Packs our suppliers list", "Note"], [12, 10, 16, 24, 50])
    for b, (mol, mah, ut, vials, packs, use, extra) in BRANDS.items():
        for u in vials:
            have = sorted({p["vials_per_pack"] for p in prods.values() if p["brand"] == b and p["units_per_vial"] == u and p["listings"]})
            if set(have) != set(packs):
                ns.append([b, f"{u} {ut}", ", ".join(map(str, packs)), ", ".join(map(str, have)) or "none",
                           "emc says 'not all pack sizes may be marketed'" + ("; therapeutic licence" if "therapeutic (" in use else "")]); fmt(ns)
    p = ROOT / "output/category_01_toxin.xlsx"; wb.save(p); print(p)
    print(len(prods), "products |", cnt, "| codes used:", len(seen))
    for c, ms in sorted(seen.items()): print(f"  {c:22s} {len(ms):3d} listings {len({m['supplier'] for m in ms}):2d} suppliers")
    for m in maps:
        if not m["code"]: print("  REVIEW", m["supplier"], "|", m["title"], "|", m["decision"])


if __name__ == "__main__":
    main()
