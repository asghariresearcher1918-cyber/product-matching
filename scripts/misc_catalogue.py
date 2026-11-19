"""Categories 13-15 - Beauty (nails/brows/lashes/PMU/makeup), Supplements, Vaccine: catalogues + listing maps.
Small tail categories. Beauty & supplements are branded (identity = brand + name + size; equivalence group = subtype).
Vaccine identity = vaccine + presentation. Mostly list-only; compare where several suppliers share a code.
Outputs: catalogue/final/{beauty,supplement,vaccine}_products.csv + _listing_map.csv,
output/category_13_15_beauty_supplements_vaccine.xlsx    Usage: python -I scripts/misc_catalogue.py"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent

BEAUTY_SUB = [
 ("Lash / brow serum", r"revitalash|revitabrow|lash\b|brow\b|eyelash|eyebrow|lash serum|growth serum"),
 ("PMU / microblading pigment", r"pigment|perma\s*blend|permablend|\bink\b|fade\b|microblading pigment|pmu ink"),
 ("PMU / microblading tool", r"microblading|microblade|pmu machine|tattoo machine|dragonhawk|needle cartridge|pmu|hand tool|blade\b|pen machine"),
 ("Mineral makeup / cosmetics", r"jane iredale|iredale|makeup|foundation|concealer|lipstick|mineral|blush|bronzer|mascara|powder\b|primer|tint"),
 ("Nail care", r"\bnail|cuticle|gel polish|manicure|pedicure"),
 ("Aftercare / numbing", r"aftercare|numbing|balm|healing"),
]
SUP_SUB = [
 ("Collagen", r"collagen|marine collagen|peptan"),
 ("Oral sun protection", r"heliocare|oral sun|sunprotect|fernblock"),
 ("Vitamin C (oral/liposomal)", r"vitamin c|altrient|liposomal c|ascorbic"),
 ("Skin / beauty supplement", r"skin\b|beauty\b|lumi|jalupro|viscoderm|ibsa|hydroly|glow\b|nutri"),
 ("Vitamin / mineral", r"vitamin|mineral|zinc|biotin|omega|electrolyte|multivit"),
]
NOISE = {"the", "with", "for", "and", "buy", "uk", "new", "stock", "item", "vat", "payable", "zero", "prescription",
         "x", "ml", "g", "capsules", "capsule", "tablets", "tablet", "sachets", "pack", "box", "of", "size", "each",
         "supplement", "food", "ltd", "size", "professional", "clinic", "day", "days", "month", "supply"}


def classify(t, rules, default):
    for name, rx in rules:
        if re.search(rx, t, re.I): return name
    return default


def size_of(t):
    m = (re.search(r"(\d+)\s*(?:x\s*)?(?:capsules?|caps?|tablets?|tabs?|sachets?)\b", t, re.I)
         or re.search(r"(\d+(?:\.\d+)?)\s*(ml|g|mg)\b", t, re.I))
    return re.sub(r"\s+", "", m.group(0).lower()) if m else ""


def brand_of(t):
    w = re.sub(r"[^A-Za-z0-9&+ -]", " ", t).split()
    return w[0] if w else ""


def namecore(title, brand):
    t = re.sub(r"[®™©]", " ", title)
    t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"[^A-Za-z0-9 ]", " ", t)
    bw = set(re.sub(r"[^a-z0-9 ]", " ", brand.lower()).split())
    keep = []
    for w in t.split():
        wl = w.lower()
        if wl in bw or wl in NOISE or len(w) <= 1: continue
        if wl in [k.lower() for k in keep]: continue
        keep.append(w)
        if len(keep) >= 5: break
    return " ".join(keep)


def slug(*p):
    s = "-".join(x for x in p if x)
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9.]+", "-", s).strip("-")).upper()


def build(category, rules, default, prefix, canon=None):
    allr = csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8"))
    rows = [r for r in allr if r["category"] == category and r["scope"] == "Phase 1"]
    maps, prods = [], {}
    for r in rows:
        title = r["title"] if not r["title"].isdigit() else (r["page_title"] or r["title"])
        if not title.strip():
            maps.append(dict(r, code="", sub="", brand="", decision="no title", confidence="review")); continue
        tl = title.lower()
        sub = classify(tl, rules, default)
        brand = brand_of(title)
        size = size_of(tl)
        core = namecore(title, brand)
        code = (canon and canon(tl)) or slug(prefix, brand[:16], core[:34], size)
        conf = "high" if core else "rule"
        maps.append(dict(r, code=code, sub=sub, brand=brand, decision=f"{sub}; {brand} {core}; {size or 'size?'}", confidence=conf))
        p = prods.setdefault(code, dict(code=code, subtype=sub, brand=brand, name=core, size=size, suppliers=set(), listings=0))
        p["suppliers"].add(r["supplier"]); p["listings"] += 1
    for p in prods.values():
        p["supplier_n"] = len(p["suppliers"]); p["suppliers"] = len(p["suppliers"])
    key = prefix.lower()
    out = ROOT / "catalogue/final"; out.mkdir(parents=True, exist_ok=True)
    pc = ["code", "subtype", "brand", "name", "size", "supplier_n", "listings"]
    with open(out / f"{key}_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc, extrasaction="ignore"); w.writeheader()
        w.writerows(sorted(prods.values(), key=lambda p: (p["subtype"], p["brand"], p["code"])))
    with open(out / f"{key}_listing_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "supplier", "title", "url", "sub", "brand", "code", "confidence", "decision"], extrasaction="ignore")
        w.writeheader(); w.writerows(maps)
    return prods, maps


def main():
    beauty = build("Beauty (nails, brows, lashes, PMU, makeup)", BEAUTY_SUB, "Beauty (other)", "BTY")
    supp = build("Supplements", SUP_SUB, "Supplement (other)", "SUP")
    def vac_canon(tl):
        if re.search(r"engerix", tl) and re.search(r"adult|20\s*micro|20mcg|20\s*ug", tl):
            return "VAC-ENGERIX-B-ADULT-20MCG-PFS"  # same licensed product; different suppliers -> one code, compare
        return ""
    vacc = build("Vaccine", [("Hepatitis B", r"engerix|hep b|hepatitis b|hbvaxpro"), ("Other vaccine", r".")], "Vaccine", "VAC", canon=vac_canon)

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
    FILL = {"high": "C6EFCE", "rule": "DDEBF7", "review": "F8CBAD"}
    wb = Workbook(); rd = wb.active; rd.title = "Read me"
    def line(txt, sz=10, bold=False):
        rd.append([txt]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=sz, bold=bold)
    line("Categories 13-15 - Beauty, Supplements & Vaccine", 12, True)
    for name, (prods, maps) in [("Beauty (nails/brows/lashes/PMU/makeup)", beauty), ("Supplements", supp), ("Vaccine", vacc)]:
        multi = sum(1 for p in prods.values() if p["supplier_n"] > 1)
        line(f"{name}: {len(prods)} codes from {len(maps)} listings; {multi} multi-supplier.")
    line("Branded; identity = brand + name + size, equivalence group = subtype. Mostly list-only; compare where suppliers share a code.", 10)
    line("Only Engerix B (adult Hep B) was kept as a vaccine per owner decision; others were removed earlier.", 10, True)
    rd.column_dimensions["A"].width = 150

    for name, (prods, maps), subcol in [("Beauty", beauty, "Subtype"), ("Supplements", supp, "Subtype"), ("Vaccine", vacc, "Type")]:
        ps = wb.create_sheet(f"{name} products")
        head(ps, ["Code", subcol, "Brand", "Name", "Size", "Suppliers", "Listings"], [30, 26, 18, 36, 10, 9, 8])
        for p in sorted(prods.values(), key=lambda p: (-p["supplier_n"], p["subtype"], p["brand"])):
            ps.append([p["code"], p["subtype"], p["brand"], p["name"], p["size"], p["supplier_n"], p["listings"]]); fmt(ps)
        ls = wb.create_sheet(f"{name} listings")
        head(ls, ["Code", subcol, "Brand", "Supplier", "Listing (link)", "Confidence", "How decided"], [30, 24, 16, 16, 48, 11, 34])
        for m in sorted([m for m in maps if m["code"]], key=lambda m: (m["sub"], m["code"], m["supplier"])):
            ls.append([m["code"], m["sub"], m["brand"], m["supplier"], m["title"], m["confidence"], m["decision"]]); fmt(ls); link(ls, 5, m["url"])
            ls.cell(row=ls.max_row, column=6).fill = PatternFill("solid", fgColor=FILL.get(m["confidence"], "FFFFFF"))
        ls.auto_filter.ref = f"A1:G{ls.max_row}"
    p = ROOT / "output/category_13_15_beauty_supplements_vaccine.xlsx"; wb.save(p); print(p)
    for name, (prods, maps) in [("Beauty", beauty), ("Supplements", supp), ("Vaccine", vacc)]:
        print(f"{name}: {len(prods)} codes / {len(maps)} listings | subtypes:", dict(collections.Counter(pp['subtype'] for pp in prods.values())))


if __name__ == "__main__":
    main()
