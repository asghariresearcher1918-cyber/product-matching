"""Category 11 - Clinic consumables & PPE: catalogue + listing map.
Mixed commodity + branded consumables. Equivalence group = functional subtype (gloves, masks, gauze/swabs,
dressings/tape, antiseptic/prep, drapes/covers, paper/towel/tissue, sharps/waste, gowns/aprons, head/face PPE,
containers, cleaning solutions, bibs, applicators, other). Gloves are spec-based (material + size + colour, brand a
filterable attribute, owner rule) so the same glove compares across suppliers; branded items keep brand+name identity.
Supplier noise stripped; size/spec read from title then page. Code = SUBTYPE-[spec/brand-name]-[size].
Outputs: catalogue/final/consumable_products.csv, consumable_listing_map.csv, output/category_11_consumables.xlsx
Usage: python -I scripts/consumable_catalogue.py"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_facts import page_text
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent

SUBTYPES = [
 ("Compression garment", r"\bmacom\b|compression (garment|vest|bra|band|support)|post-?op garment|support garment"),
 ("Blade / scalpel", r"\bblade\b|scalpel|stitch cutter|cygnetic|blade remover"),
 ("IV & blood collection", r"vacutainer|iv set|infusion set|intrafix|giving set|blood collection|butterfly needle|winged set|gravity set|primeline"),
 ("Conductive gel (US/ECG)", r"ultrasound gel|conduction gel|conductive gel|ecg gel|\banagel\b"),
 ("Diagnostic / monitoring", r"thermometer|test strip|\blancet|glucose monitor|endotest|pulse oximeter|bp monitor|sphygmo|caresens"),
 ("Tourniquet", r"tourniquet"),
 ("Hot / cold pack", r"ice pack|cold pack|hot pack|cold bag|coldbag|instant ice"),
 ("First aid", r"first aid"),
 ("Gloves", r"\bglove|nitrile|latex|vinyl|biogel|polyfield|powder-?free"),
 ("Face mask / respirator", r"face mask|surgical mask|\bmask\b|respirator|ffp[23]|type ii|earloop"),
 ("Head / face PPE", r"visor|face shield|surgical cap|bouffant|hair ?net|surgical hat|mob cap|theatre cap|round cap|surgical hood"),
 ("Gown / apron / coverall", r"\bgown|apron|coverall|scrub suit|lab coat"),
 ("Sharps / clinical waste", r"sharps|sharpsguard|clinical waste|waste bag|dustbin liner|bin liner|yellow bag|disposal bin"),
 ("Antiseptic / skin prep / wipe", r"clinisept|clinell|hydrex|hibi|hibiscrub|hibiwash|alcohol|chlorhex|skin prep|antisep|sanitiser|sanitizer|disinfect|\bwipe|milton|azowipe|isopropyl|surface spray|\bprep pad"),
 ("Dressing / tape / suture", r"dressing|plaster|bandage|\btape\b|micropore|transpore|steri-?strip|\bvicryl|\bsuture|wound|mepore|opsite|tegaderm|primapore|hypafix|cohesive"),
 ("Gauze / swab / cotton", r"gauze|swab|cotton wool|cotton ball|dental roll|non-?woven|topper|gamgee|cellulose"),
 ("Drape / cover / barrier film", r"drape|couch roll|bed roll|mayo table|table cover|wraparound|wrap around|tube sleeve|headrest cover|surface cover|barrier film|protection cover|disposa-?shield|equipment protection"),
 ("Paper / towel / tissue", r"hand towel|c-?fold|z-?fold|m-?fold|toilet|facial tissue|\btissue|wiping paper|centrefeed|centre feed|jumbo roll|kitchen roll|roll towel|hygiene roll|dispenser|paper roll"),
 ("Bib", r"\bbib\b|bibs\b|bib chain"),
 ("Container / tray / bowl", r"\btray\b|container|gallipot|\bbowl\b|\bjar\b|\bcup\b|flowfusor|collection bottle|specimen|kidney dish"),
 ("Cleaning / solution", r"hand soap|hand ?wash|hand gel|liquid soap|purified water|sterile water|saline wash|detergent|solution\b|cleaning|surgical spirit"),
 ("Applicator / spatula", r"applicator|cotton bud|\bspatula|microbrush|tongue depressor|wooden stick"),
 ("Couch / bed & furniture roll", r"couch cover|bed sheet|pillow case"),
]
GLOVE_MAT = [("nitrile", r"nitrile"), ("latex", r"latex"), ("vinyl", r"vinyl"), ("polyisoprene", r"polyisoprene|biogel")]
SIZES = [("XS", r"\bx-?small\b|\bxs\b"), ("S", r"\bsmall\b|\bs/m\b"), ("M", r"\bmedium\b|\bmed\b"),
         ("L", r"\blarge\b"), ("XL", r"\bx-?large\b|\bxl\b")]
NOISE = {"the", "with", "for", "and", "buy", "uk", "new", "disposable", "sterile", "non", "sterile)", "box", "pack",
         "of", "ml", "x", "each", "per", "ce", "pcs", "pieces", "clinic", "medical", "professional", "stock", "item",
         "vat", "payable", "zero", "prescription", "appropriate", "training", "required", "free", "single", "use",
         "ply", "colour", "color", "size", "pack)", "ltd", "quality", "value"}


def subtype(t):
    for name, rx in SUBTYPES:
        if re.search(rx, t, re.I): return name
    return "Consumable (other)"


def glove_spec(t):
    mat = next((m for m, rx in GLOVE_MAT if re.search(rx, t, re.I)), "")
    sz = next((s for s, rx in SIZES if re.search(rx, t, re.I)), "")
    col = next((c for c in ["black", "blue", "white", "clear", "purple", "green"] if re.search(r"\b" + c + r"\b", t, re.I)), "")
    pf = "PF" if re.search(r"powder-?free|\bp/?f\b", t, re.I) else ("PD" if re.search(r"powdered", t, re.I) else "")
    return mat, sz, col, pf


def size_of(t):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|l|litre|g|cm|mm|m)\b", t, re.I) or re.search(r"(\d+)\s*x\s*(\d+)\s*cm", t, re.I)
    return re.sub(r"\s+", "", m.group(0).lower()) if m else ""


def pack_of(title, pid):
    """Units per pack, read from the NAME first then the whole PAGE (owner rule: 100% certainty, never guessed).
    Shops state it as 'Size: 1 x 4', 'Size - pack of 2', 'pack of N', 'N pcs', etc. 'A x B' = B units per pack."""
    for src in (title, page_text(pid)):
        t = (src or "").lower()
        m = re.search(r"size\s*[:\-]?\s*(\d{1,4})\s*x\s*(\d{1,4})", t) or re.search(r"\b(\d{1,4})\s*x\s*(\d{1,4})\b", t)
        if m:
            return str(int(m.group(2)))
        m = re.search(r"pack of\s*(\d{1,4})|box of\s*(\d{1,4})|size\s*[:\-]?\s*(\d{2,4})\s*(?:pcs|pieces?|pack)", t)
        if m:
            return str(int(next(g for g in m.groups() if g)))
        m = re.search(r"\b(\d{1,4})\s*(?:pcs|pieces?|pairs?|sheets?|wipes?|swabs?|rolls?|sachets?|['’]s)\b", t)
        if m and 2 <= int(m.group(1)) <= 10000:
            return str(int(m.group(1)))
    return ""


def brand_of(t):
    w = re.sub(r"[^A-Za-z0-9&+ -]", " ", t).split()
    return (w[0] if w else "")


def namecore(title, brand, extra_skip=()):
    t = re.sub(r"[®™©]", " ", title)
    t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"\d+(?:\.\d+)?\s*(ml|l|litre|g|cm|mm|x|ply|pack|box)\b", " ", t, flags=re.I)
    t = re.sub(r"[^A-Za-z0-9 ]", " ", t)
    skip = NOISE | set(extra_skip)
    bw = set(re.sub(r"[^a-z0-9 ]", " ", brand.lower()).split())
    keep = []
    for w in t.split():
        wl = w.lower()
        if wl in bw or wl in skip or len(w) <= 1: continue
        if wl in [k.lower() for k in keep]: continue
        keep.append(w)
        if len(keep) >= 4: break
    return " ".join(keep)


def slug(*p):
    s = "-".join(x for x in p if x)
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9.%]+", "-", s).strip("-")).upper()


def main():
    rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8"))
            if r["category"] == "Clinic consumables & PPE" and r["scope"] == "Phase 1"]
    maps, prods = [], {}
    for r in rows:
        title = r["title"] if not r["title"].isdigit() else (r["page_title"] or r["title"])
        if not title.strip():
            maps.append(dict(r, code="", sub="", brand="", decision="no title", confidence="review")); continue
        tl = title.lower()
        sub = subtype(title)
        brand = brand_of(title)
        size = size_of(tl) or size_of(page_text(r["id"])[:400])
        pack = pack_of(title, r["id"])            # units per pack (name first, then page) - owner rule
        if sub == "Gloves":  # spec-based: material+size+colour, brand an attribute
            mat, sz, col, pf = glove_spec(tl)
            spec = " ".join(x for x in [mat, sz, col, pf] if x)
            code = slug("GLOVE", mat, sz, col, pf) if (mat or sz) else slug("GLOVE", namecore(title, brand)[:20])
            desc = f"Gloves; {spec or '?'}; brand {brand}"
            name = spec
            key_brand = brand
        else:
            core = namecore(title, brand)
            # pack is part of a consumable's identity: a 4-pack and a 2-pack of the same item are different products.
            # only a real multipack (>=2) splits the code; single/unstated units keep the base code (no 'P1' noise).
            multipack = f"P{pack}" if (pack and int(pack) >= 2) else ""
            code = slug(re.sub(r"[^A-Z]", "", sub.upper())[:6] or "CONS", brand[:14], core[:30], size, multipack)
            desc = f"{sub}; {brand} {core}; {size or 'size?'}" + (f"; pack of {pack}" if pack else "")
            name = core
            key_brand = brand
        if not code:
            maps.append(dict(r, code="", sub=sub, brand=brand, decision="could not parse - review", confidence="review")); continue
        conf = "high" if (sub != "Consumable (other)" and (name or size)) else ("rule" if sub != "Consumable (other)" else "partial")
        maps.append(dict(r, code=code, sub=sub, brand=key_brand, decision=desc, confidence=conf))
        p = prods.setdefault(code, dict(code=code, subtype=sub, name=name, size=size, pack=pack, brands=set(), suppliers=set(), listings=0))
        p["brands"].add(key_brand); p["suppliers"].add(r["supplier"]); p["listings"] += 1
    for p in prods.values():
        p["supplier_n"] = len(p["suppliers"]); p["brands"] = "; ".join(sorted(b for b in p["brands"] if b)[:6]); p["suppliers"] = len(p["suppliers"])
    out = ROOT / "catalogue/final"; out.mkdir(parents=True, exist_ok=True)
    pc = ["code", "subtype", "name", "size", "pack", "brands", "supplier_n", "listings"]
    with open(out / "consumable_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc, extrasaction="ignore"); w.writeheader()
        w.writerows(sorted(prods.values(), key=lambda p: (p["subtype"], p["code"])))
    with open(out / "consumable_listing_map.csv", "w", newline="", encoding="utf-8") as f:
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
    for t, b in [("Category 11 - Clinic consumables & PPE", True),
                 (f"{len(prods)} product codes from {len(maps)} listings across {len(set(m['supplier'] for m in maps))} suppliers.", False),
                 ("Equivalence group = functional subtype. Gloves are spec-based (material + size + colour, brand a filterable "
                  "attribute) so the same glove compares across suppliers; branded items (antiseptics, dressings) keep "
                  "brand + name identity. Everything is listed; compare where several suppliers share a code.", False),
                 (f"{multi} codes are stocked by more than one supplier (compare on price-per-unit).", False),
                 ("Subtypes: " + ", ".join(f"{k} ({v})" for k, v in bysub.most_common()), False),
                 (f"Confidence: high {cnt['high']}, rule {cnt['rule']}, partial {cnt['partial']}, review {cnt['review']}. "
                  "Sheets: By subtype | Products | Listings | Review.", True)]:
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=12 if b else 10, bold=b)
    rd.column_dimensions["A"].width = 152

    ss = wb.create_sheet("By subtype")
    head(ss, ["Subtype", "Codes", "Listings", "Multi-supplier"], [30, 9, 10, 14])
    agg = collections.defaultdict(lambda: [0, 0, 0])
    for p in prods.values():
        a = agg[p["subtype"]]; a[0] += 1; a[1] += p["listings"]; a[2] += (1 if p["supplier_n"] > 1 else 0)
    for sb, _ in bysub.most_common():
        a = agg[sb]; ss.append([sb, a[0], a[1], a[2]]); fmt(ss)

    ps = wb.create_sheet("Products")
    head(ps, ["Code", "Subtype", "Name / spec", "Size", "Brands", "Suppliers", "Listings"], [34, 24, 34, 10, 40, 9, 8])
    for p in sorted(prods.values(), key=lambda p: (-p["supplier_n"], p["subtype"], p["code"])):
        ps.append([p[k] for k in pc]); fmt(ps)
    ls = wb.create_sheet("Listings")
    head(ls, ["Code", "Subtype", "Brand", "Supplier", "Listing (link)", "Confidence", "How decided"], [34, 22, 16, 16, 50, 12, 36])
    FILL = {"high": "C6EFCE", "rule": "DDEBF7", "partial": "FFF2CC", "review": "F8CBAD"}
    for m in sorted([m for m in maps if m["code"]], key=lambda m: (m["sub"], m["code"], m["supplier"])):
        ls.append([m["code"], m["sub"], m["brand"], m["supplier"], m["title"], m["confidence"], m["decision"]]); fmt(ls); link(ls, 5, m["url"])
        ls.cell(row=ls.max_row, column=6).fill = PatternFill("solid", fgColor=FILL.get(m["confidence"], "FFFFFF"))
    ls.auto_filter.ref = f"A1:G{ls.max_row}"
    rv = wb.create_sheet("Review")
    head(rv, ["Supplier", "Listing (link)", "Why"], [18, 66, 30])
    for m in [m for m in maps if m["confidence"] in ("review", "partial")]:
        rv.append([m["supplier"], m["title"], m["decision"]]); fmt(rv); link(rv, 2, m["url"])
    p = ROOT / "output/category_11_consumables.xlsx"; wb.save(p); print(p)
    print(len(prods), "codes |", dict(cnt), "| multi-supplier:", multi)
    print("subtypes:", dict(bysub))
    print("Consumable (other) listings:", sum(1 for m in maps if m["sub"] == "Consumable (other)"))


if __name__ == "__main__":
    main()
