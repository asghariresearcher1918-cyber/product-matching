"""Catalogue-wide defect scan: find likely data errors in bulk so the owner reviews ~tens of flagged items instead of
checking thousands. Classes checked (name/field-based, fast & reliable):
  A. Pack MISSING but the name clearly states a count (pack of N / box of N / N pcs / x N / roll of N / single item).
  B. Category/type mismatch — a strong product-type word in the name contradicts the assigned category.
  C. Size looks like an SKU / code, not a real measurement (e.g. bare 'NNNNm', a lone long number).
  D. Display name still looks scraper-damaged (entirely lower-case, or a fused 'waist NNNN' range).
Output: output/defect_scan.xlsx (one row per flag, with a clickable product link). Usage: python -I scripts/defect_scan.py"""
import csv, re, sys
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"
sys.path.insert(0, str(ROOT / "scripts"))
from pack_size import resolve_pack          # same pack the site/Excel actually display (name-first, then catalogue)


def top_of(cid):
    return (cid or "").split(".")[0]


def main():
    master = {r["uid"]: r for r in csv.DictReader(open(FINAL / "master_catalogue.csv", encoding="utf-8"))}
    tax = {r["uid"]: r for r in csv.DictReader(open(FINAL / "taxonomy_v2.csv", encoding="utf-8"))}
    # representative listing (first) + url per uid, from the crosswalk
    url, lid = {}, {}
    for r in csv.DictReader(open(FINAL / "crosswalk.csv", encoding="utf-8")):
        u = r.get("product_uid")
        if u and u not in url:
            url[u] = r.get("url", ""); lid[u] = r.get("listing_id", "")

    # count patterns in a name. 'x N' only counts when NOT followed by a unit (so '1 x 6 ml' = a 6ml size, and
    # '1.25cm x 9.1m' = a length, are NOT read as a pack).
    _U = r"(?!\s*(?:ml|mg|g|kg|mcg|cm|mm|m|l|litre|oz|iu|units?|\"|in|x|\.))"
    COUNT = re.compile(r"\bpack of\s*\d+|\bbox of\s*\d+|\b(?:roll|set|bag|case|carton|tub)\s+of\s*\d+|"
                       r"\b\d+\s*(?:pcs|pieces?|pairs?|sheets?|wipes?|swabs?|rolls?|sachets?|tablets?|tabs?|amps?|ampoules?|caps?|capsules?|['’]s)\b|"
                       r"(?<![\d.])x\s*\d+\b" + _U + r"|\bpack of 1\b|\(?\s*single\s+(?:mask|respirator|pack|unit|piece|vial|tube|bottle)s?\b", re.I)
    # type word -> label; flagged only when the product sits in a CLEARLY UNRELATED domain (not a shuffle between the
    # clinical categories C10/C11/C12/C13, which are too close to call from the name alone).
    UNRELATED = {"C01", "C02", "C03", "C04", "C06", "C07", "C08", "C09", "C14", "WLM"}
    TYPEMAP = [
        (r"\b(kn90|kn95|ffp[123]|n95|respirator|particulate mask)\b", "respirator/PPE"),
        (r"\b(scalpel|surgical blade|stitch cutter|\bsuture)\b", "surgical blade/suture"),
        (r"\b(couch roll|nitrile gloves|vinyl gloves|examination gloves|coverall|face shield)\b", "consumable/PPE"),
        (r"\b(pdo|pcl|pllampcl)\b.*\bthreads?\b|\bmono threads?\b|\bcog threads?\b|\bbarbed? threads?\b", "PDO thread"),
        (r"\bhypodermic needle\b", "needle"),
    ]
    SKU_SIZE = re.compile(r"^\d{3,}(?:m|cm|g)?$|^[A-Z]{2,}\d{2,}", re.I)

    flags = []
    for uid, m in master.items():
        name = m.get("product", ""); nl = name.lower()
        pack, _flag = resolve_pack(name, (m.get("pack") or "").strip())   # what the owner actually sees
        pack = (pack or "").strip()
        spec = (m.get("key_spec") or "").strip()
        cat = tax.get(uid, {}); cid = top_of(cat.get("primary_category_id", "")); catname = cat.get("primary_category", "")
        row = {"defect": "", "uid": uid, "product": name, "category": catname,
               "pack": pack, "size": spec, "evidence": "", "supplier": m.get("brand", ""),
               "listing_id": lid.get(uid, ""), "url": url.get(uid, "")}
        # A. pack missing but a count is stated in the name
        mc = COUNT.search(name)
        if not pack and mc:
            flags.append({**row, "defect": "A: pack blank but count in name", "evidence": mc.group(0)})
        # B. type/category mismatch — only when the product is in a clearly-unrelated domain
        for rx, lbl in TYPEMAP:
            if re.search(rx, nl) and cid in UNRELATED:
                flags.append({**row, "defect": f"B: {lbl} in unrelated category", "evidence": f"name says {lbl}; sits in {cid} {catname}"})
                break
        # C. size looks like an SKU / code
        if spec and SKU_SIZE.match(spec) and not re.search(r"\d\s*(ml|mg|iu|g|cm|mm)\b", spec):
            flags.append({**row, "defect": "C: size looks like an SKU/code", "evidence": spec})
        # D. display name still damaged
        if name and name == nl and re.search(r"[a-z]", name):
            flags.append({**row, "defect": "D: name still all-lowercase", "evidence": name[:40]})
        elif re.search(r"waist\s*\d{4}\b", nl):
            flags.append({**row, "defect": "D: fused range in name (lost hyphen)", "evidence": re.search(r'waist\s*\d{4}', nl).group(0)})

    # write workbook (with clickable link per row — owner rule)
    wb = Workbook(); ws = wb.active; ws.title = "Defect scan"
    cols = ["Defect", "Product", "Category", "Pack", "Size", "Evidence", "Brand", "Listing id", "Link (click)"]
    ws.append(cols)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="8B2F2F"); c.alignment = Alignment(wrap_text=True)
    order = {"A": 0, "B": 1, "C": 2, "D": 3}
    for f in sorted(flags, key=lambda x: (order.get(x["defect"][0], 9), x["category"], x["product"])):
        ws.append([f["defect"], f["product"], f["category"], f["pack"], f["size"], f["evidence"], f["supplier"], f["listing_id"], ""])
        if f["url"].startswith("http"):
            c = ws.cell(row=ws.max_row, column=9); c.value = "Open product ↗"; c.hyperlink = f["url"]
            c.font = Font(color="0563C1", underline="single")
    for col, w in zip("ABCDEFGHI", [30, 46, 24, 8, 20, 26, 16, 12, 16]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    out = ROOT / "output/defect_scan.xlsx"
    wb.save(out)
    import collections
    by = collections.Counter(f["defect"] for f in flags)
    print(f"total flags: {len(flags)}  across {len({f['uid'] for f in flags})} products")
    for d, n in sorted(by.items()):
        print(f"  {n:4}  {d}")
    print("->", out)


if __name__ == "__main__":
    main()
