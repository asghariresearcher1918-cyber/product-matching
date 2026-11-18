"""Category 4 - PDO / lifting threads: catalogue + listing map.
Threads match on brand + material (PDO / PLLA / PCL / PLGA) + thread type (mono / screw-twist / cog-barbed / cone) +
gauge + length + delivery (needle / cannula) + pack. Most brands here are single-supplier, so most are 'list only'
(compare only where two suppliers have the identical brand+type+gauge+length+pack). Pack read from title/page/image.
Equivalence group = material + type (shown together: e.g. 'PDO cog/barbed' for lifting threads of any brand).
Outputs: catalogue/final/thread_products.csv, thread_listing_map.csv, output/category_04_threads.xlsx
Usage: python -I scripts/thread_catalogue.py"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_facts import page_text, image_text
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent

# brand regex -> (canonical, material, manufacturer, verified)
BRANDS = [
 (r"silhouette", ("Silhouette Soft", "PLLA/PLGA", "Sinclair", True)),
 (r"\bmint\b", ("MINT", "PDO", "HansBiomed", True)),
 (r"definisse", ("Definisse", "PDO", "Relife", True)),
 (r"lifskin", ("LIFSkin", "PDO", "not named", False)),
 (r"rejuva", ("Rejuva", "PDO", "not named", False)),
 (r"croquis", ("Croquis", "PDO", "not named", False)),
 (r"ultra ?v", ("Ultra V", "PDO", "Ultra V Line (Korea)", True)),
 (r"countourel|contourel", ("Croma Contourel", "PDO", "Croma", True)),
 (r"princess", ("Croma Princess", "PDO", "Croma", True)),
 (r"\bneo\b", ("NEO Thread", "PDO", "not named", False)),
 (r"springthread|spring thread", ("SpringThread", "PLLA", "Promoitalia", True)),
 (r"intraline", ("Intraline", "PDO", "Intraline", True)),
 (r"\bmd\b.*thread|md double", ("MD Threads", "PDO", "not named", False)),
 (r"\bpcl\b", ("Generic PCL", "PCL", "varies", False)),
 (r"\bpdo\b|thread", ("Generic PDO", "PDO", "own brand", False)),
]
# thread type (specific first)
TYPES = [
 ("cog/barbed", r"\bcog\b|barb|moulding|molding|fishbone|anchor|ancorage|\bboca\b|cutting|\b\d+d\b|w-?type|bi-?u|contour|max\b|ultra\+?|double arm|spring"),
 ("screw/twist", r"screw|twist|spiral|double twist"),
 ("cone", r"\bcone|suture"),
 ("multi", r"multi"),
 ("double-needle", r"double needle"),
 ("mono", r"\bmono\b|smooth|basic|\bfine\b|\btip\b|\bup\b|\bfix\b|\bpetit\b|\beasy\b"),
]


def gauge(t):
    m = re.search(r"(\d{2})\s*g\b", t)
    return m.group(1) + "G" if m else ""


def length(t):
    # prefer 'NNmm'; else the thread length in cm (slugs drop the decimal, e.g. 316cm -> 31.6cm, so /10 when >40)
    mms = [int(x) for x in re.findall(r"(\d{2,3})\s*mm", t)]
    if mms: return f"{max(mms)}MM"
    cms = [float(x) for x in re.findall(r"(\d{1,3}(?:\.\d)?)\s*cm", t)]
    cms = [c / 10 if c > 40 else c for c in cms]
    if cms: return f"{max(cms):g}CM"
    return ""


def pack(title, pid):
    for src, t in (("title", title.lower()), ("page", page_text(pid).lower())):
        m = (re.search(r"\(?\b(\d{1,3})\s*(?:pcs|pc|threads|sutures|units)\b", t) or re.search(r"\bx\s*(\d{1,3})\b", t)
             or re.search(r"pack of\s*(\d{1,3})", t) or re.search(r"\((\d{1,3})\s*[x×]\s*\d", t) or re.search(r"\((\d{1,3})\s*packs", t))
        if m: return int(m.group(1)), f"pack from {src}"
    o = image_text(pid).lower(); m = re.search(r"\b(\d{1,3})\s*(?:pcs|threads)\b", o)
    if m: return int(m.group(1)), "pack from image"
    return 1, "pack not stated - assumed 1 (owner rule)"


def delivery(t):
    if re.search(r"without needle|no needle", t): return "no-needle"
    if re.search(r"cannula|l-?cannula|hiko|blunt", t): return "cannula"
    if re.search(r"needle|sharp|\(n\)", t): return "needle"
    return ""


def main():
    rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8"))
            if r["category"] == "PDO threads" and r["scope"] == "Phase 1"]
    maps, prods = [], {}
    for r in rows:
        title = r["title"] if not r["title"].isdigit() else (r["page_title"] or r["title"])
        tl = title.lower()
        # bundles and actual training courses only (not the "training required/recommended" note on real products)
        if re.search(r"^\s*buy\b|\bbundle\b|training (course|kit|package|day)|\bmasterclass\b", tl):
            maps.append(dict(r, code="", brand="", group="", decision="bundle / training course - review", confidence="review")); continue
        info = next((i for rx, i in BRANDS if re.search(rx, tl)), None)
        if not info:
            maps.append(dict(r, code="", brand="", group="", decision="not recognised as a thread - review", confidence="review")); continue
        canon, material, mah, verified = info
        if re.search(r"\bpcl\b", tl): material = "PCL"
        typ = next((name for name, rx in TYPES if re.search(rx, tl)), "mono")
        g, ln, pk_dl = gauge(tl), length(tl), delivery(tl)
        pk, how = pack(title, r["id"])
        grp = f"{material} {typ}"
        parts = [re.sub(r"[^A-Z0-9]+", "", canon.upper()), typ.split("/")[0].upper()] + ([g] if g else []) + ([ln] if ln else []) + ([pk_dl.upper()[:3]] if pk_dl else []) + [f"{pk}PCS"]
        c = "-".join(parts)
        sized = bool(g or ln or typ == "cone")  # gauge, length, or a cone product (cones have no gauge)
        if sized and "not stated" not in how: conf = "high"
        elif sized: conf = "rule"  # size known, pack defaulted to owner rule
        else: conf = "partial - check size/pack"
        maps.append(dict(r, code=c, brand=canon, group=grp,
                         decision=f"{material} {typ}; {g} {ln} {pk_dl}; {how}".replace("  ", " ").strip(), confidence=conf))
        prods.setdefault(c, dict(code=c, brand=canon, material=material, thread_type=typ, equivalence_group=grp, manufacturer=mah,
                                 gauge=g, length=ln, delivery=pk_dl, pcs_per_pack=pk, brand_verified="yes" if verified else "NO - confirm",
                                 suppliers=set(), listings=0))
        prods[c]["suppliers"].add(r["supplier"]); prods[c]["listings"] += 1
    for p in prods.values(): p["suppliers"] = len(p["suppliers"])
    out = ROOT / "catalogue/final"; out.mkdir(parents=True, exist_ok=True)
    pc = ["code", "brand", "material", "thread_type", "equivalence_group", "manufacturer", "gauge", "length", "delivery", "pcs_per_pack", "brand_verified", "suppliers", "listings"]
    with open(out / "thread_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc); w.writeheader(); w.writerows(sorted(prods.values(), key=lambda p: (p["equivalence_group"], p["brand"], p["code"])))
    with open(out / "thread_listing_map.csv", "w", newline="", encoding="utf-8") as f:
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
    grp = collections.Counter(m["group"] for m in maps if m["code"])
    for t, b in [("Category 4 - PDO / lifting threads: catalogue", True),
                 (f"{len(prods)} product codes, {len(maps)} listings. Threads match on brand + material + type + gauge + length + needle/cannula + pack.", False),
                 (f"Confidence: high {cnt['high']}, rule {cnt.get('rule', 0)} (size known, pack defaulted), partial {cnt.get('partial - check size/pack', 0)} (no gauge/length/cone found). Manufacturer unverified for some niche brands (material is in the listing name).", False),
                 ("Equivalence group = material + thread type (mono = skin quality, screw/twist = volume, cog/barbed = lifting, cone = suspension).", False),
                 ("Most thread brands here are single-supplier -> list only (no price comparison). Compare only identical brand+type+gauge+length+pack.", False),
                 ("Sheets: Products | Listings | Review.", True)]:
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=12 if b else 10, bold=b)
    rd.column_dimensions["A"].width = 150
    gp = wb.create_sheet("Groups", 1)
    head(gp, ["Equivalence group", "Listings", "Codes"], [34, 10, 10])
    for g, n in sorted(grp.items()):
        gp.append([g, n, sum(1 for p in prods.values() if p["equivalence_group"] == g)]); fmt(gp)
    ps = wb.create_sheet("Products")
    head(ps, ["Code", "Brand", "Material", "Type", "Equivalence group", "Manufacturer", "Gauge", "Length", "Needle/cannula", "Pcs/pack", "Brand verified", "Suppliers", "Listings"],
         [34, 16, 10, 12, 24, 18, 7, 8, 12, 8, 12, 9, 8])
    for p in sorted(prods.values(), key=lambda p: (p["equivalence_group"], p["brand"], p["gauge"], p["length"])):
        ps.append([p[k] for k in pc]); fmt(ps)
        if p["brand_verified"].startswith("NO"): ps.cell(row=ps.max_row, column=11).fill = PatternFill("solid", fgColor="FFF2CC")
    ls = wb.create_sheet("Listings")
    head(ls, ["Code", "Brand", "Equivalence group", "Supplier", "Listing (link)", "Confidence", "How decided", "OK?"], [34, 16, 24, 16, 52, 14, 40, 7])
    FILL = {"high": "C6EFCE", "high*": "E2EFDA", "rule": "DDEBF7", "partial - check size/pack": "FFF2CC", "review": "F8CBAD"}
    for m in sorted([m for m in maps if m["code"]], key=lambda m: (m["group"], m["brand"], m["code"], m["supplier"])):
        ls.append([m["code"], m["brand"], m["group"], m["supplier"], m["title"], m["confidence"], m["decision"], ""]); fmt(ls); link(ls, 5, m["url"])
        ls.cell(row=ls.max_row, column=6).fill = PatternFill("solid", fgColor=FILL.get(m["confidence"], "FFFFFF"))
    ls.auto_filter.ref = f"A1:H{ls.max_row}"
    rv = wb.create_sheet("Review")
    head(rv, ["Supplier", "Listing (link)", "Why no code"], [18, 62, 40])
    for m in [m for m in maps if not m["code"]]:
        rv.append([m["supplier"], m["title"], m["decision"]]); fmt(rv); link(rv, 2, m["url"])
    p = ROOT / "output/category_04_threads.xlsx"; wb.save(p); print(p)
    print(len(prods), "codes |", dict(cnt), "| groups", dict(grp))
    for m in maps:
        if not m["code"]: print("  REVIEW", m["supplier"], "|", m["title"][:55], "|", m["decision"])


if __name__ == "__main__":
    main()
