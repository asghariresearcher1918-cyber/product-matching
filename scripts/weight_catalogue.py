"""Category 5 - Weight-loss medicines: catalogue + listing map.
These are licensed POMs (emc). Reference below gives each brand's molecule (the equivalence group), class, route,
licensed strengths and source. Strength / route / pack read from the listing title, then page tabs, then image.
Equivalence group = molecule (e.g. all semaglutide brands shown together; same active, different brand/route/licence).
Outputs: catalogue/final/weight_products.csv, weight_listing_map.csv, output/category_05_weight_loss.xlsx
Usage: python -I scripts/weight_catalogue.py"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_facts import page_text, image_text
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
EMC = "https://www.medicines.org.uk/emc/search?q="
# brand regex -> (canonical, molecule, class, route, licence, emc product id, strengths, note)
BRANDS = [
 (r"wegovy", ("Wegovy", "semaglutide", "GLP-1", "varies", "weight management", "13825",
              "SC FlexTouch pen 0.25/0.5/1/1.7/2.4 mg; also oral tablets", "")),
 (r"ozempic", ("Ozempic", "semaglutide", "GLP-1", "SC pen", "type 2 diabetes (weight use off-label)", "9748",
               "0.25/0.5/1/2 mg pre-filled pen", "diabetes licence")),
 (r"rybelsus", ("Rybelsus", "semaglutide", "GLP-1", "oral tablet", "type 2 diabetes", "11507",
                "3/7/14 mg tablets (1.5/4/9 mg titration packs seen)", "oral semaglutide")),
 (r"mounjaro", ("Mounjaro", "tirzepatide", "GLP-1/GIP", "SC pen", "weight management / diabetes", "13595",
                "KwikPen 2.5/5/7.5/10/12.5/15 mg", "dual GLP-1/GIP")),
 (r"trulicity", ("Trulicity", "dulaglutide", "GLP-1", "SC pen", "type 2 diabetes", "3844",
                 "0.75/1.5/3/4.5 mg pen", "diabetes licence")),
 (r"saxenda", ("Saxenda", "liraglutide", "GLP-1", "SC pen", "weight management", "9494",
               "6 mg/mL multi-dose pen", "")),
 (r"victoza", ("Victoza", "liraglutide", "GLP-1", "SC pen", "type 2 diabetes", "21986",
               "6 mg/mL pen", "diabetes licence")),
 (r"byetta|exenatide", ("Byetta", "exenatide", "GLP-1", "SC pen", "type 2 diabetes", "", "pen", "")),
 (r"foundayo|orforglipron", ("Foundayo", "orforglipron", "GLP-1 (oral)", "oral tablet", "verify UK licence", "",
                             "0.8/2.5/5.5/9/14.5/17.2 mg tablets", "newer oral GLP-1 - confirm UK regulatory status")),
 (r"xenical", ("Xenical", "orlistat", "lipase inhibitor", "oral capsule", "obesity", "1204", "120 mg capsules", "")),
 (r"\balli\b", ("Alli", "orlistat", "lipase inhibitor", "oral capsule", "OTC weight loss", "", "60 mg capsules", "pharmacy / OTC")),
 (r"orlistat", ("Orlistat", "orlistat", "lipase inhibitor", "oral capsule", "obesity", "", "120 mg capsules (generic)", "")),
 (r"mysimba", ("Mysimba", "naltrexone + bupropion", "combination", "oral tablet", "weight management", "4248",
               "8 mg/90 mg prolonged-release tablets", "")),
]


# fixed route per brand (the brand determines the form); Wegovy has both and is decided per listing
ROUTE = {"Ozempic": "pen (SC)", "Mounjaro": "pen (SC)", "Trulicity": "pen (SC)", "Saxenda": "pen (SC)", "Victoza": "pen (SC)",
         "Byetta": "pen (SC)", "Rybelsus": "oral", "Foundayo": "oral", "Xenical": "oral", "Alli": "oral", "Orlistat": "oral", "Mysimba": "oral"}


def norm(t):
    return re.sub(r"\b(\d) (\d)\s*mg", r"\1.\2mg", t.lower())  # slug dropped the decimal: "2 4mg" -> "2.4mg"


def route_of(canon, t):
    if canon == "Wegovy": return "oral" if re.search(r"tablet|\btabs?\b", t) else "pen (SC)"
    return ROUTE.get(canon, "")


# licensed strengths (mg) per brand - used to snap parsed values and fix slug-dropped decimals (125 -> 12.5)
VALID = {
    "Mounjaro": [2.5, 5, 7.5, 10, 12.5, 15], "Ozempic": [0.25, 0.5, 1, 2],
    "Wegovy|pen (SC)": [0.25, 0.5, 1, 1.7, 2.4], "Wegovy|oral": [1.5, 4, 9, 14, 25],
    "Rybelsus": [3, 7, 14, 1.5, 4, 9], "Trulicity": [0.75, 1.5, 3, 4.5],
    "Foundayo": [0.8, 2.5, 5.5, 9, 14.5, 17.2],
}


def fmt_mg(v):
    return f"{v:g}"


def strength(canon, rt, t):
    m = re.search(r"(\d+(?:\.\d+)?)\s*mg(?:\s*/\s*0?\.?6?ml)?", t)
    if not m: return ""
    v = float(m.group(1))
    valid = VALID.get(f"{canon}|{rt}") or VALID.get(canon)
    if valid:
        for cand in (v, round(v / 10, 3), round(v / 100, 3)):  # snap, fixing slug-dropped decimals
            if any(abs(cand - x) < 0.001 for x in valid): return fmt_mg(cand)
    return fmt_mg(v)


def pack(title, pid):
    for src, t in (("title", title.lower()), ("page", page_text(pid).lower())):
        m = re.search(r"\b(\d{1,2})\s*doses?\b|\bx\s*(\d{1,2})\b|\(\s*(\d{1,2})\s*\)|\b(\d{1,2})\s*(?:pens?|tablets?|caps?|x\s*30)\b|1\s*x\s*30", t)
        if m:
            g = next((x for x in m.groups() if x), None)
            if g: return int(g), f"pack from {src}"
    return 1, "pack not stated - assumed 1 (owner rule)"


def main():
    rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8"))
            if r["category"] == "Weight-loss medicine" and r["scope"] == "Phase 1"]
    maps, prods = [], {}
    for r in rows:
        title = r["title"] if not r["title"].isdigit() else (r["page_title"] or r["title"])
        tl = norm(title)
        if re.search(r"clinical (guide|review)|: a uk|\bblog\b|how (to|does)|what is ", tl):
            maps.append(dict(r, code="", brand="", group="", decision="article / not a product - review", confidence="review")); continue
        info = next((i for rx, i in BRANDS if re.search(rx, tl)), None)
        if not info:
            maps.append(dict(r, code="", brand="", group="", decision="brand not recognised - review", confidence="review")); continue
        canon, mol, cls, rt0, lic, emc, strs, bnote = info
        rt = route_of(canon, tl)
        st = strength(canon, rt, tl)
        pk, how = pack(title, r["id"])
        grp = f"{mol} ({cls})"
        rc = {"oral": "ORAL", "pen (SC)": "PEN"}.get(rt, "")
        # code = brand + strength + route (one presentation per strength); pack kept as an attribute, not in the code
        parts = [re.sub(r"[^A-Z0-9]+", "", canon.upper())] + ([f"{st}MG"] if st else []) + ([rc] if rc else [])
        c = "-".join(parts)
        conf = "high" if st else "partial - strength not found"
        if not st and canon in ("Saxenda", "Victoza", "Mysimba", "Alli", "Orlistat", "Xenical"): conf = "high"  # single-strength brands
        maps.append(dict(r, code=c, brand=canon, group=grp, decision=f"{mol}; {st or 'single strength'}mg; {rt}; {how}", confidence=conf))
        src = EMC + canon.lower() if not emc else f"https://www.medicines.org.uk/emc/product/{emc}"
        prods.setdefault(c, dict(code=c, brand=canon, molecule=mol, drug_class=cls, equivalence_group=grp, route=rt, strength_mg=st,
                                 licence=lic, vials_or_pens_per_pack=pk, note=bnote, source=src, suppliers=set(), listings=0))
        prods[c]["suppliers"].add(r["supplier"]); prods[c]["listings"] += 1
    for p in prods.values(): p["suppliers"] = len(p["suppliers"])
    out = ROOT / "catalogue/final"; out.mkdir(parents=True, exist_ok=True)
    pc = ["code", "brand", "molecule", "drug_class", "equivalence_group", "route", "strength_mg", "licence", "vials_or_pens_per_pack", "suppliers", "listings", "note", "source"]
    with open(out / "weight_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc); w.writeheader(); w.writerows(sorted(prods.values(), key=lambda p: (p["molecule"], p["brand"], p["code"])))
    with open(out / "weight_listing_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "supplier", "title", "url", "brand", "group", "code", "confidence", "decision", "page_status"], extrasaction="ignore")
        w.writeheader(); w.writerows(maps)

    F = "Arial"; HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
    def head(ws, cols, w):
        ws.append(cols)
        for j, x in enumerate(w, 1):
            c = ws.cell(row=1, column=j); c.font, c.fill = HF, HFILL; c.alignment = Alignment(wrap_text=True, vertical="top"); ws.column_dimensions[get_column_letter(j)].width = x
        ws.freeze_panes = "B2"
    def fmt(ws):
        for c in ws[ws.max_row]: c.font = Font(name=F, size=9); c.alignment = Alignment(wrap_text=True, vertical="top")
    def link(ws, col, url):
        c = ws.cell(row=ws.max_row, column=col); c.hyperlink = url; c.font = Font(name=F, size=9, color="0563C1", underline="single")
    wb = Workbook(); rd = wb.active; rd.title = "Read me"
    cnt = collections.Counter(m["confidence"] for m in maps)
    for t, b in [("Category 5 - Weight-loss medicines: catalogue", True),
                 (f"{len(prods)} product codes, {len(maps)} listings. high {cnt['high']}, rule {cnt['rule']} (strength known, pack defaulted), partial {cnt['partial - strength not found']}, review {cnt['review']}.", False),
                 ("Equivalence group = molecule: all semaglutide brands (Wegovy, Ozempic, Rybelsus) shown together, etc. Same active, different brand/route/licence.", False),
                 ("These are prescription-only medicines (POM) - price shown only to verified prescribers. Licence column flags diabetes-licensed brands used off-label for weight.", False),
                 ("Sheets: Products | Listings | Review.", True)]:
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=12 if b else 10, bold=b)
    rd.column_dimensions["A"].width = 150
    ps = wb.create_sheet("Products")
    head(ps, ["Code", "Brand", "Molecule", "Class", "Equivalence group", "Route", "Strength mg", "Licence", "Per pack", "Suppliers", "Listings", "Note", "Source"],
         [26, 12, 16, 16, 24, 10, 10, 30, 8, 9, 8, 30, 14])
    for p in sorted(prods.values(), key=lambda p: (p["molecule"], p["brand"], p["strength_mg"])):
        ps.append([p[k] if k != "source" else "emc" for k in pc]); fmt(ps); link(ps, len(pc), p["source"])
    ls = wb.create_sheet("Listings")
    head(ls, ["Code", "Brand", "Equivalence group", "Supplier", "Listing (link)", "Confidence", "How decided", "OK?"], [26, 12, 24, 16, 52, 16, 40, 7])
    FILL = {"high": "C6EFCE", "rule": "DDEBF7", "partial - strength not found": "FFF2CC", "review": "F8CBAD"}
    for m in sorted([m for m in maps if m["code"]], key=lambda m: (m["group"], m["brand"], m["code"], m["supplier"])):
        ls.append([m["code"], m["brand"], m["group"], m["supplier"], m["title"], m["confidence"], m["decision"], ""]); fmt(ls); link(ls, 5, m["url"])
        ls.cell(row=ls.max_row, column=6).fill = PatternFill("solid", fgColor=FILL.get(m["confidence"], "FFFFFF"))
    ls.auto_filter.ref = f"A1:H{ls.max_row}"
    rv = wb.create_sheet("Review")
    head(rv, ["Supplier", "Listing (link)", "Why no code"], [18, 62, 40])
    for m in [m for m in maps if not m["code"]]:
        rv.append([m["supplier"], m["title"], m["decision"]]); fmt(rv); link(rv, 2, m["url"])
    p = ROOT / "output/category_05_weight_loss.xlsx"; wb.save(p); print(p)
    print(len(prods), "codes |", dict(cnt), "| molecules", collections.Counter(p["molecule"] for p in prods.values()))
    for c, p in sorted(prods.items()): print(f"  {c:22s} {p['listings']:3d}L {p['suppliers']:2d}S  {p['equivalence_group']}")
    for m in maps:
        if not m["code"] or m["confidence"].startswith("partial"): print(" ", m["confidence"][:7], m["supplier"], "|", m["title"][:55])


if __name__ == "__main__":
    main()
