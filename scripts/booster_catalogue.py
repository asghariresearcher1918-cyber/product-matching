"""Category 8 - Skin boosters / polynucleotides / mesotherapy: catalogue + listing map.
These are BRANDED products (not generic-interchangeable), so each brand+line+presentation gets its own code,
and the equivalence group is the ACTIVE CLASS - polynucleotide/PDRN, HA bio-remodelling, amino-acid booster,
mesotherapy cocktail, exosome, PRP/PRF - so alternative brands in the same class are shown together in search /
suggestions (owner rule: different licence -> separate code but linked group). Line / volume / pack read from the
title, then the page (page_facts). Code = BRAND[-LINE]-[VOLUME]-PACK.
Outputs: catalogue/final/booster_products.csv, booster_listing_map.csv, output/category_08_skin_booster.xlsx
Usage: python -I scripts/booster_catalogue.py"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_facts import page_text
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent

# canonical brand map: regex (specific first) -> (canonical brand, manufacturer, active class)
PN = "Polynucleotide / PDRN"
HA = "HA bio-remodelling"
AMINO = "Amino-acid skin booster"
MESO = "Mesotherapy cocktail"
EXO = "Exosome"
PRP = "PRP / PRF kit"
OTHER = "Skin booster / mesotherapy (other)"
BRANDS = [
 (r"nucleofill", ("Nucleofill", "Promoitalia", PN)),
 (r"plenhyage", ("Plenhyage", "Vivacy", PN)),
 (r"\bplinest\b|pilnest|newest|mastelli", ("Plinest / Newest", "Mastelli", PN)),
 (r"nithya", ("Nithya", "Euromi", PN)),
 (r"asce\s*\+|\basce\b", ("ASCE+", "Exocobio", EXO)),
 (r"cellbooster|cell booster", ("Cellbooster", "Croma", HA)),
 (r"hyalace", ("Hyalace", "Hyalace", HA)),
 (r"innoaesthetics|inno aesthetics", ("Inno Aesthetics", "Innoaesthetics", MESO)),
 (r"rejuran", ("Rejuran", "PharmaResearch (Korea)", PN)),
 (r"vitaran", ("Vitaran", "VitaRan / Caregen", PN)),
 (r"ameela", ("Ameela", "Teg-Derma / IBSA", PN)),
 (r"polyphil", ("Polyphil", "Polyphil", PN)),
 (r"nouveau visage", ("Nouveau Visage", "Nouveau Visage", PN)),
 (r"longevha", ("LongevHA", "LongevHA", PN)),
 (r"ninaveli", ("Ninaveli", "Ninaveli", PN)),
 (r"\bami\b|ami eyes|ami pro", ("AMI", "AMI", PN)),
 (r"reversha", ("Reversha", "Reversha", PN)),
 (r"profhilo", ("Profhilo", "IBSA", HA)),
 (r"viscoderm", ("Viscoderm", "IBSA", HA)),
 (r"seventy hyal|seventyhyal|70 hyal", ("Seventy Hyal 2000", "Seventy Hyal", HA)),
 (r"ejal", ("Ejal 40", "Professional Derma", HA)),
 (r"hyalual", ("Hyalual", "Hyalual", HA)),
 (r"\bhyaron\b", ("Hyaron", "Hyaron", HA)),
 (r"aquashine", ("Aquashine", "Caregen", HA)),
 (r"\brichesse\b", ("Richesse", "Richesse", HA)),
 (r"sunekos", ("Sunekos", "Professional Derma", AMINO)),
 (r"jalupro", ("Jalupro", "Professional Derma", AMINO)),
 (r"cellenis", ("Cellenis", "Regen Lab", PRP)),
 (r"pluryal", ("Pluryal Mesoline", "MD Skin Solutions", MESO)),
 (r"\brrs\b", ("RRS", "AQ Skin / Skin Tech", MESO)),
 (r"fillmed|filorga|nctf", ("Fillmed (NCTF)", "Fillmed", MESO)),
 (r"cytocare", ("Cytocare", "Revitacare", MESO)),
 (r"dermaheal", ("Dermaheal", "Caregen", MESO)),
 (r"\bbcn\b", ("BCN", "Institute BCN", MESO)),
 (r"toskani", ("Toskani", "Toskani", MESO)),
 (r"dermaqual", ("Dermaqual", "Dermaqual", MESO)),
 (r"inno-?tds|innotds", ("Inno-TDS", "Innoaesthetics", MESO)),
 (r"magicalift", ("Magicalift", "Magicalift", MESO)),
 (r"stayve", ("Stayve", "Stayve", MESO)),
 (r"prostrolane", ("Prostrolane", "Caregen", MESO)),
 (r"medisco", ("Medisco", "Medisco", MESO)),
 (r"\bares\b", ("Ares", "Ares", MESO)),
 (r"\bdpg\b", ("DPG", "DPG", MESO)),
 (r"\bxela\b|rederm", ("Xela Rederm", "Xela", MESO)),
 (r"natural meso|natural-meso", ("Natural Meso", "Natural Meso", MESO)),
 (r"mesoeye|lumi eyes|lumi-?eyes", ("Lumi Eyes", "Lumi", PN)),
 (r"lumi-?pn", ("Lumi PN", "Lumi", PN)),
 (r"lumi-?meso", ("Lumi Meso", "Lumi", MESO)),
 (r"lumi-?pro|lumi pro", ("Lumi Pro", "Lumi", MESO)),
 (r"dermaren", ("Dermaren", "Dermaren", PN)),
 (r"cosmopro|hikari", ("Cosmopro Hikari", "Cosmopro", PN)),
 (r"purasomes", ("Purasomes", "Purasomes", EXO)),
 (r"exoblanc", ("Exoblanc", "Exoblanc", EXO)),
 (r"exocean", ("Exocean", "Exocean", EXO)),
 (r"\bexo(?:some|cream|derm)?\b", ("Exosome (other)", "various", EXO)),
 (r"infini", ("Infini", "Infini", PRP)),
 (r"\bprp\b|\bprf\b|regenlab|tropocells|\bpure\s*prp", ("PRP / PRF kit", "various", PRP)),
 (r"revitrane", ("Revitrane", "Revitrane", HA)),
 (r"neauvia", ("Neauvia Hydro Deluxe", "Matex Lab", HA)),
 (r"croma|saypha booster", ("Saypha Booster", "Croma", HA)),
 (r"lemon bottle", ("Lemon Bottle (skin booster)", "Lemon Bottle", OTHER)),
 (r"revs\b", ("REVS", "REVS", MESO)),
 (r"karisma", ("Karisma", "Karisma", PN)),
 (r"kiara", ("Kiara", "Kiara Reju", PN)),
 (r"\bejal\b", ("Ejal", "Professional Derma", HA)),
 (r"myfiller", ("MyFiller Booster", "MyFiller", HA)),
 (r"\btsk\b", ("TSK (needles)", "TSK", OTHER)),
 (r"\bwow\b", ("WOW", "WOW", EXO)),
 (r"revofil|aquafilling booster", ("Revofil", "Revofil", PN)),
 (r"\bhp\b meso|hp mesotherapy", ("HP Meso", "HP", MESO)),
]
# whole-title class hints when brand unknown
CLASS_HINTS = [(EXO, r"exosome|exo\b|lyoph.*exo"), (PRP, r"\bprp\b|\bprf\b|platelet"),
               (PN, r"polynucleotide|pdrn|\bpn\b|salmon dna"), (HA, r"bio.?remodel|profhilo|\bha\b booster"),
               (AMINO, r"amino"), (MESO, r"mesother|meso\b|cocktail")]


def brand_class(title):
    t = title.lower()
    for rx, (b, man, cls) in BRANDS:
        if re.search(rx, t): return b, man, cls, "brand map"
    for cls, rx in CLASS_HINTS:
        if re.search(rx, t): return "", "", cls, "class hint"
    return "", "", OTHER, "unclassified"


def volume(t):
    m = re.search(r"(\d+(?:\.\d+)?)\s*ml\b", t, re.I)
    if m: return m.group(1).rstrip(".") + "ml"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(mg|g)\b", t, re.I)
    return re.sub(r"\s+", "", m.group(0).lower()) if m else ""


def pack(t):
    m = (re.search(r"pack of\s*(\d+)", t, re.I) or re.search(r"\bbox of\s*(\d+)", t, re.I)
         or re.search(r"(\d+)\s*x\s*\d*\.?\d*\s*ml", t, re.I) or re.search(r"\bx\s*(\d+)\b", t, re.I)
         or re.search(r"\b(\d+)\s*(?:vials?|syringes?|amps?|ampoules?)\b", t, re.I))
    return int(m.group(1)) if m else 1


# supplier noise and base-formula words that must NOT become a product line
NOISE_WORDS = {
 "the", "with", "for", "and", "buy", "uk", "ml", "kit", "new", "skin", "booster", "boosters", "mesotherapy", "meso",
 "injection", "injectable", "inj", "treatment", "prescription", "item", "stock", "regular", "price", "appropriate",
 "training", "recommended", "recommend", "online", "herts", "get", "remedium", "premium", "syringe", "syringes",
 "needle", "needles", "cannula", "vial", "vials", "amp", "amps", "ampoule", "ampoules", "box", "pack", "packs",
 "ltd", "sterile", "ce", "marked", "medical", "device", "per", "each", "from", "of", "pre", "filled", "prefilled",
 "hl", "h+l", "profhilo", "set", "single", "double", "range", "offer", "sale", "aesthetic", "aesthetics", "clinic",
 "professional", "original", "genuine", "authentic", "value", "bundle", "x1", "1x", "2x", "3x",
 "hologram", "roi", "eu", "uk/eu", "irish", "ireland", "english", "euro",
 "vat", "payable", "zero", "pay", "no", "yes", "essex", "london", "exom", "rejuvenation",
 "free", "aqua", "now", "here", "shop", "order", "best", "top", "quality", "grade",
 "supplies", "supply", "cream"}


def market(t):
    if re.search(r"hologram", t, re.I): return "HG"       # hologram vs non-hologram = market variant (owner rule)
    if re.search(r"\broi\b|irish|ireland", t, re.I): return "ROI"
    return ""


def line_of(title, brand):
    """The product sub-line only (e.g. 'Structura', 'Body', 'Shine', '1200'), noise and base-formula stripped."""
    t = re.sub(r"\(.*?\)", " ", title)
    t = re.sub(r"\d+(?:\.\d+)?\s*(ml|mg|g|x|vials?|syringes?|amps?|ampoules?|pack|box)\b", " ", t, flags=re.I)
    t = re.sub(r"[-/+]", " ", t)
    t = re.sub(r"[^A-Za-z0-9 ]", " ", t)
    bw = set(re.sub(r"[^a-z0-9 ]", " ", brand.lower()).split())
    keep = []
    for w in t.split():
        wl = w.lower()
        if wl in bw or wl in NOISE_WORDS or len(w) <= 1: continue
        if wl in [k.lower() for k in keep]: continue
        keep.append(w)
        if len(keep) >= 2: break
    return " ".join(keep)


def slug(*parts):
    s = "-".join(p for p in parts if p)
    s = re.sub(r"[^A-Za-z0-9.%+]+", "-", s).strip("-").upper()
    return re.sub(r"-+", "-", s)


def main():
    rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8"))
            if r["category"] == "Skin booster / polynucleotide / mesotherapy" and r["scope"] == "Phase 1"]
    maps, prods = [], {}
    for r in rows:
        title = r["title"] if not r["title"].isdigit() else (r["page_title"] or r["title"])
        tl = title.lower()
        brand, man, cls, how = brand_class(title)
        vol = volume(tl)
        pk = pack(tl)
        if not vol:
            vol = volume(page_text(r["id"])[:500])
        bname = brand or (re.sub(r"[^A-Za-z0-9+ -]", " ", title).split()[0].title() if title.strip() else brand)
        line = line_of(title, bname)
        mk = market(tl)
        code = slug(bname[:22], line[:26], vol, f"X{pk}" if pk > 1 else "", mk)
        if not code:
            maps.append(dict(r, code="", brand="", cls=cls, decision="could not parse - review", confidence="review")); continue
        conf = "high" if (brand and vol) else ("rule" if brand or vol else "partial")
        maps.append(dict(r, code=code, brand=bname, cls=cls,
                         decision=f"{cls}; {bname}{(' ' + line) if line else ''}; {vol or '?'}; pack {pk}{'; ' + mk if mk else ''}; {how}", confidence=conf))
        p = prods.setdefault(code, dict(code=code, brand=bname, line=line, active_class=cls, manufacturer=man,
                                        volume=vol, pack=pk, market=mk, suppliers=set(), listings=0))
        p["suppliers"].add(r["supplier"]); p["listings"] += 1
    # consolidation: a volume-less code folds into the single stated volume of the same brand+line+pack+market
    groups = collections.defaultdict(list)
    for p in prods.values():
        groups[(p["brand"], p["line"].lower(), p["pack"], p["market"])].append(p)
    remap = {}
    for g in groups.values():
        blanks = [p for p in g if not p["volume"]]
        stated = {p["volume"]: p for p in g if p["volume"]}
        if blanks and len(stated) == 1:
            tgt = next(iter(stated.values()))
            for b in blanks:
                remap[b["code"]] = tgt["code"]
                tgt["suppliers"] |= b["suppliers"]; tgt["listings"] += b["listings"]
                del prods[b["code"]]
    for m in maps:
        if m.get("code") in remap:
            m["decision"] += " (volume from matched product)"; m["code"] = remap[m["code"]]
    # decimal fix: a supplier writing "35ml"/"15ml"/"10ml" means 3.5/1.5/1.0 for an injectable vial.
    # Only merge when the decimal twin already exists in the same brand+line+pack+market (safe, no guessing).
    def mlnum(v):
        mm = re.match(r"^(\d+(?:\.\d+)?)ml$", v or "")
        return float(mm.group(1)) if mm else None
    groups2 = collections.defaultdict(dict)
    for p in prods.values():
        n = mlnum(p["volume"])
        if n is not None:
            groups2[(p["brand"], p["line"].lower(), p["pack"], p["market"])][round(n, 3)] = p
    dmap = {}
    for vols in groups2.values():
        for n, p in list(vols.items()):
            if n >= 10 and (n / 10) in vols:          # 35 -> 3.5, 15 -> 1.5, 10 -> 1.0
                tgt = vols[n / 10]
                dmap[p["code"]] = tgt["code"]
                tgt["suppliers"] |= p["suppliers"]; tgt["listings"] += p["listings"]
                prods.pop(p["code"], None)
    for m in maps:
        if m.get("code") in dmap:
            m["decision"] += " (decimal volume fixed)"; m["code"] = dmap[m["code"]]
    for p in prods.values():
        p["suppliers"] = len(p["suppliers"])
    out = ROOT / "catalogue/final"; out.mkdir(parents=True, exist_ok=True)
    pc = ["code", "active_class", "brand", "line", "volume", "pack", "market", "manufacturer", "suppliers", "listings"]
    with open(out / "booster_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc); w.writeheader()
        w.writerows(sorted(prods.values(), key=lambda p: (p["active_class"], p["brand"], p["code"])))
    with open(out / "booster_listing_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "supplier", "title", "url", "brand", "cls", "code", "confidence", "decision"], extrasaction="ignore")
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
    bycls = collections.Counter(p["active_class"] for p in prods.values())
    for t, b in [("Category 8 - Skin boosters / polynucleotides / mesotherapy", True),
                 (f"{len(prods)} product codes from {len(maps)} listings across {len(set(m['supplier'] for m in maps))} suppliers.", False),
                 ("These are branded products, not interchangeable generics. Each brand + line + presentation is its own code. "
                  "The equivalence group is the ACTIVE CLASS, so alternative brands in the same class are shown together in "
                  "search / suggestions (owner rule: different licence -> separate code, linked group).", False),
                 ("Classes: " + ", ".join(f"{k} ({v})" for k, v in bycls.most_common()), False),
                 (f"Confidence: high {cnt['high']}, rule {cnt['rule']} (brand or volume only), partial {cnt['partial']}, review {cnt['review']}.", False),
                 ("Where several suppliers carry the same code -> compare on price-per-ml. Single supplier -> list only. "
                  "Sheets: By class | Products | Listings | Review.", True)]:
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=12 if b else 10, bold=b)
    rd.column_dimensions["A"].width = 150

    cs = wb.create_sheet("By class")
    head(cs, ["Active class", "Codes", "Listings", "Brands"], [26, 9, 10, 90])
    byc = collections.defaultdict(lambda: [0, 0, set()])
    for p in prods.values():
        byc[p["active_class"]][0] += 1; byc[p["active_class"]][1] += p["listings"]; byc[p["active_class"]][2].add(p["brand"])
    for cls in [PN, HA, AMINO, MESO, EXO, PRP, OTHER]:
        if cls in byc:
            v = byc[cls]; cs.append([cls, v[0], v[1], ", ".join(sorted(b for b in v[2] if b))]); fmt(cs)

    ps = wb.create_sheet("Products")
    head(ps, ["Code", "Active class", "Brand", "Line / variant", "Volume", "Pack", "Market", "Manufacturer", "Suppliers", "Listings"],
         [30, 24, 20, 24, 10, 7, 8, 22, 9, 8])
    for p in sorted(prods.values(), key=lambda p: (p["active_class"], p["brand"], p["volume"], p["code"])):
        ps.append([p[k] for k in pc]); fmt(ps)
    ls = wb.create_sheet("Listings")
    head(ls, ["Code", "Active class", "Brand", "Supplier", "Listing (link)", "Confidence", "How decided"], [30, 22, 18, 16, 50, 12, 40])
    FILL = {"high": "C6EFCE", "rule": "DDEBF7", "partial": "FFF2CC", "review": "F8CBAD"}
    for m in sorted([m for m in maps if m["code"]], key=lambda m: (m["cls"], m["brand"], m["code"], m["supplier"])):
        ls.append([m["code"], m["cls"], m["brand"], m["supplier"], m["title"], m["confidence"], m["decision"]]); fmt(ls); link(ls, 5, m["url"])
        ls.cell(row=ls.max_row, column=6).fill = PatternFill("solid", fgColor=FILL.get(m["confidence"], "FFFFFF"))
    ls.auto_filter.ref = f"A1:G{ls.max_row}"
    rv = wb.create_sheet("Review")
    head(rv, ["Supplier", "Listing (link)", "Class guess", "Why"], [18, 60, 22, 30])
    for m in [m for m in maps if m["confidence"] in ("review", "partial")]:
        rv.append([m["supplier"], m["title"], m["cls"], m["decision"]]); fmt(rv); link(rv, 2, m["url"])
    p = ROOT / "output/category_08_skin_booster.xlsx"; wb.save(p); print(p)
    print(len(prods), "codes |", dict(cnt), "|", dict(bycls))
    print("unclassified (OTHER) listings:", sum(1 for m in maps if m["cls"] == OTHER))


if __name__ == "__main__":
    main()
