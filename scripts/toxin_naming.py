"""Apply the Botulinum Toxin naming standard to the toxin listings (non-destructive report).
Builds the Canonical Product Title (brand + official strength + official unit, NO pack) and the standardised
Supplier Listing Title (canonical + the pack THAT pharmacy sells; UNKNOWN pack -> no pack shown + flagged), keeping
each supplier's raw title unchanged. Official unit per brand's potency system (Speywood kept; nothing force-converted
to IU; Units/ml kept distinct from Units/vial). Output: output/toxin_naming_standard.xlsx.
Usage: python -I scripts/toxin_naming.py"""
import csv, re
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"

# Official product truth per brand (manufacturer SmPC): unit label, potency system, form, and liquid concentration.
POWDER = "Powder for solution for injection"
LIQUID = "Solution for injection"
OFFICIAL = {
 "Botox":     dict(mol="onabotulinumtoxinA",  system="Allergan Units",  unit="Units",            form=POWDER, liquid=False),
 "Azzalure":  dict(mol="abobotulinumtoxinA",  system="Speywood",        unit="Speywood Units",   form=POWDER, liquid=False),
 "Dysport":   dict(mol="abobotulinumtoxinA",  system="Speywood",        unit="Speywood Units",   form=POWDER, liquid=False),
 "Bocouture": dict(mol="incobotulinumtoxinA", system="Merz Units",      unit="Units",            form=POWDER, liquid=False),
 "Xeomin":    dict(mol="incobotulinumtoxinA", system="Merz Units",      unit="Units",            form=POWDER, liquid=False),
 "Letybo":    dict(mol="letibotulinumtoxinA", system="Units",           unit="Units",            form=POWDER, liquid=False),
 "Nuceiva":   dict(mol="prabotulinumtoxinA",  system="Units",           unit="Units",            form=POWDER, liquid=False),
 # liquids: official label is a CONCENTRATION (Units/ml), kept distinct from total units/vial
 "Alluzience": dict(mol="abobotulinumtoxinA", system="Speywood",        unit="Speywood Units/ml", form=LIQUID, liquid=True,
                    conc="200", vial_ml="0.625ml", total_per_vial="125"),
 "Relfydess":  dict(mol="relabotulinumtoxinA", system="Units",          unit="Units/ml",         form=LIQUID, liquid=True,
                    conc="100", vial_ml="1.5ml", total_per_vial="150"),
}
SPELL = {"bocouture": "Bocouture", "azzalure": "Azzalure", "alluzience": "Alluzience", "nuceiva": "Nuceiva"}


def canonical(brand, units):
    o = OFFICIAL.get(brand)
    if not o:
        return f"{brand} {units} Units", "Units", units
    if o["liquid"]:
        return f'{brand} {o["conc"]} {o["unit"]}', o["unit"], o["conc"]
    return f'{brand} {units} {o["unit"]}', o["unit"], units


def pack_from_decision(dec):
    m = re.search(r"pack (\d+) \(([^)]*)\)", dec or "")
    if not m:
        return None, "UNKNOWN"
    n, src = int(m.group(1)), m.group(2)
    if "assumed" in src or "not stated" in src:
        return None, "UNKNOWN (not stated by this pharmacy)"
    if n > 10:
        return None, f"UNKNOWN (implausible pack {n})"
    return n, f"from {src}"


def main():
    prods = {r["code"]: r for r in csv.DictReader(open(FINAL / "toxin_products.csv", encoding="utf-8"))}
    rows = []
    for m in csv.DictReader(open(FINAL / "toxin_listing_map.csv", encoding="utf-8")):
        if m.get("matched") != "reference":
            continue
        p = prods.get(m["code"], {})
        brand = p.get("brand", "")
        o = OFFICIAL.get(brand, {})
        units = p.get("units_per_vial", "")
        canon, unit_label, strength = canonical(brand, units)
        n, pstat = pack_from_decision(m.get("decision", ""))
        listing_title = canon + (f" – {n} Vial{'s' if n and n > 1 else ''}" if n else "")
        rows.append({
            "supplier": m["supplier"], "supplier_raw_title": m["title"],
            "canonical_product_title": canon, "supplier_listing_title": listing_title,
            "brand_name": brand, "active_ingredient": o.get("mol", ""), "toxin_type": "Botulinum toxin type A",
            "strength_value": strength, "strength_unit": unit_label, "potency_unit_system": o.get("system", ""),
            "dosage_form": o.get("form", ""), "vial_volume_ml": o.get("vial_ml", ""),
            "total_units_per_vial": o.get("total_per_vial", "" if o.get("liquid") else units),
            "pack_quantity": (n if n else "UNKNOWN"), "pack_status": pstat,
            "evidence_source": p.get("source", ""), "verification_status": "UNKNOWN pack" if not n else "reference-matched",
        })

    # workbook
    F = "Arial"
    HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
    SM, WRAP = Font(name=F, size=9), Alignment(wrap_text=True, vertical="top")
    wb = Workbook(); ws = wb.active; ws.title = "Toxin naming standard"
    cols = ["Supplier", "Supplier RAW title (kept)", "➡ Canonical Product Title", "➡ Supplier Listing Title (standardised)",
            "Strength", "Unit (official)", "Potency system", "Form", "Vial ml", "Total units/vial",
            "Pack qty", "Pack status", "Verification"]
    widths = [16, 40, 30, 36, 9, 18, 16, 30, 9, 13, 9, 30, 16]
    ws.append(cols)
    for j, w in enumerate(widths, 1):
        c = ws.cell(row=1, column=j); c.font, c.fill, c.alignment = HF, HFILL, WRAP
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A2"
    for r in sorted(rows, key=lambda r: (r["brand_name"], r["strength_value"], r["supplier"])):
        ws.append([r["supplier"], r["supplier_raw_title"], r["canonical_product_title"], r["supplier_listing_title"],
                   r["strength_value"], r["strength_unit"], r["potency_unit_system"], r["dosage_form"],
                   r["vial_volume_ml"], r["total_units_per_vial"], r["pack_quantity"], r["pack_status"], r["verification_status"]])
        for c in ws[ws.max_row]:
            c.font, c.alignment = SM, WRAP
        if r["pack_quantity"] == "UNKNOWN":
            ws.cell(row=ws.max_row, column=11).fill = PatternFill("solid", fgColor="FFEB9C")
    ws.auto_filter.ref = f"A1:M{ws.max_row}"

    # a compact Canonical-products summary tab
    cp = wb.create_sheet("Canonical products")
    cp.append(["Canonical Product Title", "Unit (official)", "Form", "Listings"])
    for c in cp[1]: c.font, c.fill = HF, HFILL
    import collections
    cc = collections.Counter(r["canonical_product_title"] for r in rows)
    meta = {r["canonical_product_title"]: r for r in rows}
    for name, n in sorted(cc.items()):
        mr = meta[name]
        cp.append([name, mr["strength_unit"], mr["dosage_form"], n])
        for c in cp[cp.max_row]: c.font = SM
    for col, w in zip("ABCD", [34, 18, 30, 9]):
        cp.column_dimensions[col].width = w

    out = ROOT / "output/toxin_naming_standard.xlsx"
    wb.save(out)
    unknown = sum(1 for r in rows if r["pack_quantity"] == "UNKNOWN")
    print(f"wrote {out} | {len(rows)} listings | {len(cc)} canonical products | {unknown} UNKNOWN pack")


if __name__ == "__main__":
    main()
