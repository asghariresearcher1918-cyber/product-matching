"""Category 7 - Medicines (injectable/emergency, oral, topical/eye, vitamin & IV): catalogue + listing map.
Medicines are generics/brands identified by active molecule. Equivalence group = molecule + strength + form
(generics of the same molecule/strength/form are interchangeable; manufacturer/brand is an attribute - owner rule #2).
Source of truth: emc (and the NHS dm+d dictionary). Molecule taken from a brand->molecule map, else the generic name
in the listing. Strength / form / pack read from the title, then the page. Code = MOLECULE-STRENGTH-FORM-PACK.
Outputs: catalogue/final/medicine_products.csv, medicine_listing_map.csv, output/category_07_medicines.xlsx
Usage: python -I scripts/medicine_catalogue.py"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_facts import page_text
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
EMC = "https://www.medicines.org.uk/emc/search?q="

# brand -> active molecule (lower-case). Checked first; longest keys first.
BRAND2MOL = {
 "emla": "lidocaine + prilocaine", "lmx4": "lidocaine", "lmx 4": "lidocaine", "lmx": "lidocaine",
 "ametop": "tetracaine", "lignospan": "lidocaine + adrenaline", "xylocaine": "lidocaine", "xylonor": "lidocaine",
 "scandonest": "mepivacaine", "septanest": "articaine + adrenaline", "citanest": "prilocaine", "marcain": "bupivacaine",
 "kenalog": "triamcinolone", "adcortyl": "triamcinolone", "depo-medrone": "methylprednisolone", "depo medrone": "methylprednisolone",
 "fibrovein": "sodium tetradecyl sulfate", "aethoxysklerol": "polidocanol",
 "hyalase": "hyaluronidase", "disolvidase": "hyaluronidase (unlicensed)", "liporase": "hyaluronidase",
 "bacteriostatic": "sodium chloride (bacteriostatic)", "tor-bac": "sodium chloride (bacteriostatic)", "torbac": "sodium chloride (bacteriostatic)", "bac-stat": "sodium chloride (bacteriostatic)",
 "lumigan": "bimatoprost", "iopidine": "apraclonidine", "alphagan": "brimonidine", "azopt": "brinzolamide",
 "timoptol": "timolol", "xalatan": "latanoprost", "lacri-lube": "eye lubricant",
 "betnovate": "betamethasone", "dermovate": "clobetasol", "eumovate": "clobetasone", "elocon": "mometasone",
 "differin": "adapalene", "epiduo": "adapalene + benzoyl peroxide", "duac": "clindamycin + benzoyl peroxide",
 "treclin": "clindamycin + tretinoin", "zineryt": "erythromycin + zinc", "rozex": "metronidazole", "finacea": "azelaic acid",
 "skinoren": "azelaic acid", "soolantra": "ivermectin", "mirvaso": "brimonidine", "efudix": "fluorouracil",
 "fucidin": "fusidic acid", "fucibet": "fusidic acid + betamethasone", "bactroban": "mupirocin", "daktacort": "miconazole + hydrocortisone",
 "piriton": "chlorphenamine", "clarityn": "loratadine", "phenergan": "promethazine", "regaine": "minoxidil",
 "propecia": "finasteride", "proscar": "finasteride", "hirudoid": "heparinoid", "dermatix": "silicone gel",
 "glucagen": "glucagon", "glucogel": "glucose", "dextrogel": "glucose", "ventolin": "salbutamol", "salamol": "salbutamol",
 "epipen": "adrenaline", "jext": "adrenaline", "emerade": "adrenaline", "glyceryl trinitrate": "glyceryl trinitrate", "gtn": "glyceryl trinitrate",
 "buccastem": "prochlorperazine", "stemetil": "prochlorperazine", "maxolon": "metoclopramide", "zofran": "ondansetron",
 "augmentin": "co-amoxiclav", "keflex": "cefalexin", "zinnat": "cefuroxime", "vibramycin": "doxycycline", "tetralysal": "lymecycline",
 "roaccutane": "isotretinoin", "pabrinex": "vitamins B + C", "neo-cytamen": "hydroxocobalamin", "neocytamen": "hydroxocobalamin",
 "kenalog": "triamcinolone", "aknemycin": "erythromycin + tretinoin", "zindaclin": "clindamycin", "dalacin": "clindamycin",
}
FORMS = [
 ("ampoule", r"ampoule|\bamp\b|\bamps\b"), ("pre-filled syringe", r"pre-?filled syringe|\bpfs\b|syringe"),
 ("vial", r"\bvial\b|\bvials\b"), ("injection", r"injection|\binj\b|solution for inj|for injection"),
 ("eye drops", r"eye drops?|eye solution"), ("ear drops", r"ear drops?"), ("nasal spray", r"nasal spray|nasule"),
 ("inhaler", r"inhaler|evohaler|accuhaler|easyhaler|turbohaler|nebules?"), ("patch", r"patch(es)?|transdermal"),
 ("cream", r"\bcream\b"), ("ointment", r"ointment"), ("gel", r"\bgel\b"), ("lotion|foam", r"lotion|foam|solution.*scalp"),
 ("suppository|pessary", r"suppositor|pessar|rectal"), ("oral solution|suspension", r"oral (solution|suspension)|\bsyrup\b|elixir|linctus|suspension"),
 ("capsule", r"capsule|\bcaps?\b"), ("tablet", r"tablet|\btabs?\b|caplet|dispersible|soluble|lozenge|orodispersible|sublingual|effervescent"),
 ("spray", r"\bspray\b|pump spray"), ("powder", r"powder"), ("solution|infusion", r"\bsolution\b|infusion|\biv\b|bag\b|irrigation"),
]
NOISE = re.compile(r"\b(stock item|vat payable|prescription item|zero vat|on prescription|pom|expiry|exp\.?\w*|short dated|"
                   r"limited stock|unlicensed|single|pack of \d+|\bx\s*\d+|\d+'?s?\b|available on request|chilled item|"
                   r"mypharmacyspace|dr\.? adams pharmacy)\b", re.I)


GENERIC_FIX = {"co amoxiclav": "co-amoxiclav", "water for injection": "water for injection",
               "sodium chloride": "sodium chloride", "b hydroxocobalamin": "hydroxocobalamin",
               "b methylcobalamin": "methylcobalamin", "b cyanocobalamin": "cyanocobalamin"}


def molecule(title):
    t = title.lower()
    for b in sorted(BRAND2MOL, key=len, reverse=True):
        if re.search(r"\b" + re.escape(b), t): return BRAND2MOL[b], "brand->molecule"
    # drop a leading dose / percentage / volume / count so "0.9% Sodium Chloride" and "21 x co amoxiclav" parse
    g = re.sub(r"^\s*(?:(?:\d+(?:\.\d+)?\s*)?(?:%|w/v|w/w|mg|mcg|g|ml|iu|units?|x)\b\s*)+", " ", title, flags=re.I)
    g = re.sub(r"^\s*b\s*12\b", " b", g, flags=re.I)  # vitamin B12 forms: keep the molecule word that follows
    # generic: leading alphabetic name, cut at first number/paren, strip noise
    g = re.split(r"[\d(]", g, maxsplit=1)[0]
    g = NOISE.sub(" ", g)
    g = re.sub(r"[^A-Za-z +/&-]", " ", g)
    g = re.sub(r"\b(solution|injection|inj|for|bp|b\.p\.|the|with|and)\b", " ", g, flags=re.I)
    toks = [x for x in g.split() if len(x) > 1][:2]
    name = " ".join(toks).lower()
    name = GENERIC_FIX.get(name, name)
    return (name, "generic name") if name else ("", "")


INJECTABLE = {"ampoule", "vial", "injection", "pre-filled syringe"}


def form_of(t):
    for name, rx in FORMS:
        if re.search(rx, t, re.I):
            f = name.split("|")[0]
            return "injection" if f in INJECTABLE else f  # container (amp/vial) is an attribute, not a separate product
    return ""


def strength(t):
    t = t.replace(",", "")  # 300,000 iu -> 300000 iu
    m = (re.search(r"(\d+)\s*(mg|mcg)\s*/\s*(\d+(?:\.\d+)?)\s*ml", t, re.I)
         or re.search(r"(\d+(?:\.\d+)?)\s*(mcg|microgram|mg|g|%|iu|units?|mg/ml|mg/g)\b", t, re.I))
    if not m: return ""
    s = re.sub(r"\s+", "", m.group(0).lower()).replace("microgram", "mcg").replace("units", "u").replace("unit", "u")
    return canon_strength(s)


def topical_strength(t):
    """For creams/gels/ointments the strength is the %, not the tube weight (5g/30g = pack size)."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", t)
    return m.group(1).rstrip(".") + "%" if m else ""


def canon_strength(s):
    """Canonicalise weight to mg so 150mcg == 0.15mg, 1g == 1000mg. Concentrations / %, iu, u kept as-is."""
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(mcg|mg|g)", s)
    if not m: return s
    v, u = float(m.group(1)), m.group(2)
    mg = v / 1000 if u == "mcg" else (v * 1000 if u == "g" else v)
    return (f"{mg:.4f}".rstrip("0").rstrip(".")) + "mg"


def pack(t):
    m = (re.search(r"pack of\s*(\d+)", t, re.I) or re.search(r"\bx\s*(\d+)\b", t, re.I)
         or re.search(r"\b(\d+)\s*(?:tablets?|caps?|capsules?|amps?|ampoules?|vials?|x\s*\d)", t, re.I)
         or re.search(r"\(\s*(\d+)\s*x", t) or re.search(r"\b(\d+)'?s\b", t))
    return int(m.group(1)) if m else 1


def main():
    cats = {"Medicine - injectable / anaesthetic / emergency": "injectable/emergency", "Medicine - oral": "oral",
            "Medicine - topical / eye / other": "topical/eye", "Vitamin & IV therapy": "vitamin/IV", "Medicine (form not stated)": "other"}
    rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8"))
            if r["category"] in cats and r["scope"] == "Phase 1"]
    maps, prods = [], {}
    for r in rows:
        title = r["title"] if not r["title"].isdigit() else (r["page_title"] or r["title"])
        tl = title.lower()
        if re.search(r"emergency kit|complication kit|dissolving kit|anaphylaxis (kit|pack)", tl):
            maps.append(dict(r, code="", mol="", group="", decision="emergency kit (multi-item) - list, not a single code", confidence="kit")); continue
        mol, how = molecule(title)
        if not mol:
            maps.append(dict(r, code="", mol="", group="", decision="molecule not parsed - review", confidence="review")); continue
        cat = cats[r["category"]]
        form = form_of(tl)
        if not form:
            form = form_of(page_text(r["id"])[:400])
        if not form and re.search(r"\b(emla|lmx|xylonor|ametop|anesderm|denela|tetracaine|numbing)\b", tl):
            form = "cream"  # topical anaesthetic brands sold as a cream/gel; a bare "5g"/"30g" is the tube, not strength
        if cat == "injectable/emergency" and form in ("solution", ""):
            form = "injection"  # "solution for injection" / 1:1000 solution = an injection in this category
        topical = form in ("cream", "ointment", "gel", "lotion")
        st = topical_strength(tl) if topical else strength(tl)
        if not st:
            pg = page_text(r["id"])[:400]
            st = topical_strength(pg) if topical else strength(pg)
        pk = pack(tl)
        grp = mol
        parts = [re.sub(r"[^A-Z0-9]+", "", mol.upper())[:18]] + ([re.sub(r"[^A-Z0-9.%]+", "", st.upper())] if st else []) + ([re.sub(r"[^A-Z]+", "", form.upper())[:4]] if form else [])
        c = "-".join(p for p in parts if p) or re.sub(r"[^A-Z0-9]+", "", mol.upper())[:18]
        conf = "high" if st and form else ("rule" if st or form else "partial - check strength/form")
        maps.append(dict(r, code=c, mol=mol, group=grp, decision=f"{mol}; {st or '?'}; {form or '?'}; {how}", confidence=conf))
        prods.setdefault(c, dict(code=c, molecule=mol, equivalence_group=grp, strength=st, form=form, category=cats[r["category"]],
                                 source=EMC + mol.split()[0], suppliers=set(), listings=0, brands=set()))
        prods[c]["suppliers"].add(r["supplier"]); prods[c]["listings"] += 1
        prods[c]["brands"].add(re.split(r"[\d(]", title, maxsplit=1)[0].strip()[:24])
    # consolidation: a form-less code (molecule[+strength] only) folds into the single stated form of the same molecule+strength
    groups = collections.defaultdict(list)
    for p in prods.values():
        groups[(p["molecule"], p["strength"])].append(p)
    remap = {}
    for g in groups.values():
        blanks = [p for p in g if not p["form"]]
        stated = {p["form"]: p for p in g if p["form"]}
        if blanks and len(stated) == 1:
            tgt = next(iter(stated.values()))
            for b in blanks:
                remap[b["code"]] = tgt["code"]
                tgt["suppliers"] |= b["suppliers"]; tgt["listings"] += b["listings"]; tgt["brands"] |= b["brands"]
                del prods[b["code"]]
    for m in maps:
        if m.get("code") in remap:
            m["decision"] += " (form inferred from matched product)"; m["code"] = remap[m["code"]]
    for p in prods.values():
        p["suppliers"] = len(p["suppliers"]); p["brands"] = "; ".join(sorted(p["brands"])[:4])
    out = ROOT / "catalogue/final"; out.mkdir(parents=True, exist_ok=True)
    pc = ["code", "molecule", "equivalence_group", "strength", "form", "category", "brands", "suppliers", "listings", "source"]
    with open(out / "medicine_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc); w.writeheader(); w.writerows(sorted(prods.values(), key=lambda p: (p["molecule"], p["code"])))
    with open(out / "medicine_listing_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "supplier", "title", "url", "mol", "group", "code", "confidence", "decision", "category", "page_status"], extrasaction="ignore")
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
    for t, b in [("Category 7 - Medicines: catalogue", True),
                 (f"{len(prods)} product codes, {len(maps)} listings (injectable/emergency, oral, topical/eye, vitamin & IV).", False),
                 (f"high {cnt['high']}, rule {cnt['rule']} (strength or form only), partial {cnt['partial - check strength/form']}, emergency kit {cnt['kit']}, review {cnt['review']}.", False),
                 ("Equivalence group = active molecule + strength + form. Generics of the same molecule/strength/form are interchangeable; the brand/manufacturer is an attribute (owner rule). Branded drugs are mapped to their molecule (e.g. Kenalog -> triamcinolone, Emla -> lidocaine+prilocaine, Lumigan -> bimatoprost).", False),
                 ("All are POM (except a few pharmacy items) - price shown to verified professionals. Sheets: Products | Listings | Review.", True)]:
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=12 if b else 10, bold=b)
    rd.column_dimensions["A"].width = 150
    ps = wb.create_sheet("Products")
    head(ps, ["Code", "Molecule", "Strength", "Form", "Category", "Brands seen", "Suppliers", "Listings", "Source"],
         [26, 26, 12, 14, 18, 40, 9, 8, 14])
    for p in sorted(prods.values(), key=lambda p: (p["molecule"], p["strength"], p["code"])):
        ps.append([p[k] for k in pc if k != "equivalence_group"]); fmt(ps); link(ps, 9, p["source"])
    ls = wb.create_sheet("Listings")
    head(ls, ["Code", "Molecule", "Category", "Supplier", "Listing (link)", "Confidence", "How decided", "OK?"], [26, 24, 16, 16, 50, 16, 36, 7])
    FILL = {"high": "C6EFCE", "rule": "DDEBF7", "partial - check strength/form": "FFF2CC", "kit": "FCE4D6", "review": "F8CBAD"}
    for m in sorted([m for m in maps if m["code"]], key=lambda m: (m["mol"], m["code"], m["supplier"])):
        ls.append([m["code"], m["mol"], m["category"], m["supplier"], m["title"], m["confidence"], m["decision"], ""]); fmt(ls); link(ls, 5, m["url"])
        ls.cell(row=ls.max_row, column=6).fill = PatternFill("solid", fgColor=FILL.get(m["confidence"], "FFFFFF"))
    ls.auto_filter.ref = f"A1:H{ls.max_row}"
    rv = wb.create_sheet("Review and kits")
    head(rv, ["Supplier", "Listing (link)", "Why no code"], [18, 62, 42])
    for m in [m for m in maps if not m["code"]]:
        rv.append([m["supplier"], m["title"], m["decision"]]); fmt(rv); link(rv, 2, m["url"])
    p = ROOT / "output/category_07_medicines.xlsx"; wb.save(p); print(p)
    print(len(prods), "codes |", dict(cnt))
    top = collections.Counter()
    for m in maps:
        if m["code"]: top[m["mol"]] += 1
    print("top molecules:", ", ".join(f"{k}({v})" for k, v in top.most_common(15)))
    rev = [m for m in maps if m["confidence"] == "review"]
    print("review:", len(rev))
    for m in rev[:15]: print("  ", m["supplier"], "|", m["title"][:55])


if __name__ == "__main__":
    main()
