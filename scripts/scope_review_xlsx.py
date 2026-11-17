"""Scope review workbook: one row per category with proposed display mode, plus every product (link) by category.
Usage: python -I scripts/scope_review_xlsx.py"""
import collections, csv
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
F = "Arial"
HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
COMPARE = "Compare prices (same product code across suppliers)"
BROWSE = "Browse & choose (many brands, buyer picks)"
MODE = {
    "Toxin": COMPARE, "Dermal filler": COMPARE, "Skin booster / polynucleotide / mesotherapy": COMPARE,
    "Biostimulator": COMPARE, "Fat dissolving": COMPARE, "PDO threads": COMPARE,
    "Medicine - injectable / anaesthetic / emergency": COMPARE, "Medicine - oral": COMPARE,
    "Medicine - topical / eye / other": COMPARE, "Weight-loss medicine": COMPARE, "Vaccine": COMPARE,
    "Vitamin & IV therapy": COMPARE, "Skincare, haircare & peels": COMPARE + " - branded lines",
    "Supplements": COMPARE + " - branded lines",
    "Needles, cannulas & syringes": BROWSE + "; compare when same brand+size",
    "Clinic consumables & PPE": BROWSE + "; compare when same brand+size",
    "Devices & equipment": BROWSE, "Beauty (nails, brows, lashes, PMU, makeup)": BROWSE,
    "Training, services & marketing": "Not a product to stock - suggest leave out",
    "Not a product": "Leave out (pages that are not products)", "Unclassified": "Check by hand",
}

def head(ws, cols, widths):
    ws.append(cols)
    for j, w in enumerate(widths, 1):
        c = ws.cell(row=1, column=j); c.font, c.fill = HF, HFILL
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A2"

rows = list(csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8")))
by = collections.defaultdict(list)
for r in rows: by[r["category"]].append(r)
wb = Workbook(); ws = wb.active; ws.title = "Categories"
head(ws, ["Category", "Listings", "Suppliers", "Proposed display", "Examples", "Your decision", "Your note"], [38, 9, 9, 46, 80, 16, 40])
dv = DataValidation(type="list", formula1='"Include,Exclude,Discuss"', allow_blank=True); ws.add_data_validation(dv)
for cat, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
    ex = list(dict.fromkeys(r["page_title"] or r["title"] for r in rs))[:6]
    ws.append([cat, len(rs), len({r["supplier"] for r in rs}), MODE.get(cat, ""), " | ".join(ex), "", ""])
    dv.add(f"F{ws.max_row}")
    for c in ws[ws.max_row]:
        c.font = Font(name=F, size=9); c.alignment = Alignment(wrap_text=True, vertical="top")
ap = wb.create_sheet("All products")
cols = ["Category", "Supplier", "Product (link)", "Supplier's own category", "Confidence"]
head(ap, cols, [34, 20, 60, 40, 11])
for r in sorted(rows, key=lambda r: (r["category"], (r["page_title"] or r["title"]).lower())):
    ap.append([r["category"], r["supplier"], r["page_title"] or r["title"], r["supplier_category"], r["confidence"]])
    for c in ap[ap.max_row]: c.font = Font(name=F, size=9)
    c = ap.cell(row=ap.max_row, column=3); c.hyperlink = r["url"]; c.font = Font(name=F, size=9, color="0563C1", underline="single")
ap.auto_filter.ref = f"A1:E{ap.max_row}"
out = ROOT / "output/scope_review.xlsx"; wb.save(out); print(out, len(rows))
