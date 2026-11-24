"""Standalone 'what changed' workbook for the biostimulator review round (owner can audit every edit).
Hand-authored change log of the fixes applied after the owner's review notes. Usage: python -I scripts/biostim_changes_report.py"""
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
F = "Arial"
HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
SM, WRAP = Font(name=F, size=9), Alignment(wrap_text=True, vertical="top")
GRP = Font(name=F, bold=True, size=10)

# (Area, Product / item, Before, After, Why / rule)
ROWS = [
 ("NAME — unit count", "AestheFill", "AestheFill (bare name)", "AestheFill (1 x 200mg)", "Rule: if the name has mg/ml, show the unit count too (even 1)."),
 ("NAME — unit count", "Radiesse", "Radiesse (1.5ml)", "Radiesse (1 x 1.5ml)", "Same rule applied to every product with mg/ml."),
 ("NAME — unit count", "Sculptra", "Sculptra (367.5mg)", "Sculptra (1 x 367.5mg)", "Same rule."),
 ("NAME — commercial name", "HArmonyCa", "HArmonyCa (CaHA in HA gel 1.25ml x2 +lido)", "HArmonyCa with Lidocaine (2 x 1.25ml)", "Use the real market name (80% of pharmacies), not a synthesised spec string."),
 ("NAME — incomplete", "StiCol", "StiCol (bare, no spec)", "StiCol Volume (1 x 365mg)", "Reference gave it a strength; name must be complete."),
 ("LIDOCAINE — wrong split", "Radiesse (non-lido listings)", "'radiesse 15ml without lidocaine' was inside the +lidocaine product", "moved to Radiesse (1 x 1.5ml)", "Detection now respects negation: 'non lido' / 'without lidocaine' = NO lidocaine."),
 ("PACK — single vs twin", "Sculptra", "'Sculptra Twin Vial' and '2x5ml' were in the single-vial product", "moved to Sculptra (2 x 367.5mg)", "Read 'Twin Vial' = 2 and normalise the x symbol so 2x5ml is detected."),
 ("REFERENCE — found", "iLLUMA PLLA 200 / 500", "no reference link (flagged)", "LINKUS GLOBAL portfolio link added (unflagged)", "Owner supplied the reference link."),
 ("REFERENCE — found", "StiCol", "no reference (flagged)", "Contac Korea (sticolfiller.com)", "Research found the maker."),
 ("NAME SOURCE", "PLLACELL", "'pharmacy consensus (no brand reference link)'", "'pharmacy consensus: Ask Pharmacy, Kiss, LPG'", "Owner: no maker exists, so list the pharmacies the name came from."),
 ("CATEGORY MOVE", "Doublyx Evo", "Biostimulator", "Skin booster / PN / mesotherapy", "Research: non-crosslinked HA (Xcelens), a booster - not a collagen stimulator."),
 ("CATEGORY MOVE", "Linerase Hydro (+ 3 bundles)", "Biostimulator", "Skin booster / PN / mesotherapy", "HA booster (Mastelli), not a collagen stimulator."),
 ("CATEGORY MOVE", "Elysiha Face / Eyes", "Biostimulator", "Skincare, haircare & peels", "elysiha.com: topical serum (Caromed Italia) PDRN+HA+collagen - not injectable."),
 ("KEPT (owner decision)", "HArmonyCa, Neauvia Stimulate", "flagged hybrid (CaHA+HA)", "kept in Biostimulator", "Owner: keep here for now, move later if wanted."),
 ("KEPT (owner decision)", "PLLACELL (1 x 100mg)", "flagged (no maker)", "kept in Biostimulator with this name", "Owner: keep the name as is."),
 ("NEW COLUMN", "every category Excel", "(none)", "'Name reference' column on Products + Listings-per-product tabs", "Owner can audit where each product's name was decided."),
]

wb = Workbook(); ws = wb.active; ws.title = "Biostimulator changes"
cols = ["Area", "Product / item", "Before", "After", "Why / rule"]
widths = [24, 30, 44, 40, 56]
ws.append(cols)
for j, w in enumerate(widths, 1):
    c = ws.cell(row=1, column=j); c.font, c.fill, c.alignment = HF, HFILL, WRAP
    ws.column_dimensions[get_column_letter(j)].width = w
ws.freeze_panes = "A2"
fills = {"NAME": "FFF2CC", "LIDO": "FCE4D6", "PACK": "FCE4D6", "REFE": "E2EFDA", "NAME S": "E2EFDA",
         "CATE": "DDEBF7", "KEPT": "EDEDED", "NEW ": "E2EFDA"}
for area, item, before, after, why in ROWS:
    ws.append([area, item, before, after, why])
    key = area[:4]
    fill = next((v for k, v in fills.items() if area.upper().startswith(k.upper())), "FFFFFF")
    for c in ws[ws.max_row]:
        c.font, c.alignment = SM, WRAP
        c.fill = PatternFill("solid", fgColor=fill)
ws.auto_filter.ref = f"A1:E{ws.max_row}"

out = ROOT / "output/biostim_CHANGES.xlsx"
wb.save(out)
print("wrote", out, "-", len(ROWS), "changes")
