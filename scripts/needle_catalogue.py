"""Category 10 - Needles, cannulas & syringes (consumables): catalogue + listing map.
These are commodity consumables, so per the owner rule (same spec, different manufacturer -> ONE code, manufacturer an
attribute/filter) the code is SPEC-based: subtype + gauge + length (needle/cannula) or volume + luer (syringe) + pack.
Brand is recorded as a filterable attribute and every brand seen for a code is listed, so a 30G 13mm needle from BD,
Terumo, etc. compares together. Equivalence group = subtype. Specs read from title then page (page_facts).
Code = SUBTYPE-[GAUGE]-[LENGTH]-[VOLUME]-[LUER]-PACK.
Outputs: catalogue/final/needle_products.csv, needle_listing_map.csv, output/category_10_needles.xlsx
Usage: python -I scripts/needle_catalogue.py"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from droplist import dropped
from page_facts import page_text
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent

# subtype by keyword (ordered)
SUBTYPES = [
 ("Needle holder / tool", r"needle holder|holder\b|needle disposal|mixing tube|syringe sleeve|air/water syringe|disposa-?shield|pro-?tip sleeve"),
 ("Sharps bin", r"sharps\b|sharps bin|sharps container|disposal bin"),
 ("Electrolysis needle", r"electrolysis|one\s*-?piece needle|two\s*-?piece needle|sterex|\bf\d{1,2}[sg]\b"),
 ("Microneedling cartridge", r"cartridge|needle module|\bpin\b|rmt\b|\b1need|edermastamp|gentlo|microneedle|micro-?needle|nano\s*needle|dermapen"),
 ("Filter needle", r"filter needle|filter-needle|blunt fill|filtra"),
 ("Dental needle", r"dental needle|dental\b.*needle"),
 ("Microcannula", r"cannula|micro-?cannula|blunt|steriglide|softfil|silkann|silk ann|magicalift|nanosoft|intralipo|pix'?l|dermasculpt"),
 ("Insulin syringe", r"insulin syringe|u-?100 syringe|insulin\b"),
 ("Syringe", r"syringe|plastipak|omnifix|unifix|luer slip syringe|luer lock syringe|\bbd emerald\b|injekt"),
 ("Hypodermic needle", r"needle|hypodermic|microlance|sterican|novofine|microfine|micro-?fine|unisharp|drawing up"),
 ("Luer adapter / connector", r"luer\b.*(adapter|connector|cap|combi)|combi-?stopper|stopcock"),
]
# brand -> default subtype hint when the word is missing
BRAND_SUB = {
 "steriglide": "Microcannula", "softfil": "Microcannula", "silkann": "Microcannula", "silk": "Microcannula",
 "magicalift": "Microcannula", "fms": "Microcannula", "fmc": "Microcannula", "nanosoft": "Microcannula",
 "intraliponeedle": "Microcannula", "steriject": "Microcannula", "tsk": "Microcannula", "mint": "Microcannula",
 "microlance": "Hypodermic needle", "sterican": "Hypodermic needle", "novofine": "Hypodermic needle",
 "microfineu100": "Insulin syringe", "unisharp": "Hypodermic needle", "sterex": "Hypodermic needle",
 "plastipak": "Syringe", "omnifix": "Syringe", "unifix": "Syringe", "omnican": "Syringe", "injekt": "Syringe",
}
# canonical brand map
BRANDS = [
 (r"\bbd\b|microlance|plastipak|emerald|embecta|microfine", "BD"), (r"\btsk\b|steriglide|invisible needle", "TSK"),
 (r"\bfms\b", "FMS"), (r"\bfmc\b", "FMC"), (r"terumo", "Terumo"), (r"\bjbp\b|nanosoft", "JBP (Nanosoft)"),
 (r"unisharp", "Unisharp"), (r"silkann|silk ann", "SilkAnn"), (r"magicalift", "Magicalift"),
 (r"softfil", "SoftFil"), (r"sterican|\bbraun|omnifix|omnican|injekt", "B. Braun"), (r"sterex", "Sterex"),
 (r"novofine|novotwist", "Novo Nordisk"), (r"glucorx", "GlucoRx"), (r"fillmed", "Fillmed"),
 (r"potenza", "Potenza"), (r"steriject", "Steriject"), (r"needleflex", "Needleflex"), (r"dermaqual", "Dermaqual"),
 (r"mint\b", "MINT"), (r"intralipo", "IntraLipo"),
]
LUER = [("luer lock", r"luer\s*-?\s*lock|\bll\b"), ("luer slip", r"luer\s*-?\s*slip|luer\s*-?\s*slide|\bls\b")]


def subtype(t):
    for name, rx in SUBTYPES:
        if re.search(rx, t, re.I): return name
    w = re.sub(r"[^a-z0-9]", "", t.lower().split()[0]) if t.split() else ""
    return BRAND_SUB.get(w, "")


def brand_of(t):
    for rx, b in BRANDS:
        if re.search(rx, t, re.I): return b
    w = re.sub(r"[^A-Za-z0-9]", "", t.split()[0]) if t.split() else ""
    return w.upper() if len(w) <= 4 else w.title()


def gauge(t):
    m = re.search(r"\b(\d{2})\s*G\b", t) or re.search(r"\b(\d{2})\s*g\b", t) or re.search(r"\b(\d{2})\s*gauge", t, re.I)
    if m and 18 <= int(m.group(1)) <= 34: return m.group(1) + "G"
    return ""


def length(t):
    for m in re.finditer(r"(\d{1,3})\s*mm\b", t, re.I):
        v = int(m.group(1))
        if 4 <= v <= 120: return str(v) + "mm"
    m = re.search(r'(\d(?:\.\d)?)\s*(?:inch|")', t)
    if m: return str(round(float(m.group(1)) * 25.4)) + "mm"
    return ""


def volume(t):
    m = re.search(r"(\d+(?:\.\d+)?)\s*ml\b", t, re.I)
    return m.group(1).rstrip(".") + "ml" if m else ""


def luer_of(t):
    for name, rx in LUER:
        if re.search(rx, t, re.I): return name
    return ""


def pack(t):
    m = (re.search(r"(?:box|pack|bag)\s*of\s*(\d+)", t, re.I) or re.search(r"\b(\d+)\s*(?:per box|/box|pcs|pieces)\b", t, re.I)
         or re.search(r"\bx\s*(\d+)\b", t, re.I) or re.search(r"\b(\d+)\s*(?:needles?|cannulas?|syringes?)\b", t, re.I))
    return int(m.group(1)) if m else 1


def slug(*p):
    s = "-".join(x for x in p if x)
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9.]+", "-", s).strip("-")).upper()


def main():
    rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8"))
            if r["category"] == "Needles, cannulas & syringes" and r["scope"] == "Phase 1" and r["id"] not in dropped()]
    maps, prods = [], {}
    for r in rows:
        title = r["title"] if not r["title"].isdigit() else (r["page_title"] or r["title"])
        if not title.strip():
            maps.append(dict(r, code="", sub="", brand="", decision="no title", confidence="review")); continue
        sub = subtype(title)
        brand = brand_of(title)
        g, ln, vol, luer, pk = gauge(title), length(title), volume(title), luer_of(title), pack(title)
        if (not sub) or ((sub in ("Hypodermic needle", "Microcannula")) and not g) or (sub == "Syringe" and not vol):
            pg = page_text(r["id"])[:500]
            sub = sub or subtype(pg)
            g = g or gauge(pg); ln = ln or length(pg); vol = vol or volume(pg); luer = luer or luer_of(pg)
        sub = sub or "Consumable (other)"
        if sub in ("Syringe", "Insulin syringe"):
            spec = [vol, luer]
        else:
            spec = [g, ln]
        has_spec = any(spec)
        # no spec parsed -> add a brand token so genuinely different items don't collapse into one meaningless code
        btok = re.sub(r"[^A-Z0-9]", "", brand.upper())[:8] if not has_spec else ""
        code = slug(re.sub(r"[^A-Z]", "", sub.upper())[:6] or "CONS", *spec, btok, f"X{pk}" if pk > 1 else "")
        key_spec = " ".join(x for x in spec if x) or "(no spec)"
        conf = "high" if (sub and (g or vol)) else ("rule" if sub else "partial")
        maps.append(dict(r, code=code, sub=sub, brand=brand,
                         decision=f"{sub}; {key_spec}; pack {pk}; brand {brand}", confidence=conf))
        p = prods.setdefault(code, dict(code=code, subtype=sub, gauge=g, length=ln, volume=vol, luer=luer,
                                        pack=pk, spec=key_spec, brands=set(), suppliers=set(), listings=0))
        p["brands"].add(brand); p["suppliers"].add(r["supplier"]); p["listings"] += 1
    for p in prods.values():
        p["supplier_n"] = len(p["suppliers"]); p["brand_n"] = len(p["brands"])
        p["brands"] = "; ".join(sorted(b for b in p["brands"] if b)); p["suppliers"] = len(p["suppliers"])
    out = ROOT / "catalogue/final"; out.mkdir(parents=True, exist_ok=True)
    pc = ["code", "subtype", "gauge", "length", "volume", "luer", "pack", "brands", "supplier_n", "listings"]
    with open(out / "needle_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc, extrasaction="ignore"); w.writeheader()
        w.writerows(sorted(prods.values(), key=lambda p: (p["subtype"], p["gauge"], p["code"])))
    with open(out / "needle_listing_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "supplier", "title", "url", "sub", "brand", "code", "confidence", "decision"], extrasaction="ignore")
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
    bysub = collections.Counter(p["subtype"] for p in prods.values())
    multi = sum(1 for p in prods.values() if p["supplier_n"] > 1)
    for t, b in [("Category 10 - Needles, cannulas & syringes", True),
                 (f"{len(prods)} spec codes from {len(maps)} listings across {len(set(m['supplier'] for m in maps))} suppliers.", False),
                 ("These are commodity consumables, so the code is the SPEC (subtype + gauge + length, or volume + luer for "
                  "syringes) and the brand is a filterable attribute - same spec from any manufacturer compares together "
                  "(owner rule: same spec, different manufacturer -> one code). Every brand seen is listed per code.", False),
                 (f"{multi} spec codes are stocked by more than one supplier (compare on price-per-unit).", False),
                 ("Subtypes: " + ", ".join(f"{k} ({v})" for k, v in bysub.most_common()), False),
                 (f"Confidence: high {cnt['high']}, rule {cnt['rule']}, partial {cnt['partial']}, review {cnt['review']}. "
                  "Sheets: By subtype | Products | Listings | Review.", True)]:
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=12 if b else 10, bold=b)
    rd.column_dimensions["A"].width = 150

    ss = wb.create_sheet("By subtype")
    head(ss, ["Subtype", "Codes", "Listings", "Brands"], [26, 9, 10, 90])
    agg = collections.defaultdict(lambda: [0, 0, set()])
    for p in prods.values():
        a = agg[p["subtype"]]; a[0] += 1; a[1] += p["listings"]; a[2].update(b for b in p["brands"].split("; ") if b)
    for sb, _ in bysub.most_common():
        a = agg[sb]; ss.append([sb, a[0], a[1], ", ".join(sorted(a[2]))]); fmt(ss)

    ps = wb.create_sheet("Products")
    head(ps, ["Code", "Subtype", "Gauge", "Length", "Volume", "Luer", "Pack", "Brands (filter)", "Suppliers", "Listings"],
         [26, 20, 8, 9, 8, 10, 6, 40, 9, 8])
    for p in sorted(prods.values(), key=lambda p: (-p["supplier_n"], p["subtype"], p["gauge"], p["code"])):
        ps.append([p[k] for k in pc]); fmt(ps)
    ls = wb.create_sheet("Listings")
    head(ls, ["Code", "Subtype", "Brand", "Supplier", "Listing (link)", "Confidence", "How decided"], [26, 20, 16, 16, 50, 12, 38])
    FILL = {"high": "C6EFCE", "rule": "DDEBF7", "partial": "FFF2CC", "review": "F8CBAD"}
    for m in sorted([m for m in maps if m["code"]], key=lambda m: (m["sub"], m["code"], m["supplier"])):
        ls.append([m["code"], m["sub"], m["brand"], m["supplier"], m["title"], m["confidence"], m["decision"]]); fmt(ls); link(ls, 5, m["url"])
        ls.cell(row=ls.max_row, column=6).fill = PatternFill("solid", fgColor=FILL.get(m["confidence"], "FFFFFF"))
    ls.auto_filter.ref = f"A1:G{ls.max_row}"
    rv = wb.create_sheet("Review")
    head(rv, ["Supplier", "Listing (link)", "Why"], [18, 66, 36])
    for m in [m for m in maps if m["confidence"] in ("review", "partial")]:
        rv.append([m["supplier"], m["title"], m["decision"]]); fmt(rv); link(rv, 2, m["url"])
    p = ROOT / "output/category_10_needles.xlsx"; wb.save(p); print(p)
    print(len(prods), "codes |", dict(cnt), "| multi-supplier:", multi)
    print("subtypes:", dict(bysub))


if __name__ == "__main__":
    main()
