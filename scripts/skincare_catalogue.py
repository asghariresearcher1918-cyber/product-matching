"""Category 9 - Skincare, haircare & peels (cosmeceuticals): catalogue + listing map.
Branded cosmeceuticals - identity = brand + product name + size; they are NOT interchangeable, so the same branded SKU
is matched across suppliers for price comparison, and everything else is listed. The equivalence group is the product
FUNCTION (SPF/sunscreen, chemical peel, retinoid, vitamin C, cleanser, exfoliant/toner, serum, moisturiser, eye, mask,
lip, haircare/scalp, body, other) for browse / filter. Supplier noise (training required, stock/prescription item, VAT,
trial size, new) is stripped so the same product's listings collapse to one code. Size read from title then page.
Code = BRAND-NAMECORE-[SIZE]. Outputs: catalogue/final/skincare_products.csv, skincare_listing_map.csv,
output/category_09_skincare.xlsx   Usage: python -I scripts/skincare_catalogue.py"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_facts import page_text
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent

# canonical brand: regex (longer/specific first) -> display brand
BRANDS = [
 (r"pca skin|^pca\b", "PCA Skin"), (r"medik8", "Medik8"), (r"noon aesthetics|^noon\b", "Noon Aesthetics"),
 (r"neostrata", "NeoStrata"), (r"teoxane|teosyal", "Teoxane"), (r"heliocare", "Heliocare"),
 (r"mesoestetic|mesoéstetic", "Mesoestetic"), (r"obagi", "Obagi"), (r"fillmed|filorga", "Fillmed"),
 (r"neauvia", "Neauvia"), (r"\bwiqo\b", "WiQo"), (r"tebiskin", "Tebiskin"), (r"alastin", "Alastin"),
 (r"dermalogica", "Dermalogica"), (r"cetaphil", "Cetaphil"), (r"epicutis", "Epicutis"),
 (r"theraderm", "Theraderm"), (r"biorepeel", "BioRePeelCl3"), (r"enerpeel", "Enerpeel"), (r"glyderm", "GlyDerm"),
 (r"mediceutic", "Mediceuticals"), (r"cellderma", "Cellderma"), (r"skinceutical", "SkinCeuticals"),
 (r"zo skin|zo medical|^zo\b", "ZO Skin Health"), (r"obaji", "Obagi"), (r"iss clinical|is clinical|isclinical", "iS Clinical"),
 (r"intradermology|intraceutical", "Intraceuticals"), (r"environ", "Environ"), (r"exuviance", "Exuviance"),
 (r"jan marini", "Jan Marini"), (r"image skincare|^image\b", "Image Skincare"), (r"dermaquest", "DermaQuest"),
 (r"dp dermaceutical|dermaceutical", "DP Dermaceuticals"), (r"aftermed", "Aftermed"), (r"kaizen", "Kaizen"),
 (r"allskin|all skin", "AllSkin Med"), (r"\bkanso\b", "Kanso"), (r"\byugen\b", "Yugen"), (r"\bawvi\b", "AWvi"),
 (r"prosystem|pro-system", "pHformula"), (r"\blca\b", "LCA Pharmaceutical"), (r"profhilo", "Profhilo (topical)"),
 (r"viscoderm", "Viscoderm (topical)"), (r"hyalual", "Hyalual (topical)"), (r"croma", "Croma"),
 (r"nouveau", "Nouveau Skin"), (r"cosmopro", "Cosmopro"), (r"exoblanc", "Exoblanc"), (r"nelsons", "Nelsons"),
 (r"cellcosmet|cellmen", "Cellcosmet"), (r"helio", "Heliocare"), (r"definisse", "Definisse (topical)"),
 (r"the ordinary", "The Ordinary"),
]
# product function (ordered; first match wins)
FUNCS = [
 ("Chemical peel", r"\bpeel\b|peeling|tca\b|glycolic peel|enerpeel|biorepeel|mandelic peel|jessner|prx[- ]?t33|cl3"),
 ("Sunscreen / SPF", r"spf\s*\d*|sunscreen|sun screen|\buv[ab]?\b|uva shield|sunblock|photoprotect|mineral tolerance|heliocare"),
 ("Retinoid (vitamin A)", r"retinal|retinol|retinoid|vitamin a\b|crystal retinal|\ba-?retinoate\b"),
 ("Vitamin C", r"vitamin c\b|\bvit c\b|ascorbic|c-tetra|c tetra|ferulic|c25|c15"),
 ("Cleanser / wash", r"cleanser|cleansing|face wash|\bwash\b|foaming|micellar|make-?up remover|press\s*&\s*glow"),
 ("Exfoliant / toner", r"\btoner\b|exfoliant|exfoliating|\baha\b|\bbha\b|\bpha\b|glycolic(?! peel)|salicylic|lactic|resurfac"),
 ("Eye care", r"\beye\b|eye cream|eye serum|eye contour"),
 ("Mask", r"\bmask\b|masque|sheet mask"),
 ("Lip care", r"\blip\b|lip balm"),
 ("Serum / booster", r"serum|booster|ampoule|concentrate|essence|drops\b"),
 ("Moisturiser / cream", r"moistur|\bcream\b|hydrat|emulsion|lotion|balm|emollient|\bgel\b|day cream|night cream"),
 ("Haircare / scalp", r"\bhair\b|scalp|shampoo|conditioner|minoxidil|regaine"),
 ("Body / hand", r"\bbody\b|\bhand\b|foot\b|\bbath\b|shower"),
 ("Supplement (oral)", r"supplement|capsule|tablet|oral|sachet|nutraceutical"),
]
NOISE = {
 "the", "with", "for", "and", "buy", "uk", "new", "skin", "skincare", "care", "size", "trial", "mini", "travel",
 "appropriate", "training", "required", "recommend", "recommended", "stock", "item", "prescription", "zero", "vat",
 "payable", "pay", "regular", "price", "professional", "pro", "range", "online", "ml", "g", "x", "set", "kit",
 "ltd", "sterile", "ce", "per", "each", "from", "of", "aesthetic", "aesthetics", "clinic", "original", "genuine",
 "value", "bundle", "offer", "sale", "now", "shop", "order", "best", "top", "quality", "gift", "collection", "pack",
 "back", "bar", "caddy", "advanced", "treatment", "step", "system", "formula",
}


def brand_of(title):
    t = title.lower()
    for rx, b in BRANDS:
        if re.search(rx, t): return b, "brand map"
    w = re.sub(r"[^A-Za-z0-9&+ -]", " ", title).split()
    return (w[0].title() if w else ""), "first token"


def func_of(t):
    for name, rx in FUNCS:
        if re.search(rx, t, re.I): return name
    return "Other skincare"


def size_of(t):
    m = re.search(r"(\d+(?:\.\d+)?)\s*ml\b", t, re.I) or re.search(r"(\d+(?:\.\d+)?)\s*g\b", t, re.I) \
        or re.search(r"(\d+(?:\.\d+)?)\s*(?:oz|ml|g|capsules?|tablets?|sachets?)\b", t, re.I)
    if not m: return ""
    return re.sub(r"\s+", "", m.group(0).lower())


def namecore(title, brand):
    t = re.sub(r"[®™©]", " ", title)
    t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"\d+(?:\.\d+)?\s*(ml|g|oz|x|%|capsules?|tablets?|sachets?)\b", " ", t, flags=re.I)
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


def slug(*parts):
    s = "-".join(p for p in parts if p)
    s = re.sub(r"[^A-Za-z0-9.%+]+", "-", s).strip("-").upper()
    return re.sub(r"-+", "-", s)


def main():
    rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8"))
            if r["category"] == "Skincare, haircare & peels" and r["scope"] == "Phase 1"]
    maps, prods = [], {}
    for r in rows:
        title = r["title"] if not r["title"].isdigit() else (r["page_title"] or r["title"])
        if not title.strip():
            maps.append(dict(r, code="", brand="", func="", decision="no title - review", confidence="review")); continue
        tl = title.lower()
        brand, how = brand_of(title)
        func = func_of(tl)
        size = size_of(tl)
        if not size:
            size = size_of(page_text(r["id"])[:400])
        core = namecore(title, brand)
        code = slug(brand[:20], core[:40], size)
        if not code:
            maps.append(dict(r, code="", brand=brand, func=func, decision="could not parse name - review", confidence="review")); continue
        conf = "high" if (brand and core) else ("rule" if brand else "partial")
        maps.append(dict(r, code=code, brand=brand, func=func,
                         decision=f"{func}; {brand}; {core or '?'}; {size or 'size?'}; {how}", confidence=conf))
        p = prods.setdefault(code, dict(code=code, brand=brand, name=core, function=func, size=size, suppliers=set(), listings=0))
        p["suppliers"].add(r["supplier"]); p["listings"] += 1
    # fold a size-less code into the single stated size of the same brand+name
    groups = collections.defaultdict(list)
    for p in prods.values():
        groups[(p["brand"], p["name"])].append(p)
    remap = {}
    for g in groups.values():
        blanks = [p for p in g if not p["size"]]
        stated = {p["size"]: p for p in g if p["size"]}
        if blanks and len(stated) == 1:
            tgt = next(iter(stated.values()))
            for b in blanks:
                remap[b["code"]] = tgt["code"]; tgt["suppliers"] |= b["suppliers"]; tgt["listings"] += b["listings"]
                del prods[b["code"]]
    for m in maps:
        if m.get("code") in remap:
            m["decision"] += " (size from matched product)"; m["code"] = remap[m["code"]]
    for p in prods.values():
        p["suppliers"] = len(p["suppliers"])
    out = ROOT / "catalogue/final"; out.mkdir(parents=True, exist_ok=True)
    pc = ["code", "function", "brand", "name", "size", "suppliers", "listings"]
    with open(out / "skincare_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc); w.writeheader()
        w.writerows(sorted(prods.values(), key=lambda p: (p["function"], p["brand"], p["code"])))
    with open(out / "skincare_listing_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "supplier", "title", "url", "brand", "func", "code", "confidence", "decision"], extrasaction="ignore")
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
    byf = collections.Counter(p["function"] for p in prods.values())
    multi = sum(1 for p in prods.values() if p["suppliers"] > 1)
    for t, b in [("Category 9 - Skincare, haircare & peels (cosmeceuticals)", True),
                 (f"{len(prods)} product codes from {len(maps)} listings across {len(set(m['supplier'] for m in maps))} suppliers, {len(set(p['brand'] for p in prods.values()))} brands.", False),
                 ("Branded cosmeceuticals are not interchangeable, so identity = brand + product name + size. The same branded "
                  "SKU sold by several suppliers is matched for price comparison; everything else is listed. The equivalence "
                  "group is the product FUNCTION (peel / SPF / retinoid / vitamin C / cleanser / serum / moisturiser / ...) "
                  "for browse and filter.", False),
                 (f"{multi} codes are carried by more than one supplier (compare on price); the rest are single-supplier (list only).", False),
                 ("Functions: " + ", ".join(f"{k} ({v})" for k, v in byf.most_common()), False),
                 (f"Confidence: high {cnt['high']}, rule {cnt['rule']} (brand only), partial {cnt['partial']}, review {cnt['review']}. "
                  "Supplier noise (training required / stock item / VAT / trial size) was stripped so a product's listings collapse to one code. "
                  "Sheets: By function | Products | Listings | Review.", True)]:
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=12 if b else 10, bold=b)
    rd.column_dimensions["A"].width = 155

    fs = wb.create_sheet("By function")
    head(fs, ["Function", "Codes", "Listings", "Top brands"], [26, 9, 10, 95])
    agg = collections.defaultdict(lambda: [0, 0, collections.Counter()])
    for p in prods.values():
        agg[p["function"]][0] += 1; agg[p["function"]][1] += p["listings"]; agg[p["function"]][2][p["brand"]] += 1
    for fn, _ in byf.most_common():
        v = agg[fn]; fs.append([fn, v[0], v[1], ", ".join(b for b, _ in v[2].most_common(12))]); fmt(fs)

    ps = wb.create_sheet("Products")
    head(ps, ["Code", "Function", "Brand", "Product name", "Size", "Suppliers", "Listings"], [34, 22, 20, 40, 10, 9, 8])
    for p in sorted(prods.values(), key=lambda p: (-p["suppliers"], p["function"], p["brand"], p["code"])):
        ps.append([p[k] for k in pc]); fmt(ps)
    ls = wb.create_sheet("Listings")
    head(ls, ["Code", "Function", "Brand", "Supplier", "Listing (link)", "Confidence", "How decided"], [34, 20, 18, 16, 50, 12, 38])
    FILL = {"high": "C6EFCE", "rule": "DDEBF7", "partial": "FFF2CC", "review": "F8CBAD"}
    for m in sorted([m for m in maps if m["code"]], key=lambda m: (m["func"], m["brand"], m["code"], m["supplier"])):
        ls.append([m["code"], m["func"], m["brand"], m["supplier"], m["title"], m["confidence"], m["decision"]]); fmt(ls); link(ls, 5, m["url"])
        ls.cell(row=ls.max_row, column=6).fill = PatternFill("solid", fgColor=FILL.get(m["confidence"], "FFFFFF"))
    ls.auto_filter.ref = f"A1:G{ls.max_row}"
    rv = wb.create_sheet("Review")
    head(rv, ["Supplier", "Listing (link)", "Why"], [18, 66, 36])
    for m in [m for m in maps if m["confidence"] == "review"]:
        rv.append([m["supplier"], m["title"], m["decision"]]); fmt(rv); link(rv, 2, m["url"])
    p = ROOT / "output/category_09_skincare.xlsx"; wb.save(p); print(p)
    print(len(prods), "codes |", dict(cnt), "| multi-supplier:", multi)
    print("functions:", dict(byf))


if __name__ == "__main__":
    main()
