"""Category 2 - Biostimulators: catalogue + listing map.
Biostimulators are CE-marked medical devices, so there is no single UK register like emc. The reference below gives each
brand's active agent (the equivalence group), manufacturer and standard presentation, with a 'verified' flag:
  verified=True  -> well-documented major brand (agent certain);
  verified=False -> niche brand, agent taken from the product name / supplier page - mark 'confirm with manufacturer'.
Each listing's pack / volume / strength / lidocaine is read from the title, then every page tab, then the product image
(scripts/page_facts, owner rules 2026-11-18); nothing found -> smallest pack, flagged.
Outputs: catalogue/final/biostim_products.csv, biostim_listing_map.csv, output/category_02_biostimulator.xlsx
Usage: python -I scripts/biostim_catalogue.py"""
import collections, csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_facts import page_text, labelled_fields, image_text
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent

# agent -> equivalence group label shown to buyers
GROUP = {
    "PLLA": "PLLA - poly-L-lactic acid",
    "PDLLA": "PDLLA - poly-D,L-lactic acid (± HA)",
    "CaHA": "CaHA - calcium hydroxylapatite",
    "CaHA+HA": "CaHA + HA hybrid",
    "PCL": "PCL - polycaprolactone",
    "collagen": "Injectable collagen stimulator",
    "HA booster": "HA skin booster (not a biostimulator)",
    "unknown": "Unconfirmed - ask the supplier",
}
# brands with a single standard strength -> use it instead of whatever the page happens to say
FIXED_MG = {"Sculptra": "367.5", "Ecolla": "365", "aesPLLA": "365", "PLLACELL": "100", "Julaine": "150",
            "StiCol": "365", "AestheFill": "200", "Lenisna": "200", "Linerase": "100", "PiNkLLA": "100"}
# brand regex (specific first) -> (canonical, agent, manufacturer, verified, variant_kind, note)
# variant_kind: "mg" strength in mg | "ml" volume | "letter" model letter (Ellanse) | "VX" Lanluma | "fixed"
BRANDS = [
 (r"harmonyca|harmony ?ca", ("HArmonyCa", "CaHA+HA", "Allergan / AbbVie", True, "fixed", "CaHA microspheres in HA gel, with lidocaine; 2 x 1.25 ml")),
 (r"radiesse", ("Radiesse", "CaHA", "Merz", True, "ml", "CaHA 30% in gel carrier; 0.8 / 1.5 / 3.0 ml; ± lidocaine (Radiesse+)")),
 (r"\bnovuma\b", ("Novuma", "CaHA", "Burgeon (Korea), Vivacy UK", True, "ml", "CaHA microspheres 55-60% in CMC gel (verified: CaHA)")),
 (r"sculptra", ("Sculptra", "PLLA", "Galderma", True, "mg", "PLLA 367.5 mg per vial; single or 2-vial pack")),
 (r"lanluma", ("Lanluma", "PLLA", "Sinclair", True, "VX", "PLLA; V = 210 mg / 15 ml (face), X = 630 mg / 40 ml (body)")),
 (r"ellans[eé]", ("Ellanse", "PCL", "Sinclair", True, "letter", "PCL microspheres; S/M/L/E by longevity; 1 ml vials")),
 (r"\bgouri\b", ("Gouri", "PCL", "APAD / Gran Aesthetics", True, "fixed", "liquid PCL; 1 x 1 ml")),
 (r"aesthefill|aesthe ?fill", ("AestheFill", "PDLLA", "Regen Biotech", True, "mg", "PDLLA powder 200 mg, reconstituted")),
 (r"juvelook|juve ?look", ("Juvelook", "PDLLA", "VAIM / Medit", True, "mg", "PDLLA + HA; 50 mg (Juvelook) / 200 mg (Juvelook Volume)")),
 (r"lenisna", ("Lenisna", "PDLLA", "Medit / Fillmed", True, "mg", "PDLLA + HA 200 mg")),
 (r"ecolla", ("Ecolla", "PLLA", "Korea (not named)", True, "mg", "PLLA powder, 365 mg vial (verified: PLLA)")),
 (r"pllacell", ("PLLACELL", "PLLA", "Korea (not named)", True, "mg", "PLLA + polynucleotide hybrid cocktail (PLLA ~35mg + PN + glutathione + vit C + HA), 100 mg total (verified: PLLA-based)")),
 (r"\bjulaine\b", ("Julaine", "PLLA", "Nordberg Medical (Sweden)", True, "mg", "PLLA 150 mg + CMC (verified: PLLA)")),
 (r"sticol", ("StiCol", "PLLA", "not named", True, "mg", "PLLA (+ HA); StiCol Soft / Volume (verified: PLLA)")),
 (r"\bolidia\b", ("Olidia", "PLLA", "Korea (PRP Science)", True, "mg", "PLLA powder, 365 mg vial (verified: PLLA)")),
 (r"illuma plla|\billuma\b", ("iLLUMA PLLA", "PLLA", "not named", True, "mg", "PLLA + CMC; 200 / 500 mg (verified: PLLA)")),
 (r"pinklla", ("PiNkLLA", "PLLA", "Daesung (Korea)", True, "mg", "PLLA + polynucleotide, 100 mg (verified: PLLA-based)")),
 (r"aes ?plla", ("aesPLLA", "PLLA", "Oreon Life Science (Korea)", True, "mg", "PLLA 150 mg + CMC + mannitol, 365 mg powder (verified: PLLA)")),
 (r"linerase hydro", ("Linerase Hydro", "HA booster", "Mastelli", True, "ml", "HA booster, 5 x 5 ml - not a collagen stimulator (grouped separately)")),
 (r"linerase", ("Linerase", "collagen", "Mastelli", True, "mg", "heterologous Type I collagen of EQUINE origin, 100 mg powder (verified: collagen, equine - not porcine)")),
 (r"neauvia.*stimulate|organic stimulate", ("Neauvia Stimulate", "CaHA+HA", "Matex Lab / Neauvia", True, "ml", "PEG-crosslinked HA ~26 mg/ml + 1% CaHA + glycine + L-proline (verified: CaHA + HA)")),
 (r"doublyx", ("Doublyx Evo", "unknown", "not stated", False, "ml", "agent not stated on the page - confirm with supplier")),
 (r"elysiha", ("Elysiha", "unknown", "not stated", False, "fixed", "agent not stated on the page - confirm with supplier")),
]
NOT_PRODUCT = [
 ("bundle / multi-buy offer", r"^\s*buy\b|\bget 1\b|\+ 1x|\bbundle\b|mix and match"),
 ("training -> Training", r"\btraining\b"),
]


def brand_of(t):
    for rx, info in BRANDS:
        if re.search(rx, t): return info
    return None


def num(txt, pat):
    m = re.search(pat, txt)
    return m.group(1) if m else None


def facts(title, pid):
    """Return (pack_vials, how, volume_ml, strength_mg, lidocaine) from title, then page tabs, then image."""
    t = title.lower()
    page = page_text(pid).lower()
    full = t + " || " + page
    lido = bool(re.search(r"lido|lidocaine|\+ ?lido|plus lido", t)) or ("with lidocaine" in page[:400])
    # volume ml (avoid matching '15ml' as 5; require a boundary)
    vol = num(t, r"(\d(?:\.\d+)?)\s*(?:cc|ml)\b") or num(page[:400], r"(\d(?:\.\d+)?)\s*(?:cc|ml)\b")
    mg = num(t, r"(\d{2,4}(?:\.\d+)?)\s*mg") or num(page[:400], r"(\d{2,4}(?:\.\d+)?)\s*mg")
    # pack (vials/syringes)
    pk, how = None, ""
    for src, txt in (("title", t), ("page", page)):
        m = re.search(r"\b(\d)\s*x\s*\d*\.?\d*\s*(?:ml|mg|vial|syringe|cc)|\b(\d)\s*(?:vials?|syringes?)\b|\btwin\b|\bdual\b|\bsingle\b", txt)
        if m:
            g = next((x for x in m.groups() if x), None)
            pk = int(g) if g else (2 if ("twin" in m.group(0) or "dual" in m.group(0)) else 1)
            how = f"pack from {src}"; break
    if pk is None:
        o = image_text(pid).lower()
        m = re.search(r"\b(\d)\s*(?:x|vials?|syringes?)\b", o)
        if m: pk, how = int(m.group(1)), "pack from image"
    if pk is None: pk, how = 1, "pack not stated - assumed 1 (owner rule)"
    return pk, how, vol, mg, lido


def code(brand, variant, strength, pack, lido):
    parts = [re.sub(r"[^A-Z0-9]+", "", brand.upper())]
    if variant: parts.append(variant)
    if strength: parts.append(strength)
    if lido: parts.append("LIDO")
    parts.append(f"{pack}X")
    return "-".join(parts)


def main():
    rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8"))
            if r["category"] == "Biostimulator" and r["scope"] == "Phase 1"]
    maps, prods = [], {}
    for r in rows:
        title = r["title"] if not r["title"].isdigit() else (r["page_title"] or r["title"])
        tl = (title + " | " + (r["page_title"] if not r["page_title"].startswith("Dr. Adams") else "")).lower()
        np_ = next((lab for lab, rx in NOT_PRODUCT if re.search(rx, tl)), None)
        info = brand_of(tl)
        if np_ or not info:
            maps.append(dict(r, code="", brand=info[0] if info else "", group="", decision=np_ or "brand not recognised - review", confidence="review")); continue
        canon, agent, mah, verified, vkind, bnote = info
        pk, how, vol, mg, lido = facts(title, r["id"])
        variant, strength = "", ""
        if canon == "HArmonyCa":  # only one presentation on the UK market: 2 x 1.25 ml with lidocaine
            lido, strength = True, "1.25ML"
            if not re.search(r"\b1\s*x\b|single", tl): pk = 2
        if vkind == "letter":
            m = re.search(r"ellans[eé]\s*(s|m|l|e)\b|\b(short|medium|long|extralong|extra long)\b", tl)
            if m:
                variant = (m.group(1) or {"short": "S", "medium": "M", "long": "L", "extralong": "E", "extra long": "E"}.get(m.group(2), "")).upper()
            strength = (vol + "ML") if vol else ""
        elif vkind == "VX":
            variant = "V" if re.search(r"\bv\b|210|15\s*ml|face", tl) and not re.search(r"\bx\b|630|639|40\s*ml|body", tl) else ("X" if re.search(r"\bx\b|630|639|40\s*ml|body", tl) else "")
            strength = "210MG" if variant == "V" else ("630MG" if variant == "X" else "")
        elif vkind == "ml":
            if canon == "Radiesse":  # real volumes 0.8 / 1.5 / 3.0; fix "1 5ml"/"15ml" mis-parses
                v = "1.5" if re.search(r"1[.\s,]*5\s*(?:ml|cc)|1\.5", tl) else ("3" if re.search(r"\b3\s*(?:ml|cc)|3\.0", tl) else ("0.8" if "0.8" in tl else (vol if vol in ("0.8", "1.5", "3") else "1.5")))
                strength = v + "ML"
            else:
                strength = (vol + "ML") if vol else ""
        elif vkind == "mg":
            if canon == "Juvelook":
                variant, strength = ("VOLUME", "200MG") if re.search(r"volume|200", tl) else ("", "50MG")
            elif canon == "iLLUMA PLLA":
                strength = (num(tl, r"plla\s*(\d{2,4})") or num(tl, r"\b(200|500)\b") or "") + "MG"
            elif canon in FIXED_MG:
                strength = FIXED_MG[canon] + "MG"
            elif mg:
                strength = mg + "MG"
        c = code(canon, variant, strength, pk, lido)
        conf = "high" if "not stated" not in how else ("rule" if page_text(r["id"]) and r["page_status"] == "read" else "supplier to confirm")
        if not verified: conf = "high*" if conf == "high" else conf  # pack certain but agent to confirm
        maps.append(dict(r, code=c, brand=canon, group=GROUP[agent], decision=f"{how}" + ("" if verified else "; agent per name/page - confirm with manufacturer"), confidence=conf))
        prods.setdefault(c, dict(code=c, brand=canon, variant=variant, active_agent=agent, equivalence_group=GROUP[agent], manufacturer=mah,
                                 strength=strength, volume_ml=vol or "", vials_per_pack=pk, lidocaine="yes" if lido else "no",
                                 agent_verified="yes" if verified else "NO - confirm", note=bnote, suppliers=set(), listings=0))
        prods[c]["suppliers"].add(r["supplier"]); prods[c]["listings"] += 1
    for p in prods.values(): p["suppliers"] = len(p["suppliers"])

    out = ROOT / "catalogue/final"; out.mkdir(parents=True, exist_ok=True)
    pc = ["code", "brand", "variant", "active_agent", "equivalence_group", "manufacturer", "strength", "volume_ml", "vials_per_pack",
          "lidocaine", "agent_verified", "suppliers", "listings", "note"]
    with open(out / "biostim_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc); w.writeheader(); w.writerows(sorted(prods.values(), key=lambda p: (p["active_agent"], p["brand"], p["code"])))
    with open(out / "biostim_listing_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "supplier", "title", "url", "brand", "group", "code", "confidence", "decision", "page_status"], extrasaction="ignore")
        w.writeheader(); w.writerows(maps)

    # Excel
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
    for t, b in [("Category 2 - Biostimulators: catalogue", True),
                 (f"{len(prods)} product codes across {len(set(p['active_agent'] for p in prods.values()))} agent groups. {len(maps)} listings: "
                  f"high {cnt['high']}, high* {cnt['high*']} (pack certain, agent to confirm), rule {cnt['rule']} (page read, pack not stated -> smallest), "
                  f"supplier to confirm {cnt['supplier to confirm']}, review {cnt['review']}.", False),
                 ("Biostimulators are CE-marked devices - no central UK register like emc. Agent (PLLA / CaHA / PCL / PDLLA / collagen) is the", False),
                 ("equivalence group shown together in search. Major brands are verified; niche brands are marked 'agent to confirm'.", False),
                 ("Price per unit is compared only within the same brand (the amount of active agent per vial differs between brands).", False),
                 ("Sheets: Products (catalogue) | Listings (each listing -> code) | Review (no code). Your check: 'OK?' column in Listings.", True)]:
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=12 if b else 10, bold=b)
    rd.column_dimensions["A"].width = 150
    ps = wb.create_sheet("Products")
    head(ps, ["Code", "Brand", "Variant", "Active agent", "Equivalence group", "Manufacturer", "Strength", "Volume ml", "Vials/pack", "Lidocaine", "Agent verified", "Suppliers", "Listings", "Note"],
         [30, 14, 9, 10, 30, 22, 9, 8, 8, 9, 13, 9, 8, 40])
    for p in sorted(prods.values(), key=lambda p: (p["equivalence_group"], p["brand"], p["code"])):
        ps.append([p[k] for k in pc]); fmt(ps)
        if p["agent_verified"].startswith("NO"): ps.cell(row=ps.max_row, column=11).fill = PatternFill("solid", fgColor="FFF2CC")
    ls = wb.create_sheet("Listings")
    head(ls, ["Code", "Brand", "Equivalence group", "Supplier", "Listing (link)", "Confidence", "How decided", "OK?"], [30, 13, 30, 18, 52, 12, 44, 7])
    FILL = {"high": "C6EFCE", "high*": "E2EFDA", "rule": "DDEBF7", "supplier to confirm": "FFF2CC", "review": "F8CBAD"}
    for m in sorted([m for m in maps if m["code"]], key=lambda m: (m["group"], m["brand"], m["code"], m["supplier"])):
        ls.append([m["code"], m["brand"], m["group"], m["supplier"], m["title"], m["confidence"], m["decision"], ""]); fmt(ls); link(ls, 5, m["url"])
        ls.cell(row=ls.max_row, column=6).fill = PatternFill("solid", fgColor=FILL.get(m["confidence"], "FFFFFF"))
    ls.auto_filter.ref = f"A1:H{ls.max_row}"
    rv = wb.create_sheet("Review")
    head(rv, ["Supplier", "Listing (link)", "Brand", "Why no code"], [18, 60, 14, 46])
    for m in [m for m in maps if not m["code"]]:
        rv.append([m["supplier"], m["title"], m["brand"], m["decision"]]); fmt(rv); link(rv, 2, m["url"])
    p = ROOT / "output/category_02_biostimulator.xlsx"; wb.save(p); print(p)
    print(len(prods), "codes |", dict(cnt))
    for c, p in sorted(prods.items()): print(f"  {c:34s} {p['listings']:3d}L {p['suppliers']:2d}S  {p['equivalence_group']}")
    for m in maps:
        if not m["code"]: print("  REVIEW", m["supplier"], "|", m["title"][:55], "|", m["decision"])


if __name__ == "__main__":
    main()
