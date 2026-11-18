"""Category 3 - Fat dissolving / lipolytics: catalogue + listing map.
No central UK register (CE devices / cosmetics). Reference below gives each brand's active agent (the equivalence
group), manufacturer and standard presentation, with a 'verified' flag (agent confirmed against sources, 2026-11-19).
Pack / volume read from title -> page tabs -> product image (page_facts, owner rules); nothing -> smallest, flagged.
Outputs: catalogue/final/fat_products.csv, fat_listing_map.csv, output/category_03_fat_dissolving.xlsx
Usage: python -I scripts/fat_catalogue.py"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_facts import page_text, image_text
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
GROUP = {
    "DCA": "Deoxycholic acid (sodium deoxycholate)",
    "PPC+DCA": "Phosphatidylcholine + deoxycholate (PPC)",
    "lecithin": "Lecithin / riboflavin cocktail ('bottle' type)",
    "meso": "Mesotherapy lipolytic cocktail",
    "anticellulite": "Anti-cellulite / lipodystrophy (not a fat dissolver)",
    "unknown": "Unconfirmed - ask the supplier",
}
# regex (specific first) -> (canonical, agent, manufacturer, verified, note)
BRANDS = [
 (r"aqualyx", ("Aqualyx", "DCA", "Marllor Biomedical (Italy)", True, "modified deoxycholic acid sodium salt; 8 ml vials (verified: DCA)")),
 (r"desobody|deso ?body", ("DesoBody", "DCA", "Love Cosmedical (Italy)", True, "sodium deoxycholate 1.25% - body (verified)")),
 (r"desoface|deso ?face", ("DesoFace", "DCA", "Love Cosmedical (Italy)", True, "sodium deoxycholate 0.5% - face (verified)")),
 (r"kabelline", ("Kabelline", "DCA", "Korea", True, "deoxycholate + L-carnitine (verified: DCA-based)")),
 (r"cincelar", ("Cincelar", "DCA", "not named", False, "deoxycholate + carnitine per page")),
 (r"lemon ?bottle", ("Lemon Bottle", "lecithin", "SID/SIF Medicos (Korea)", True, "riboflavin + lecithin + bromelain; no MHRA/CE (verified: lecithin/riboflavin)")),
 (r"skinny bottle", ("The Skinny Bottle", "lecithin", "not named", False, "riboflavin/lecithin type per page")),
 (r"pine bottle", ("Pine Bottle", "lecithin", "not named", False, "riboflavin/lecithin type per page")),
 (r"lipo ?lab", ("Lipo Lab", "PPC+DCA", "CSBIO (Korea)", True, "phosphatidylcholine + sodium deoxycholate; V-Line = face (verified: PPC+DCA)")),
 (r"inno-?tds draining|draining ppc", ("Inno-TDS Draining PPC", "PPC+DCA", "Innoaesthetics", True, "phosphatidylcholine draining solution (verified: PPC)")),
 (r"bcn adipo", ("BCN Adipo Forte", "PPC+DCA", "Institute BCN (Spain)", True, "PPC mesotherapy lipolytic (verified: PPC-based)")),
 (r"myfiller.*slim|revitalize slim", ("Myfiller Revitalize Slim", "PPC+DCA", "not named", False, "PPC + deoxycholate + carnitine per page")),
 (r"dr\.? ?lipo", ("Dr. Lipo", "PPC+DCA", "not named", False, "PPC + carnitine cocktail per page; Body / V-Line (face)")),
 (r"mesoestetic.*lipolytic|c\.?prof 221", ("Mesoestetic C.Prof 221", "meso", "mesoestetic (Spain)", True, "lipolytic mesotherapy solution (verified brand)")),
 (r"mesosculpt", ("MesoSculpt C71", "meso", "MCCM", False, "mesotherapy lipolytic, 1 ml per page")),
 (r"adipose lipolytic", ("Adipose Lipolytic Meso", "meso", "not named", False, "lipolytic mesotherapy / micro-needling kit per page")),
 (r"alidya", ("Alidya", "anticellulite", "Marllor Biomedical (Italy)", True, "buffered amino-acid solution for lipodystrophy / cellulite - NOT a fat dissolver (verified)")),
]
# standard per-vial volume (ml); Dr. Lipo depends on variant (handled below)
FIXED_VOL = {"Aqualyx": "8", "DesoFace": "10", "DesoBody": "10", "Cincelar": "8", "Lemon Bottle": "10",
             "The Skinny Bottle": "10", "Pine Bottle": "10", "Lipo Lab": "10", "Inno-TDS Draining PPC": "5",
             "BCN Adipo Forte": "10", "Myfiller Revitalize Slim": "10", "Mesoestetic C.Prof 221": "10",
             "MesoSculpt C71": "1", "Alidya": "10", "Kabelline": "8"}
NOT_PRODUCT = [
 ("bundle / multi-buy offer", r"^\s*buy\b|\bget 1\b|starter pack|complete injection kit|reboot"),
 ("training -> Training", r"\btraining\b"),
 ("accessory (cream) -> review", r"master cream"),
]


def facts(title, pid):
    t = title.lower(); page = page_text(pid).lower()
    vol = (re.search(r"(\d(?:\.\d+)?)\s*ml", t) or re.search(r"(\d(?:\.\d+)?)\s*ml", page[:400]))
    vol = vol.group(1) if vol else ""
    pk, how = None, ""
    for src, txt in (("title", t), ("page", page)):
        m = re.search(r"\b(\d{1,2})\s*x\s*\d|\b(\d{1,2})\s*(?:vials?|x\s*\d*\.?\d*\s*ml)|\btwin\b|\bsingle\b|half", txt)
        if m:
            g = next((x for x in m.groups() if x), None)
            pk = int(g) if g else (5 if "half" in m.group(0) else 1)
            how = f"pack from {src}"; break
    if pk is None:
        o = image_text(pid).lower(); m = re.search(r"\b(\d{1,2})\s*x\s*\d|\b(\d{1,2})\s*vials?\b", o)
        if m: pk, how = int(next(x for x in m.groups() if x)), "pack from image"
    if pk is None: pk, how = 1, "pack not stated - assumed 1 (owner rule)"
    return pk, how, vol


def main():
    rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8"))
            if r["category"] == "Fat dissolving" and r["scope"] == "Phase 1"]
    maps, prods = [], {}
    for r in rows:
        title = r["title"] if not r["title"].isdigit() else (r["page_title"] or r["title"])
        tl = title.lower()
        np_ = next((lab for lab, rx in NOT_PRODUCT if re.search(rx, tl)), None)
        info = next((i for rx, i in BRANDS if re.search(rx, tl)), None)
        if np_ or not info:
            maps.append(dict(r, code="", brand=info[0] if info else "", group="", decision=np_ or "brand not recognised - review", confidence="review")); continue
        canon, agent, mah, verified, bnote = info
        pk, how, vol = facts(title, r["id"])
        variant = ""
        if canon == "Lipo Lab": variant = "VLINE" if re.search(r"v-?line", tl) else ""
        if canon == "Dr. Lipo": variant = "VFACE" if re.search(r"v[- ]?face|\bv\b", tl) else ("BODY" if "body" in tl else "")
        if canon == "Dr. Lipo": v = "5" if variant == "VFACE" else "10"
        else: v = FIXED_VOL.get(canon, vol)  # per-vial volume is fixed per brand
        vstr = (v + "ML") if v else ""
        parts = [re.sub(r"[^A-Z0-9]+", "", canon.upper())] + ([variant] if variant else []) + ([vstr] if vstr else []) + [f"{pk}X"]
        c = "-".join(parts)
        conf = "high" if "not stated" not in how else ("rule" if r["page_status"] == "read" and page_text(r["id"]) else "supplier to confirm")
        if not verified and conf == "high": conf = "high*"
        maps.append(dict(r, code=c, brand=canon, group=GROUP[agent], decision=how + ("" if verified else "; agent per page - confirm with manufacturer"), confidence=conf))
        prods.setdefault(c, dict(code=c, brand=canon, variant=variant, active_agent=agent, equivalence_group=GROUP[agent], manufacturer=mah,
                                 volume_ml=v, vials_per_pack=pk, agent_verified="yes" if verified else "NO - confirm", note=bnote, suppliers=set(), listings=0))
        prods[c]["suppliers"].add(r["supplier"]); prods[c]["listings"] += 1
    for p in prods.values(): p["suppliers"] = len(p["suppliers"])
    out = ROOT / "catalogue/final"; out.mkdir(parents=True, exist_ok=True)
    pc = ["code", "brand", "variant", "active_agent", "equivalence_group", "manufacturer", "volume_ml", "vials_per_pack", "agent_verified", "suppliers", "listings", "note"]
    with open(out / "fat_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc); w.writeheader(); w.writerows(sorted(prods.values(), key=lambda p: (p["active_agent"], p["brand"], p["code"])))
    with open(out / "fat_listing_map.csv", "w", newline="", encoding="utf-8") as f:
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
    for t, b in [("Category 3 - Fat dissolving / lipolytics: catalogue", True),
                 (f"{len(prods)} product codes across {len(set(p['active_agent'] for p in prods.values()))} agent groups. {len(maps)} listings: "
                  f"high {cnt['high']}, high* {cnt['high*']} (pack certain, agent to confirm), rule {cnt['rule']}, supplier to confirm {cnt['supplier to confirm']}, review {cnt['review']}.", False),
                 ("No central UK register (CE devices / cosmetics). Agent is the equivalence group shown together: deoxycholic acid,", False),
                 ("PPC (phosphatidylcholine), lecithin/riboflavin 'bottle' type, mesotherapy cocktail, and anti-cellulite (Alidya - a different purpose).", False),
                 ("Price per unit compared only within the same brand. Sheets: Products | Listings | Review.", True)]:
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=12 if b else 10, bold=b)
    rd.column_dimensions["A"].width = 150
    ps = wb.create_sheet("Products")
    head(ps, ["Code", "Brand", "Variant", "Active agent", "Equivalence group", "Manufacturer", "Volume ml", "Vials/pack", "Agent verified", "Suppliers", "Listings", "Note"],
         [30, 16, 8, 12, 38, 26, 8, 8, 13, 9, 8, 44])
    for p in sorted(prods.values(), key=lambda p: (p["equivalence_group"], p["brand"], p["code"])):
        ps.append([p[k] for k in pc]); fmt(ps)
        if p["agent_verified"].startswith("NO"): ps.cell(row=ps.max_row, column=9).fill = PatternFill("solid", fgColor="FFF2CC")
    ls = wb.create_sheet("Listings")
    head(ls, ["Code", "Brand", "Equivalence group", "Supplier", "Listing (link)", "Confidence", "How decided", "OK?"], [30, 16, 38, 18, 50, 12, 42, 7])
    FILL = {"high": "C6EFCE", "high*": "E2EFDA", "rule": "DDEBF7", "supplier to confirm": "FFF2CC", "review": "F8CBAD"}
    for m in sorted([m for m in maps if m["code"]], key=lambda m: (m["group"], m["brand"], m["code"], m["supplier"])):
        ls.append([m["code"], m["brand"], m["group"], m["supplier"], m["title"], m["confidence"], m["decision"], ""]); fmt(ls); link(ls, 5, m["url"])
        ls.cell(row=ls.max_row, column=6).fill = PatternFill("solid", fgColor=FILL.get(m["confidence"], "FFFFFF"))
    ls.auto_filter.ref = f"A1:H{ls.max_row}"
    rv = wb.create_sheet("Review")
    head(rv, ["Supplier", "Listing (link)", "Brand", "Why no code"], [18, 60, 16, 46])
    for m in [m for m in maps if not m["code"]]:
        rv.append([m["supplier"], m["title"], m["brand"], m["decision"]]); fmt(rv); link(rv, 2, m["url"])
    p = ROOT / "output/category_03_fat_dissolving.xlsx"; wb.save(p); print(p)
    print(len(prods), "codes |", dict(cnt))
    for c, p in sorted(prods.items()): print(f"  {c:28s} {p['listings']:3d}L {p['suppliers']:2d}S  {p['equivalence_group']}")
    for m in maps:
        if not m["code"]: print("  REVIEW", m["supplier"], "|", m["title"][:50], "|", m["decision"])


if __name__ == "__main__":
    main()
