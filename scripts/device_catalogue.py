"""Category 12 - Devices & equipment: catalogue + listing map.
Capital equipment, device consumables (tips/cartridges) and accessories/parts. Equivalence group = modality/type
(RF microneedling, HIFU/ultrasound, laser/IPL, cryo, LED, electrosurgery/electrolysis, skin analysis, facial machine,
microneedling pen, derma roller, body/slimming, furniture, steriliser, fridge, lamp/magnifier). A 'kind' column marks
machine vs consumable (tip/cartridge) vs accessory/part. Mostly list-only (capital items); the disposable tips compare
where several suppliers carry them. Items that are clearly NOT aesthetic equipment (IUDs, respiratory spacers, x-ray,
air purifiers, home test kits) are flagged for re-filing, not coded. Code = BRAND-NAMECORE[-KIND].
Outputs: catalogue/final/device_products.csv, device_listing_map.csv, output/category_12_devices.xlsx
Usage: python -I scripts/device_catalogue.py"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent

# items that do not belong in aesthetic devices -> flag for re-filing (regex, where it belongs)
MISFILED = [
 (r"\bmirena\b|kyleena|jaydess|nexplanon|copper\s*t|nova\s*t\b|novaplus t|\bt\s*380\b|\biud\b", "Contraceptive device -> Medicines/gynae"),
 (r"aerochamber|volumatic|\bspacer\b|nebuliser|nebulizer|dentalpro aerosol", "Respiratory device -> Medicines"),
 (r"x-?ray|step wedge|film edge softener", "Dental x-ray imaging -> Imaging"),
 (r"air purifier|airbubbl|airhavn|purifier", "Air purifier -> Facility equipment"),
 (r"home blood test|testing kit|ketostix|uristix|reagent strip|menopause.*profile|pillcutter|pill cutter|blood pressure monitor", "Home test / diagnostics -> Diagnostics"),
 (r"\bpraluent\b|\bepipen\b|epi pen|\bgenotropin\b|\bxolair\b|lignospan|\baimovig\b|\bdupixent\b", "Injectable medicine -> Medicines"),
]
SUBTYPES = [
 ("RF microneedling", r"microneedl.*rf|rf.*microneedl|radiofrequency microneedl|potenza|morpheus|secret rf|secret pro|\bthermage\b|sylfirm|genius rf|intracel|infini rf"),
 ("HIFU / focused ultrasound", r"\bhifu\b|ultraformer|doublo|ultracel|focused ultrasound|sofwave|sygmalift"),
 ("Laser / IPL", r"\blaser\b|\bipl\b|diode|nd:?yag|alexandrite|co2 laser|picosecond|q-?switch|erbium|dye laser"),
 ("Cryotherapy / cryolipolysis", r"cryo|cryolipo|coolsculpt|fat freez|cryother"),
 ("LED / light therapy", r"\bled\b|light therapy|photobiomodulation|dermalux"),
 ("Electrosurgery / electrolysis / plasma", r"cauter|electrosurg|diathermy|hyfrecator|plasma pen|plexr|\bepilat|electrolysis|\bsterex\b|short wave|blend\b"),
 ("Skin analysis / imaging", r"\bobserv\b|skin analys|visia|imaging|skin scanner|\bscanner\b|moisture sensor|moistsense|woods lamp"),
 ("Facial machine & accessory", r"hydrafacial|hydra\s*plus|hydro\s*plus|profacial|dermabrasion|microdermabrasion|aqua\s*peel|aqua\s*facial|oxygen facial|jet peel|\bhydro\b"),
 ("Microneedling pen & cartridge", r"microneedl|micro-?needl|derma\s*pen|dermapen|\b1need|needle cartridge|needle module|nano cartridge|m-?pen"),
 ("Derma roller / stamp", r"derma ?roller|\broller\b|derma ?stamp|skin stamp"),
 ("Body / slimming", r"cavitation|pressotherapy|lymphatic|vacuum|slimming|body contour|emsculpt|tesla|radial shockwave|shockwave"),
 ("Clinic furniture", r"couch|\bchair\b|\bstool\b|trolley|cabinet|\bbed\b|\btable\b|mobile base|armrest|headrest\b"),
 ("Steriliser / autoclave", r"autoclave|steril[iy][sz]er|uv cabinet|uv steril"),
 ("Fridge / cooling", r"fridge|refriger|medical cool"),
 ("Lamp / magnifier / loupe", r"\blamp\b|magnif|loupe|examination light|ring light"),
 ("Device accessory / part", r"hand\s*piece|handpiece|\bcable\b|footswitch|foot switch|electrode|\bspare\b|\bpart\b|holder|\btips?\b|applicator tip|spectacles|goggle|shade|solution\b|drain bottle"),
]
KIND = [("consumable (tip/cartridge)", r"\btips?\b|cartridge|needle module|consumable|pack of|disposable|treatment pack|applicator"),
        ("accessory / part", r"hand\s*piece|handpiece|cable|footswitch|electrode|spare|holder|footswitch|goggle|spectacles|shade|drain bottle|solution"),
        ("machine / device", r"machine|device|system|platform|console|unit\b|generator")]
NOISE = {"the", "with", "for", "and", "buy", "uk", "new", "pro", "plus", "available", "on", "request", "stock", "item",
         "vat", "payable", "zero", "prescription", "x", "set", "ltd", "medical", "aesthetic", "clinic", "professional",
         "disposable", "sterile", "of", "pack", "box", "size", "standard", "each", "per", "treatment"}


def misfiled(t):
    for rx, where in MISFILED:
        if re.search(rx, t, re.I): return where
    return ""


def subtype(t):
    for name, rx in SUBTYPES:
        if re.search(rx, t, re.I): return name
    return "Equipment (other)"


def kind_of(t):
    for name, rx in KIND:
        if re.search(rx, t, re.I): return name
    return "machine / device"


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


def main():
    rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8"))
            if r["category"] == "Devices & equipment" and r["scope"] == "Phase 1"]
    maps, prods = [], {}
    for r in rows:
        title = r["title"] if not r["title"].isdigit() else (r["page_title"] or r["title"])
        if not title.strip():
            maps.append(dict(r, code="", sub="", kind="", brand="", decision="no title", confidence="review")); continue
        mf = misfiled(title)
        if mf:
            maps.append(dict(r, code="", sub="(re-file)", kind="", brand=brand_of(title),
                             decision=f"not an aesthetic device - {mf}", confidence="re-file")); continue
        sub = subtype(title)
        kind = kind_of(title)
        brand = brand_of(title)
        core = namecore(title, brand)
        code = slug(brand[:16], core[:34], {"consumable (tip/cartridge)": "TIP", "accessory / part": "PART"}.get(kind, ""))
        if not code:
            maps.append(dict(r, code="", sub=sub, kind=kind, brand=brand, decision="could not parse - review", confidence="review")); continue
        conf = "high" if (sub != "Equipment (other)" and core) else ("rule" if core else "partial")
        maps.append(dict(r, code=code, sub=sub, kind=kind, brand=brand, decision=f"{sub}; {kind}; {brand} {core}", confidence=conf))
        p = prods.setdefault(code, dict(code=code, subtype=sub, kind=kind, brand=brand, name=core, suppliers=set(), listings=0))
        p["suppliers"].add(r["supplier"]); p["listings"] += 1
    for p in prods.values():
        p["supplier_n"] = len(p["suppliers"]); p["suppliers"] = len(p["suppliers"])
    out = ROOT / "catalogue/final"; out.mkdir(parents=True, exist_ok=True)
    pc = ["code", "subtype", "kind", "brand", "name", "supplier_n", "listings"]
    with open(out / "device_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc, extrasaction="ignore"); w.writeheader()
        w.writerows(sorted(prods.values(), key=lambda p: (p["subtype"], p["brand"], p["code"])))
    with open(out / "device_listing_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "supplier", "title", "url", "sub", "kind", "brand", "code", "confidence", "decision"], extrasaction="ignore")
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
    bykind = collections.Counter(p["kind"] for p in prods.values())
    multi = sum(1 for p in prods.values() if p["supplier_n"] > 1)
    refile = sum(1 for m in maps if m["confidence"] == "re-file")
    for t, b in [("Category 12 - Devices & equipment", True),
                 (f"{len(prods)} product codes from {len(maps)} listings across {len(set(m['supplier'] for m in maps))} suppliers.", False),
                 ("Equivalence group = modality/type. A 'kind' marks machine vs consumable (tip/cartridge) vs accessory/part. "
                  "Capital equipment is mostly list-only; the disposable device tips (e.g. RF microneedling cartridges) compare "
                  "where several suppliers carry them.", False),
                 (f"Kinds: {dict(bykind)}. {multi} codes multi-supplier (compare).", False),
                 (f"{refile} listings were flagged as NOT aesthetic equipment (IUDs, respiratory spacers, x-ray, air purifiers, "
                  "home test kits) and should be re-filed - see the Re-file sheet; they are not coded here.", False),
                 ("Subtypes: " + ", ".join(f"{k} ({v})" for k, v in bysub.most_common()), False),
                 (f"Confidence: high {cnt['high']}, rule {cnt['rule']}, partial {cnt['partial']}, review {cnt['review']}, re-file {refile}. "
                  "Sheets: By type | Products | Listings | Re-file.", True)]:
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=12 if b else 10, bold=b)
    rd.column_dimensions["A"].width = 150

    ss = wb.create_sheet("By type")
    head(ss, ["Modality / type", "Codes", "Listings", "Multi-supplier"], [34, 9, 10, 14])
    agg = collections.defaultdict(lambda: [0, 0, 0])
    for p in prods.values():
        a = agg[p["subtype"]]; a[0] += 1; a[1] += p["listings"]; a[2] += (1 if p["supplier_n"] > 1 else 0)
    for sb, _ in bysub.most_common():
        a = agg[sb]; ss.append([sb, a[0], a[1], a[2]]); fmt(ss)

    ps = wb.create_sheet("Products")
    head(ps, ["Code", "Modality / type", "Kind", "Brand", "Name", "Suppliers", "Listings"], [34, 28, 24, 16, 34, 9, 8])
    for p in sorted(prods.values(), key=lambda p: (-p["supplier_n"], p["subtype"], p["brand"], p["code"])):
        ps.append([p[k] for k in pc]); fmt(ps)
    ls = wb.create_sheet("Listings")
    head(ls, ["Code", "Modality", "Kind", "Supplier", "Listing (link)", "Confidence", "How decided"], [34, 24, 22, 16, 48, 12, 34])
    FILL = {"high": "C6EFCE", "rule": "DDEBF7", "partial": "FFF2CC", "review": "F8CBAD", "re-file": "D9D9D9"}
    for m in sorted([m for m in maps if m["code"]], key=lambda m: (m["sub"], m["code"], m["supplier"])):
        ls.append([m["code"], m["sub"], m["kind"], m["supplier"], m["title"], m["confidence"], m["decision"]]); fmt(ls); link(ls, 5, m["url"])
        ls.cell(row=ls.max_row, column=6).fill = PatternFill("solid", fgColor=FILL.get(m["confidence"], "FFFFFF"))
    ls.auto_filter.ref = f"A1:G{ls.max_row}"
    rf = wb.create_sheet("Re-file")
    head(rf, ["Supplier", "Listing (link)", "Where it belongs"], [18, 60, 40])
    for m in [m for m in maps if m["confidence"] in ("re-file", "review")]:
        rf.append([m["supplier"], m["title"], m["decision"]]); fmt(rf); link(rf, 2, m["url"])
    p = ROOT / "output/category_12_devices.xlsx"; wb.save(p); print(p)
    print(len(prods), "codes |", dict(cnt), "| multi:", multi, "| re-file:", refile)
    print("subtypes:", dict(bysub))
    print("Equipment (other):", sum(1 for m in maps if m["sub"] == "Equipment (other)"))


if __name__ == "__main__":
    main()
