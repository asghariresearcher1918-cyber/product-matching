"""Compare the clinic needs map (data/clinic_needs.py) with our listings -> output/clinic_needs_coverage.xlsx
Usage: python -I scripts/needs_coverage.py"""
import collections, csv, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from clinic_needs import NEEDS
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

F = "Arial"; HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
FILL = {"Good": "C6EFCE", "Weak": "FFF2CC", "Missing": "F8CBAD"}
SKIP = {"Not a product"}
rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8")) if r["category"] not in SKIP]
texts = [(r["page_title"] + " | " + r["title"]).lower() for r in rows]

def status(n, s):
    if n == 0: return "Missing"
    return "Good" if s >= 3 and n >= 5 else "Weak"

out = []
for area, item, prio, access, mode, pat, catf in NEEDS:
    rx = re.compile(pat)
    m = [r for r, t in zip(rows, texts) if rx.search(t) and (not catf or any(c in r["category"] for c in catf.split("|")))]
    sups = collections.Counter(r["supplier"] for r in m)
    ex = list(dict.fromkeys((r["page_title"] or r["title"]) for r in m))[:5]
    out.append((area, item, prio, access, mode, len(m), len(sups), status(len(m), len(sups)), ", ".join(s for s, _ in sups.most_common(6)), " | ".join(ex), m))

def head(ws, cols, widths):
    ws.append(cols)
    for j, w in enumerate(widths, 1):
        c = ws.cell(row=1, column=j); c.font, c.fill = HF, HFILL; c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A2"

wb = Workbook(); rd = wb.active; rd.title = "Read me"
cnt = collections.Counter(o[7] for o in out)
for t in [
    "Clinic needs map - UK aesthetic & skin clinics (phase 1) vs our 11,755 listings",
    f"{len(out)} needs. Good {cnt['Good']} (3+ suppliers and 5+ listings) | Weak {cnt['Weak']} | Missing {cnt['Missing']}.",
    "Counts come from keyword matching on product names, so they are approximate: check the examples column.",
    "Priority: Required = law / professional guidance expects the clinic to have it (e.g. emergency kit, sharps, fridge with temperature log);",
    "  Core = used every day; Regular = often; Optional = only some clinics.",
    "Access (proposal): Public = anyone sees price | Professional = verified healthcare professional | POM = professional + prescription.",
    "Mode (proposal): Compare = same product from several suppliers | Browse = many brands, buyer chooses | Quote = request a quote.",
    "Your columns: 'Keep?' (Yes / No / Later) and 'Note'. Add any missing need as a new row at the bottom.",
    "Sheet 'Matches' lists every matched listing with its link.",
]:
    rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=10, bold=rd.max_row == 1)
rd.column_dimensions["A"].width = 140

ws = wb.create_sheet("Needs vs coverage")
head(ws, ["Area", "Need", "Priority", "Access", "Mode", "Listings", "Suppliers", "Coverage", "Top suppliers", "Examples", "Keep?", "Note"],
     [22, 40, 10, 12, 9, 9, 9, 10, 40, 70, 9, 30])
dv = DataValidation(type="list", formula1='"Yes,No,Later"', allow_blank=True); ws.add_data_validation(dv)
for o in out:
    ws.append(list(o[:10]) + ["", ""])
    n = ws.max_row; dv.add(f"K{n}")
    for c in ws[n]: c.font = Font(name=F, size=9); c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.cell(row=n, column=8).fill = PatternFill("solid", fgColor=FILL[o[7]])
ws.auto_filter.ref = f"A1:L{ws.max_row}"

sm = wb.create_sheet("By area", 1)
head(sm, ["Area", "Needs", "Good", "Weak", "Missing"], [28, 8, 8, 8, 8])
last = ws.max_row
areas = list(dict.fromkeys(o[0] for o in out))
for i, a in enumerate(areas, start=2):
    sm.cell(row=i, column=1, value=a)
    sm.cell(row=i, column=2, value=f"=COUNTIF('Needs vs coverage'!$A$2:$A${last},$A{i})")
    for k, lv in enumerate(("Good", "Weak", "Missing"), start=3):
        sm.cell(row=i, column=k, value=f"=COUNTIFS('Needs vs coverage'!$A$2:$A${last},$A{i},'Needs vs coverage'!$H$2:$H${last},\"{lv}\")")
t = len(areas) + 2
sm.cell(row=t, column=1, value="Total").font = Font(name=F, bold=True)
for k in range(2, 6):
    L = get_column_letter(k); sm.cell(row=t, column=k, value=f"=SUM({L}2:{L}{t-1})").font = Font(name=F, bold=True)

mt = wb.create_sheet("Matches")
head(mt, ["Need", "Supplier", "Product (link)", "Our category"], [40, 20, 60, 34])
for o in out:
    for r in o[10]:
        mt.append([o[1], r["supplier"], r["page_title"] or r["title"], r["category"]])
        for c in mt[mt.max_row]: c.font = Font(name=F, size=9)
        c = mt.cell(row=mt.max_row, column=3); c.hyperlink = r["url"]; c.font = Font(name=F, size=9, color="0563C1", underline="single")
mt.auto_filter.ref = f"A1:D{mt.max_row}"
p = ROOT / "output/clinic_needs_coverage.xlsx"; wb.save(p)
for o in out: print(f"{o[7]:8s}{o[5]:5d}{o[6]:4d}  {o[0][:14]:14s} {o[1][:48]:48s} {o[9][:110]}")
print(cnt)
