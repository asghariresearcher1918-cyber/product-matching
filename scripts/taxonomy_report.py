"""Phase-1 classification report for the v2 taxonomy migration (owner review before any production change).
Reads catalogue/final/taxonomy_v2.csv. Tabs: Summary, By category, All products (traceable), Review queue, Notes.
Usage: python -I scripts/taxonomy_report.py"""
import csv, collections
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"
F = "Arial"
HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
SM, WRAP = Font(name=F, size=9), Alignment(wrap_text=True, vertical="top")
BIG = Font(name=F, bold=True, size=12)
FILLS = {"CLASSIFIED": "C6EFCE", "REVIEW_REQUIRED": "FFEB9C", "PARKED": "D9D9D9"}

rows = list(csv.DictReader(open(FINAL / "taxonomy_v2.csv", encoding="utf-8")))


def head(ws, cols, widths):
    ws.append(cols)
    for j, w in enumerate(widths, 1):
        c = ws.cell(row=1, column=j); c.font, c.fill, c.alignment = HF, HFILL, WRAP
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A2"


wb = Workbook()
# --- Summary ---
s = wb.active; s.title = "Summary"
s["A1"] = "AestheticsProcure v2 taxonomy — phase-1 classification report"; s["A1"].font = BIG
st = collections.Counter(r["status"] for r in rows)
s.append([]); s.append(["Total products", len(rows)])
s.append(["Reviewed (all)", len(rows)])
s.append(["CLASSIFIED", st["CLASSIFIED"]])
s.append(["REVIEW_REQUIRED (needs your decision)", st["REVIEW_REQUIRED"]])
s.append(["PARKED (vaccines, phase 2)", st["PARKED"]])
s.append(["Unclassified (no mapping)", sum(1 for r in rows if not r["primary_category_id"])])
for i in range(2, s.max_row + 1):
    s.cell(row=i, column=1).font = Font(name=F, bold=True, size=10)
s.column_dimensions["A"].width = 42; s.column_dimensions["B"].width = 12

# --- By category / subcategory ---
bc = wb.create_sheet("By category")
head(bc, ["Primary ID", "Primary category", "Subcategory ID", "Subcategory", "Products", "Classified", "Review"], [12, 32, 14, 30, 11, 11, 9])
agg = collections.defaultdict(lambda: [0, 0, 0])
for r in rows:
    k = (r["primary_category_id"], r["primary_category"], r["subcategory_id"], r["subcategory"])
    agg[k][0] += 1
    agg[k][1] += (r["status"] == "CLASSIFIED")
    agg[k][2] += (r["status"] == "REVIEW_REQUIRED")
for (pid, pn, sid, sn), (tot, cl, rv) in sorted(agg.items()):
    bc.append([pid, pn, sid, sn, tot, cl, rv])
    for c in bc[bc.max_row]: c.font, c.alignment = SM, WRAP
bc.auto_filter.ref = f"A1:G{bc.max_row}"

# --- All products (full traceability) ---
ap = wb.create_sheet("All products")
cols = ["Product", "UID", "v1 category (old)", "v1 equivalence group", "Supplier category",
        "Primary ID", "Primary category", "Subcat ID", "Subcategory", "Status", "Reason", "Listings"]
head(ap, cols, [38, 22, 22, 24, 26, 10, 26, 10, 24, 16, 40, 8])
for r in rows:
    ap.append([r["product"], r["uid"], r["v1_category"], r["v1_equivalence_group"], r["supplier_category"],
               r["primary_category_id"], r["primary_category"], r["subcategory_id"], r["subcategory"],
               r["status"], r["reason"], r["listings"]])
    for c in ap[ap.max_row]: c.font, c.alignment = SM, WRAP
    ap.cell(row=ap.max_row, column=10).fill = PatternFill("solid", fgColor=FILLS.get(r["status"], "FFFFFF"))
ap.auto_filter.ref = f"A1:L{ap.max_row}"

# --- Review queue (grouped by reason) ---
rq = wb.create_sheet("Review queue")
head(rq, ["Reason", "v1 category", "Primary (proposed)", "Products", "Example products"], [44, 26, 26, 10, 60])
grp = collections.defaultdict(list)
for r in rows:
    if r["status"] == "REVIEW_REQUIRED":
        grp[(r["reason"], r["v1_category"], r["primary_category_id"])].append(r["product"])
for (reason, v1, pid), prods in sorted(grp.items(), key=lambda kv: -len(kv[1])):
    rq.append([reason, v1, pid, len(prods), " | ".join(prods[:4])])
    for c in rq[rq.max_row]: c.font, c.alignment = SM, WRAP
rq.auto_filter.ref = f"A1:E{rq.max_row}"

# --- Notes / deviations ---
nt = wb.create_sheet("Notes")
notes = [
 "Non-destructive migration: v1 'category' and supplier category are preserved; nothing deleted.",
 "Owner-approved deviations: Weight-loss = standalone top-level WLM (not C09.07); Vaccines PARKED for phase 2.",
 "Hair & scalp products moved out of old Skincare into C07.",
 "Level 3 (product type) left null except C01.01.01 Cross-linked HA Filler (only approved level-3 type).",
 "REVIEW_REQUIRED = the primary category needs your confirmation; these are NOT guessed and NOT yet shown on the site.",
 "v1 is frozen at git tag catalogue-v1 and output/site/basis_v1_15cat.html; v2 is built separately.",
 "Next: category-by-category deep verification (names/listings/subcategories), same method as the biostimulator pass.",
]
for i, t in enumerate(notes, 1):
    nt.cell(row=i, column=1, value=f"{i}. {t}").font = SM
nt.column_dimensions["A"].width = 120

out = ROOT / "output/taxonomy_v2_classification_report.xlsx"
wb.save(out)
print("wrote", out, "|", len(rows), "products |", st["CLASSIFIED"], "classified |", st["REVIEW_REQUIRED"], "review")
