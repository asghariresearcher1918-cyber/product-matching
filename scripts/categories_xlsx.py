"""Excel report of the full categorisation (output/all_products_categorised.xlsx).
Sheets: Read me | Summary (formulas over 'All products') | All products | one sheet per review need.
Usage: python -I scripts/categories_xlsx.py"""
import collections
import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
F = "Arial"
HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
CONF_FILL = {"high": "C6EFCE", "medium": "FFF2CC", "low": "F8CBAD"}


def header(ws, cols, widths):
    ws.append(cols)
    for j, w in enumerate(widths, 1):
        c = ws.cell(row=1, column=j)
        c.font, c.fill, c.alignment = HF, HFILL, Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A2"


def main():
    rows = list(csv.DictReader(open(ROOT / "output" / "all_products_categorised.csv", encoding="utf-8")))
    wb = Workbook()
    ws = wb.active
    ws.title = "Read me"
    conf = collections.Counter(r["confidence"] for r in rows)
    read = sum(r["page_status"] == "read" for r in rows)
    manual = sum("manual:" in r["evidence"] for r in rows)
    lines = [
        ("All products - category of every listing (11,755 rows, 24 suppliers)", True),
        (f"Product pages read: {read}. Rows without a page ({len(rows) - read}): blocked site (Refine Pharma), removed product (404 / redirect to home page) - categorised from the listing title only and marked so.", False),
        ("How each row was categorised: several independent signals on the product page vote for a category -", False),
        ("  the supplier's own category (breadcrumb, shop category, product type / vendor, URL path), the product name on the page, the brand,", False),
        ("  the 'Form' and legal-category fields (POM / P / GSL / MD), the description, and last the listing title.", False),
        (f"Confidence: high {conf['high']} = two or more independent signals agree; medium {conf['medium']} = one strong signal; low {conf['low']} = weak or conflicting signals.", False),
        (f"Rows reviewed by hand (one by one, from the page): {manual} - their evidence column starts with 'manual:'.", False),
        ("", False),
        ("Sheets: Summary (counts per category and supplier, live formulas) | All products (filterable; title is a link to the page) | Low confidence", True),
    ]
    for t, b in lines:
        ws.append([t])
        ws.cell(row=ws.max_row, column=1).font = Font(name=F, bold=b, size=12 if b else 10)
    ws.column_dimensions["A"].width = 150

    # All products
    ap = wb.create_sheet("All products")
    cols = ["ID", "Supplier", "Listing title (link)", "Name on page", "Category", "Confidence", "Alternatives", "Supplier's own category", "Page", "Evidence"]
    header(ap, cols, [9, 20, 46, 40, 34, 11, 26, 40, 22, 60])
    for r in sorted(rows, key=lambda r: (r["category"], r["supplier"], r["title"].lower())):
        ap.append([r["id"], r["supplier"], r["title"], r["page_title"], r["category"], r["confidence"], r["alternatives"],
                   r["supplier_category"], r["page_status"], r["evidence"]])
        n = ap.max_row
        for j in range(1, len(cols) + 1):
            ap.cell(row=n, column=j).font = Font(name=F, size=9)
        c = ap.cell(row=n, column=3)
        c.hyperlink = r["url"]
        c.font = Font(name=F, size=9, color="0563C1", underline="single")
        ap.cell(row=n, column=6).fill = PatternFill("solid", fgColor=CONF_FILL.get(r["confidence"], "FFFFFF"))
    ap.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{ap.max_row}"
    last = ap.max_row

    # Summary with COUNTIFS formulas over All products
    sm = wb.create_sheet("Summary", 1)
    cats = [c for c, _ in collections.Counter(r["category"] for r in rows).most_common()]
    sups = [s for s, _ in collections.Counter(r["supplier"] for r in rows).most_common()]
    header(sm, ["Category", "Listings", "high", "medium", "low"] + sups, [40, 10, 8, 8, 8] + [11] * len(sups))
    rng = lambda col: f"'All products'!${col}$2:${col}${last}"
    for i, c in enumerate(cats, start=2):
        sm.cell(row=i, column=1, value=c)
        sm.cell(row=i, column=2, value=f"=COUNTIF({rng('E')},$A{i})")
        for k, lv in enumerate(("high", "medium", "low"), start=3):
            sm.cell(row=i, column=k, value=f'=COUNTIFS({rng("E")},$A{i},{rng("F")},"{lv}")')
        for k, s in enumerate(sups, start=6):
            sm.cell(row=i, column=k, value=f'=COUNTIFS({rng("E")},$A{i},{rng("B")},{get_column_letter(k)}$1)')
    t = len(cats) + 2
    sm.cell(row=t, column=1, value="Total").font = Font(name=F, bold=True)
    for k in range(2, 6 + len(sups)):
        L = get_column_letter(k)
        sm.cell(row=t, column=k, value=f"=SUM({L}2:{L}{t - 1})").font = Font(name=F, bold=True)
    for row in sm.iter_rows(min_row=2, max_row=t):
        for c in row:
            if c.font is None or not c.font.bold:
                c.font = Font(name=F, size=9)
    for k in range(6, 6 + len(sups)):
        sm.cell(row=1, column=k).alignment = Alignment(text_rotation=90, vertical="bottom")
    sm.row_dimensions[1].height = 130

    # Low confidence sheet
    lw = wb.create_sheet("Low confidence")
    header(lw, cols, [9, 20, 46, 40, 34, 11, 26, 40, 22, 60])
    for r in rows:
        if r["confidence"] != "low":
            continue
        lw.append([r["id"], r["supplier"], r["title"], r["page_title"], r["category"], r["confidence"], r["alternatives"],
                   r["supplier_category"], r["page_status"], r["evidence"]])
        n = lw.max_row
        for j in range(1, len(cols) + 1):
            lw.cell(row=n, column=j).font = Font(name=F, size=9)
        c = lw.cell(row=n, column=3)
        c.hyperlink = r["url"]
        c.font = Font(name=F, size=9, color="0563C1", underline="single")
    lw.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{max(2, lw.max_row)}"
    out = ROOT / "output" / "all_products_categorised.xlsx"
    wb.save(out)
    print(out)


if __name__ == "__main__":
    main()
