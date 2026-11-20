"""Full review workbook: every listing (with a clickable link to the supplier product page) joined to its assigned
catalogue product, plus breakdowns by pharmacy, by category, and the product master. For the owner to review matching.
Output: output/all_products_full.xlsx   Usage: python -I scripts/full_export.py"""
import collections, csv
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"
F = "Arial"
HF = Font(name=F, bold=True, color="FFFFFF")
HFILL = PatternFill("solid", fgColor="2F4F6F")
LINK = Font(name=F, size=9, color="0563C1", underline="single")
SM = Font(name=F, size=9)
WRAP = Alignment(wrap_text=True, vertical="top")


def header(ws, cols, widths):
    ws.append(cols)
    for j, w in enumerate(widths, 1):
        c = ws.cell(row=1, column=j); c.font, c.fill, c.alignment = HF, HFILL, WRAP
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A2"


def row_style(ws, link_col=None, url=None):
    for c in ws[ws.max_row]:
        c.font, c.alignment = SM, WRAP
    if link_col and url and str(url).startswith("http"):
        c = ws.cell(row=ws.max_row, column=link_col); c.hyperlink = url; c.font = LINK


def main():
    prods = {p["uid"]: p for p in csv.DictReader(open(FINAL / "master_catalogue.csv", encoding="utf-8"))}
    listings = list(csv.DictReader(open(FINAL / "master_listing_index.csv", encoding="utf-8")))
    for m in listings:
        p = prods.get(m["uid"], {})
        m["product"] = p.get("product", "")
        m["brand"] = p.get("brand", "")
        m["group"] = p.get("equivalence_group", m["category"])
        m["verified"] = "reference" if "reference" in p.get("verified", "") else ""

    wb = Workbook()

    # ---- Read me ----
    rd = wb.active; rd.title = "Read me"
    def line(t, sz=10, b=False):
        rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=sz, bold=b)
    line("Full product & listing review workbook", 13, True)
    line(f"{len(prods)} catalogue products built from {len(listings)} supplier listings across "
         f"{len(set(m['supplier'] for m in listings))} pharmacies and {len(set(m['category'] for m in listings))} categories.", 10)
    line("Sheets:", 11, True)
    line("• Listings — every supplier listing, with a CLICKABLE link to the product page, and the catalogue product it was matched to. Sorted by category then product so the listings of one product sit together — easy to spot a wrong match.", 10)
    line("• Products — one row per catalogue product (code), with supplier and listing counts.", 10)
    line("• By pharmacy — each pharmacy: how many listings / products / categories.", 10)
    line("• By category — each category: products, listings, how many are multi-supplier (comparable).", 10)
    line("A 'reference' tag (green) means the product was matched to an authoritative brand reference (high accuracy). Blank = still matched from listing text.", 10)
    line("Use the filter arrows on row 1 of any sheet to slice by pharmacy, category, product or verified.", 10, True)
    rd.column_dimensions["A"].width = 160

    # ---- Listings ----
    ls = wb.create_sheet("Listings")
    header(ls, ["Category", "Equivalence group", "Brand", "Matched product", "Code (uid)", "Pharmacy",
                "Supplier listing (click to open page)", "Verified", "Match confidence"],
           [22, 24, 18, 34, 22, 18, 52, 10, 12])
    FILL = {"high": "C6EFCE", "rule": "DDEBF7", "partial": "FFF2CC", "review": "F8CBAD", "re-file": "D9D9D9", "kit": "FCE4D6"}
    for m in sorted(listings, key=lambda m: (m["category"], m["group"], m["product"], m["supplier"])):
        ls.append([m["category"], m["group"], m["brand"], m["product"], m["uid"], m["supplier"],
                   m["listing_title"], m["verified"], m["confidence"]])
        row_style(ls, 7, m["url"])
        cf = (m["confidence"] or "").split()[0] if m["confidence"] else ""
        if cf in FILL:
            ls.cell(row=ls.max_row, column=9).fill = PatternFill("solid", fgColor=FILL[cf])
        if m["verified"] == "reference":
            ls.cell(row=ls.max_row, column=8).fill = PatternFill("solid", fgColor="C6EFCE")
    ls.auto_filter.ref = f"A1:I{ls.max_row}"

    # ---- Products ----
    ps = wb.create_sheet("Products")
    header(ps, ["Category", "Equivalence group", "Brand", "Product", "Spec", "Pack", "Market",
                "Manufacturer", "Verified", "Suppliers", "Listings", "Official source"],
           [22, 24, 18, 36, 16, 6, 8, 18, 12, 9, 8, 16])
    for p in sorted(prods.values(), key=lambda p: (p["category"], p["equivalence_group"], p["brand"], p["product"])):
        ps.append([p["category"], p["equivalence_group"], p["brand"], p["product"], p["key_spec"], p["pack"],
                   p["market"], p["manufacturer"], "reference" if "reference" in p.get("verified", "") else "",
                   p["suppliers"], p["listings"], p["source"]])
        row_style(ps, 12, p["source"])
        if "reference" in p.get("verified", ""):
            ps.cell(row=ps.max_row, column=9).fill = PatternFill("solid", fgColor="C6EFCE")
    ps.auto_filter.ref = f"A1:L{ps.max_row}"

    # ---- By pharmacy ----
    phar = collections.defaultdict(lambda: [0, set(), set()])
    for m in listings:
        a = phar[m["supplier"]]; a[0] += 1; a[1].add(m["uid"]); a[2].add(m["category"])
    bp = wb.create_sheet("By pharmacy")
    header(bp, ["Pharmacy", "Listings", "Distinct products", "Categories covered"], [30, 10, 16, 16])
    for s, a in sorted(phar.items(), key=lambda x: -x[1][0]):
        bp.append([s, a[0], len(a[1]), len(a[2])]); row_style(bp)

    # ---- By category ----
    cat = collections.defaultdict(lambda: [0, 0, 0])
    for p in prods.values():
        a = cat[p["category"]]; a[0] += 1; a[1] += int(p["listings"]); a[2] += (1 if int(p["suppliers"]) > 1 else 0)
    bc = wb.create_sheet("By category")
    header(bc, ["Category", "Products", "Listings", "Multi-supplier (comparable)"], [34, 10, 10, 22])
    for c, a in sorted(cat.items(), key=lambda x: -x[1][0]):
        bc.append([c, a[0], a[1], a[2]]); row_style(bc)
    bc.append(["TOTAL", len(prods), sum(int(p["listings"]) for p in prods.values()),
               sum(1 for p in prods.values() if int(p["suppliers"]) > 1)])
    for c in bc[bc.max_row]: c.font = Font(name=F, size=9, bold=True)

    out = ROOT / "output/all_products_full.xlsx"
    wb.save(out)
    print("saved", out, "|", len(listings), "listings |", len(prods), "products |", len(phar), "pharmacies")


if __name__ == "__main__":
    main()
