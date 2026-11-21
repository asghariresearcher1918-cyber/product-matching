"""Per-category review workbook: Products of one category + the supplier listings that map to each product
(pharmacy name + clickable link). Usage: python -I scripts/category_export.py "Fat dissolving" [out.xlsx]"""
import collections, csv, re, sys
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"
F = "Arial"
HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
LINK = Font(name=F, size=9, color="0563C1", underline="single")
SM = Font(name=F, size=9)
WRAP = Alignment(wrap_text=True, vertical="top")


def head(ws, cols, widths):
    ws.append(cols)
    for j, w in enumerate(widths, 1):
        c = ws.cell(row=1, column=j); c.font, c.fill, c.alignment = HF, HFILL, WRAP
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A2"


def fmt(ws, link_col=None, url=None):
    for c in ws[ws.max_row]:
        c.font, c.alignment = SM, WRAP
    if link_col and url and str(url).startswith("http"):
        c = ws.cell(row=ws.max_row, column=link_col); c.hyperlink = url; c.font = LINK


def main():
    category = sys.argv[1]
    prods = {p["uid"]: p for p in csv.DictReader(open(FINAL / "master_catalogue.csv", encoding="utf-8")) if p["category"] == category}
    listings = [m for m in csv.DictReader(open(FINAL / "master_listing_index.csv", encoding="utf-8")) if m["category"] == category]
    for m in listings:
        p = prods.get(m["uid"], {})
        m["product"] = p.get("product", "(unmatched)")
        m["verified"] = "reference" if "reference" in p.get("verified", "") else ""

    wb = Workbook()
    # Products tab
    ps = wb.active; ps.title = "Products"
    head(ps, ["Product (as listed on site)", "Equivalence group", "Brand", "Pack size", "Verified",
              "Pharmacies", "Listings"], [44, 26, 18, 20, 11, 11, 9])
    bysup = collections.defaultdict(set); bylist = collections.Counter()
    for m in listings:
        bysup[m["uid"]].add(m["supplier"]); bylist[m["uid"]] += 1
    for uid, p in sorted(prods.items(), key=lambda kv: (kv[1]["equivalence_group"], kv[1]["brand"], kv[1]["product"])):
        ps.append([p["product"], p["equivalence_group"], p["brand"], p["key_spec"],
                   "reference" if "reference" in p.get("verified", "") else "", len(bysup.get(uid, [])), bylist.get(uid, 0)])
        fmt(ps)
        if "reference" in p.get("verified", ""):
            ps.cell(row=ps.max_row, column=5).fill = PatternFill("solid", fgColor="C6EFCE")
    ps.auto_filter.ref = f"A1:G{ps.max_row}"

    # Listings-per-product tab (grouped by product name; pharmacy + clickable link)
    ls = wb.create_sheet("Listings per product")
    head(ls, ["Product (as listed)", "Pharmacy", "Supplier listing (click to open)", "Match confidence"], [40, 20, 60, 14])
    for m in sorted(listings, key=lambda m: (m["product"], m["supplier"])):
        ls.append([m["product"], m["supplier"], m["listing_title"], m["confidence"]])
        fmt(ls, 3, m["url"])
    ls.auto_filter.ref = f"A1:D{ls.max_row}"

    name = re.sub(r"[^a-z0-9]+", "_", category.lower()).strip("_")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / f"output/category_{name}.xlsx"
    wb.save(out)
    print(f"saved {out} | {len(prods)} products | {len(listings)} listings")


if __name__ == "__main__":
    main()
