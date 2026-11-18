"""Category 6 - Dermal fillers (HA): catalogue + listing map.
Reference below gives each major brand's manufacturer, HA, and official source (Teoxane/Juvederm/Restylane IFUs, emc).
Per listing the line / volume / lidocaine / pack / market variant are read from the title, then the page, then the image
(page_facts, owner rules). Code = BRAND-LINE-[VOLUME]-[LIDO]-PACK[-MARKET]. Equivalence group = brand + line (same
product); market/lidocaine variants share the group and are shown together (owner rules 2026-11-18).
Outputs: catalogue/final/filler_products.csv, filler_listing_map.csv, output/category_06_filler.xlsx
Usage: python -I scripts/filler_catalogue.py"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_facts import page_text, image_text
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent

# brand regex (specific/longer first) -> (canonical, manufacturer, source, verified)
BRANDS = [
 (r"teosyal|teoxane", ("Teosyal", "Teoxane", "https://www.teoxane.com/en/dermal-fillers-ifus", True)),
 (r"juv[eé]derm|juvederm|skinvive|volbella|volift|voluma|volux|volite", ("Juvederm", "Allergan / AbbVie", "https://www.juvederm.co.uk", True)),
 (r"restylane", ("Restylane", "Galderma", "https://www.galderma.com", True)),
 (r"belotero", ("Belotero", "Merz", "https://www.merzaesthetics.com", True)),
 (r"stylage", ("Stylage", "Vivacy", "manufacturer IFU", True)),
 (r"revolax", ("Revolax", "Across (Korea)", "manufacturer IFU", True)),
 (r"aliaxin", ("Aliaxin", "IBSA", "https://www.ibsaderma.com", True)),
 (r"saypha", ("Saypha", "Croma", "https://www.croma.at", True)),
 (r"princess\b", ("Princess", "Croma", "https://www.croma.at", True)),
 (r"regenovue", ("Regenovue", "Dongbang Medical (Korea)", "manufacturer IFU", False)),
 (r"neauvia", ("Neauvia", "Matex Lab", "manufacturer IFU", True)),
 (r"revanesse", ("Revanesse", "Prollenium (Canada)", "manufacturer IFU", True)),
 (r"\bmaili\b", ("Maili", "Sinclair", "manufacturer IFU", True)),
 (r"bellast", ("Bellast", "not named", "supplier page", False)),
 (r"monalisa|mona lisa", ("MonaLisa", "Genoss (Korea)", "manufacturer IFU", False)),
 (r"perfectha", ("Perfectha", "Sinclair", "manufacturer IFU", True)),
 (r"\be\.?p\.?t\.?q\b|eptq|epitique", ("EPTQ", "Jetema (Korea)", "manufacturer IFU", False)),
 (r"fillmed|filorga", ("Fillmed", "Fillmed (Filorga)", "manufacturer IFU", True)),
 (r"intraline", ("Intraline", "Intraline", "manufacturer IFU", False)),
 (r"\belasty\b", ("Elasty", "Dong Kook (Korea)", "manufacturer IFU", False)),
 (r"hyacorp", ("HYAcorp", "BioScience", "manufacturer IFU", False)),
 (r"neuramis", ("Neuramis", "Medytox (Korea)", "manufacturer IFU", False)),
 (r"desirial", ("Desirial", "Vivacy", "manufacturer IFU", True)),
 (r"genefill", ("Genefill", "BioPlus (Korea)", "manufacturer IFU", False)),
 (r"revofil", ("Revofil", "Dexlevo (Korea)", "manufacturer IFU", False)),
 (r"nexfill", ("Nexfill", "not named", "supplier page", False)),
 (r"kairax", ("Kairax", "not named", "supplier page", False)),
 (r"kysense", ("Kysense", "not named", "supplier page", False)),
 (r"luxfill", ("LuxFill", "not named", "supplier page", False)),
 (r"volifil", ("Volifil", "not named", "supplier page", False)),
 (r"starfill", ("Starfill", "not named", "supplier page", False)),
 (r"skinfill", ("Skinfill", "not named", "supplier page", False)),
 (r"aessoa", ("Aessoa", "not named", "supplier page", False)),
 (r"teofil", ("Teofil", "not named", "supplier page", False)),
 (r"kiara", ("Kiara", "not named", "supplier page", False)),
 (r"lumi ?fil", ("Lumifil", "not named", "supplier page", False)),
 (r"\billuma\b", ("iLLUMA", "not named", "supplier page", False)),
 (r"ouye", ("Ouye", "not named", "supplier page", False)),
 (r"hyalmass", ("Hyalmass", "not named", "supplier page", False)),
 (r"lapiena", ("Lapiena", "not named", "supplier page", False)),
 (r"hydrotom|\bliztop\b|cleviel|yvoire|dermalax|sofiderm|hyalax|algeness|sardenya", ("(various HA)", "varies", "supplier page", False)),
]
# canonical line sets for the major brands - the parsed line is snapped to the longest matching known line
LINES = {
 "Juvederm": ["Ultra 2", "Ultra 3", "Ultra 4", "Ultra Smile", "Volbella", "Volift Retouch", "Volift", "Voluma", "Volux", "Volite", "Skinvive"],
 "Restylane": ["Classic", "Defyne", "Refyne", "Kysse", "Lyft", "Volyme", "Fynesse", "Eyelight", "Skinboosters Vital Light", "Skinboosters Vital", "Vital Light", "Vital"],
 "Belotero": ["Balance", "Intense", "Volume", "Soft", "Revive", "Lips Contour", "Lips Shape", "Contour"],
 "Teosyal": ["RHA 1", "RHA 2", "RHA 3", "RHA 4", "RHA Kiss Volume", "RHA Kiss", "Puresense Redensity 1", "Puresense Redensity 2",
             "Puresense Ultra Deep", "Puresense Deep Lines", "Puresense Kiss", "Puresense Global Action", "Puresense Ultimate",
             "Puresense Touch Up", "Redensity 1", "Redensity 2", "Kiss", "Ultra Deep", "Deep Lines", "Global Action", "Ultimate"],
 "Stylage": ["Bi Soft S", "Bi Soft M", "Bi Soft L", "Special Lips", "Lips Plus", "Hydromax", "Hydro", "XXL", "XL", "S", "M", "L"],
 "Revolax": ["Deep", "Fine", "Sub-Q"],
 "Aliaxin": ["Ev Essential Volume", "Fl Lips Fine", "Gp Global Performance", "Lv Lip Volume", "Sr", "Sv Superior Volume", "Ev", "Fl", "Gp", "Lv"],
 "Saypha": ["Volume Plus", "Volume", "Rich", "Lips"],
}
LINES = {b: sorted(v, key=len, reverse=True) for b, v in LINES.items()}
# normalise a parsed line: drop the retail noise
NOISE = re.compile(r"\b(with|without|lidocaine|lido|inj\.?|injection|stock item|vat payable|prescription item|zero vat|on prescription|"
                   r"exp\.?\w*|expiry|short dated|limited stock|training\w*|recommended|single|twin|pack|box|syringe|dermal filler|"
                   r"clone|by allergan|allergan|large volume|non-?lidocaine|next generation|premium|dated|"
                   r"\d+x\d*\.?\d*ml|\d+\s*x|\(.*?\)|\d+(?:\.\d+)?\s*(?:ml|mg|mg[-/]ml)|\d+g\b|uk|roi|hologram|non fixed needle|pre-?filled)\b", re.I)
MARKET = [("ROI", r"\broi\b|ireland"), ("hologram", r"hologram")]


def snap_line(canon, line):
    known = LINES.get(canon)
    if not known: return line
    low = " " + line.lower() + " "
    low = re.sub(r"\brha\s*(\d)", r"rha \1", low)
    low = re.sub(r"\bredensity\s+one\b", "redensity 1", low); low = re.sub(r"\bredensity\s+two\b", "redensity 2", low)
    low = re.sub(r"\bredensity\s+ii\b", "redensity 2", low); low = re.sub(r"\bredensity\s+i\b", "redensity 1", low)
    low = low.replace("ultradeep", "ultra deep")
    if canon == "Juvederm":
        low = low.replace(" smile ", " ultra smile ").replace(" retouch ", " volift retouch ")
    for k in known:
        if re.search(r"\b" + re.escape(k.lower()) + r"\b", low): return k
    if canon == "Restylane" and not line.strip(): return "Classic"  # base Restylane = Restylane Classic
    return line


def facts(title, pid):
    t = title.lower(); page = page_text(pid).lower()
    full = t + " || " + page[:400]
    vm = re.search(r"(\d(?:\.\d+)?)\s*ml", t) or re.search(r"(\d(?:\.\d+)?)\s*ml", page[:300])
    vol = vm.group(1) if vm else ""
    VOLS = [0.3, 0.55, 0.8, 1.0, 1.1, 1.2, 2.0]  # fix slug-dropped decimals, e.g. "11ml" -> 1.1
    if vol and "." not in vol:
        fv = float(vol)
        if fv not in VOLS and round(fv / 10, 2) in VOLS: vol = f"{fv / 10:g}"
    lido = bool(re.search(r"lido|lidocaine|\+ ?l\b|with l\b", t)) or ("with lidocaine" in page[:300]) or bool(re.search(r"\bl\b\s*\(", t))
    pk, how = None, ""
    for src, txt in (("title", t), ("page", page[:400])):
        m = re.search(r"\b(\d)\s*x\s*\d|\b(\d)\s*(?:syringes?|x\s*\d*\.?\d*\s*ml)|\btwin\b|\bduo\b|\bsingle\b|\(2 x|2x1", txt)
        if m:
            g = next((x for x in m.groups() if x), None)
            pk = int(g) if g else (2 if re.search(r"twin|duo", m.group(0)) else 1)
            how = f"pack from {src}"; break
    if pk is None: pk, how = 1, "pack not stated - assumed 1 syringe (owner rule)"
    return vol, lido, pk, how


# what to strip to expose the line (only the core brand word - not the line names some detection regexes include)
STRIP = {"Juvederm": r"juv[eé]derm", "Teosyal": r"teosyal|teoxane", "Princess": r"princess",
         "MonaLisa": r"monalisa|mona lisa", "HYAcorp": r"hyacorp"}


def line_of(title, brand_rx, canon):
    t = re.sub(r"\s+", " ", title).strip()
    t = re.sub(STRIP.get(canon, re.escape(canon)), "", t, flags=re.I)  # remove only the brand word
    t = NOISE.sub(" ", t)
    t = re.sub(r"[^\w+./ -]", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" -+.")
    # keep it short (first 4 tokens)
    toks = [x for x in t.split() if x.lower() not in ("the", "ml", "x", "and", "for")][:4]
    ln = " ".join(toks).title()
    return ln


def main():
    rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8"))
            if r["category"] == "Dermal filler" and r["scope"] == "Phase 1"]
    maps, prods = [], {}
    for r in rows:
        title = r["title"] if not r["title"].isdigit() else (r["page_title"] or r["title"])
        tl = title.lower()
        if re.search(r"^\s*buy\b|\bbundle\b|mix and match|\bget 1|training (course|kit|day|package)", tl):
            maps.append(dict(r, code="", brand="", line="", group="", decision="bundle / training course", confidence="review")); continue
        info = brx = None
        for rx, i in BRANDS:
            if re.search(rx, tl): info, brx = i, rx; break
        if not info:
            # long-tail / niche brand: take the first 1-2 words as the brand so it is still listed (list-everything principle)
            w = re.sub(r"[^\w ]", " ", re.sub(r"^(the|new|buy)\s+", "", tl)).split()
            bw = w[:2] if (len(w) > 1 and len(w[0]) <= 4 and not re.match(r"\d", w[1])) else w[:1]
            if not bw:
                maps.append(dict(r, code="", brand="", line="", group="", decision="no brand text - review", confidence="review")); continue
            bname = " ".join(bw).title()
            info, brx = (bname, "not named", "supplier page", False), r"^" + re.escape(" ".join(bw))
        canon, mah, src, verified = info
        line = snap_line(canon, line_of(title, brx, canon))
        vol, lido, pk, how = facts(title, r["id"])
        market = next((m for m, rx in MARKET if re.search(rx, tl)), "")
        grp = f"{canon} {line}".strip()
        parts = [re.sub(r"[^A-Z0-9]+", "", canon.upper())] + ([re.sub(r"[^A-Z0-9]+", "", line.upper())] if line else []) \
            + ([vol.replace(".", "") + "ML"] if vol else []) + (["LIDO"] if lido else []) + [f"{pk}X"] + ([market.upper()] if market else [])
        c = "-".join(p for p in parts if p)
        conf = "high" if (line and vol and "not stated" not in how) else ("rule" if line else "partial - check line/size")
        if not verified and conf == "high": conf = "high*"
        maps.append(dict(r, code=c, brand=canon, line=line, group=grp,
                         decision=f"{line}; {vol or '?'}ml; {'+lido' if lido else 'no lido'}; {how}" + ("" if verified else "; brand page only"),
                         confidence=conf))
        prods.setdefault(c, dict(code=c, brand=canon, line=line, equivalence_group=grp, manufacturer=mah, ha="yes",
                                 volume_ml=vol, lidocaine="yes" if lido else "no", syringes_per_pack=pk, market=market or "UK/std",
                                 source=src, brand_verified="yes" if verified else "brand page only", suppliers=set(), listings=0))
        prods[c]["suppliers"].add(r["supplier"]); prods[c]["listings"] += 1
    for p in prods.values(): p["suppliers"] = len(p["suppliers"])
    out = ROOT / "catalogue/final"; out.mkdir(parents=True, exist_ok=True)
    pc = ["code", "brand", "line", "equivalence_group", "manufacturer", "ha", "volume_ml", "lidocaine", "syringes_per_pack", "market", "brand_verified", "suppliers", "listings", "source"]
    with open(out / "filler_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc); w.writeheader(); w.writerows(sorted(prods.values(), key=lambda p: (p["brand"], p["line"], p["code"])))
    with open(out / "filler_listing_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "supplier", "title", "url", "brand", "line", "group", "code", "confidence", "decision", "page_status"], extrasaction="ignore")
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
        if url and url.startswith("http"):
            c = ws.cell(row=ws.max_row, column=col); c.hyperlink = url; c.font = Font(name=F, size=9, color="0563C1", underline="single")
    wb = Workbook(); rd = wb.active; rd.title = "Read me"
    cnt = collections.Counter(m["confidence"] for m in maps)
    for t, b in [("Category 6 - Dermal fillers (HA): catalogue", True),
                 (f"{len(prods)} product codes, {len(maps)} listings. high {cnt['high']}, high* {cnt['high*']} (brand page only), rule {cnt['rule']}, partial {cnt['partial - check line/size']}, review {cnt['review']}.", False),
                 ("Equivalence group = brand + line (the specific product, e.g. 'Juvederm Voluma'). Lidocaine and market (UK/ROI/hologram) variants share the group.", False),
                 ("Code = BRAND-LINE-VOLUME-[LIDO]-PACK[-MARKET]. Lines parsed from the listing then cleaned; check the Listings sheet. Most big brands are multi-supplier (comparable).", False),
                 ("Sheets: By brand | Products | Listings | Review.", True)]:
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=12 if b else 10, bold=b)
    rd.column_dimensions["A"].width = 150
    bb = wb.create_sheet("By brand", 1)
    head(bb, ["Brand", "Lines", "Codes", "Listings", "Suppliers (max)"], [20, 8, 8, 9, 12])
    byb = collections.defaultdict(list)
    for p in prods.values(): byb[p["brand"]].append(p)
    for brand, ps in sorted(byb.items(), key=lambda kv: -sum(x["listings"] for x in kv[1])):
        bb.append([brand, len({x["line"] for x in ps}), len(ps), sum(x["listings"] for x in ps), max(x["suppliers"] for x in ps)]); fmt(bb)
    ps_ws = wb.create_sheet("Products")
    head(ps_ws, ["Code", "Brand", "Line", "Equivalence group", "Manufacturer", "Volume ml", "Lidocaine", "Syringes/pack", "Market", "Brand verified", "Suppliers", "Listings", "Source"],
         [34, 14, 20, 26, 20, 8, 9, 8, 10, 14, 9, 8, 14])
    for p in sorted(prods.values(), key=lambda p: (p["brand"], p["line"], p["code"])):
        ps_ws.append([p[k] for k in pc if k != "ha"]); fmt(ps_ws); link(ps_ws, 13, p["source"])
        if p["brand_verified"] != "yes": ps_ws.cell(row=ps_ws.max_row, column=10).fill = PatternFill("solid", fgColor="FFF2CC")
    ls = wb.create_sheet("Listings")
    head(ls, ["Code", "Brand", "Line", "Supplier", "Listing (link)", "Confidence", "How decided", "OK?"], [34, 14, 18, 16, 50, 14, 40, 7])
    FILL = {"high": "C6EFCE", "high*": "E2EFDA", "rule": "DDEBF7", "partial - check line/size": "FFF2CC", "review": "F8CBAD"}
    for m in sorted([m for m in maps if m["code"]], key=lambda m: (m["brand"], m["line"], m["code"], m["supplier"])):
        ls.append([m["code"], m["brand"], m["line"], m["supplier"], m["title"], m["confidence"], m["decision"], ""]); fmt(ls); link(ls, 5, m["url"])
        ls.cell(row=ls.max_row, column=6).fill = PatternFill("solid", fgColor=FILL.get(m["confidence"], "FFFFFF"))
    ls.auto_filter.ref = f"A1:H{ls.max_row}"
    rv = wb.create_sheet("Review")
    head(rv, ["Supplier", "Listing (link)", "Why no code"], [18, 62, 40])
    for m in [m for m in maps if not m["code"]]:
        rv.append([m["supplier"], m["title"], m["decision"]]); fmt(rv); link(rv, 2, m["url"])
    p = ROOT / "output/category_06_filler.xlsx"; wb.save(p); print(p)
    print(len(prods), "codes |", dict(cnt))
    print("top brands:", ", ".join(f"{b}({sum(x['listings'] for x in ps)})" for b, ps in sorted(byb.items(), key=lambda kv: -sum(x['listings'] for x in kv[1]))[:12]))
    rev = [m for m in maps if not m["code"] and "bundle" not in m["decision"]]
    print("non-bundle review:", len(rev))
    for m in rev[:20]: print("  ", m["supplier"], "|", m["title"][:55])


if __name__ == "__main__":
    main()
