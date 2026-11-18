"""What our current list (11,755 listings) covers: categories -> sub-groups, and catalogue status.
Sub-group = the most specific item of the needs master list whose keywords match the listing.
Usage: python -I scripts/current_scope_xlsx.py  -> output/current_list_scope.xlsx"""
import collections, csv, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from clinic_needs_master import ITEMS
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

F = "Arial"; HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
rows = list(csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8")))
texts = [(r["page_title"] + " | " + r["title"]).lower() for r in rows]
l2c = {r["id"]: r for r in csv.DictReader(open(ROOT / "catalogue/draft/listing_to_code.csv", encoding="utf-8"))}
coded = {k: v["code"] for k, v in l2c.items()}
BRAND_CATS = {"Toxin", "Dermal filler", "Skin booster / polynucleotide / mesotherapy", "Biostimulator", "PDO threads", "Fat dissolving",
              "Weight-loss medicine", "Skincare, haircare & peels", "Supplements", "Beauty (nails, brows, lashes, PMU, makeup)"}
TWO = {"dr", "dr.", "the", "la", "le", "skin", "pca", "zo", "dr adams", "cosmetic", "image", "jan", "mesoestetic", "perfect", "medik8"}
def brand(r):
    b = (l2c.get(r["id"]) or {}).get("brand")
    if b: return b
    pt = r["page_title"] if r["page_title"] and not r["page_title"].lower().startswith(("partner with", "dr. adams pharmacy")) else r["title"]
    w = re.sub(r"[^\w&.' -]", " ", pt).split()
    if not w: return "?"
    b = " ".join(w[:2]) if w[0].lower() in TWO and len(w) > 1 else w[0]
    return b.upper() if len(b) <= 3 else b.title()
items = [(i[1], re.compile(i[10])) for i in ITEMS if not i[10].startswith("<cat:")]
hits = {name: {k for k, t in enumerate(texts) if rx.search(t)} for name, rx in items}
size = {n: len(h) for n, h in hits.items()}
sub = []
for k in range(len(rows)):
    m = [n for n, h in hits.items() if k in h]
    sub.append(min(m, key=lambda n: size[n]) if m else "")

PLAN = {  # proposal per category
    "Toxin": ("Phase 1 - finalise", "Compare", "Catalogue codes drafted"),
    "Dermal filler": ("Phase 1 - finalise", "Compare", "Catalogue codes drafted"),
    "Skin booster / polynucleotide / mesotherapy": ("Phase 1 - finalise", "Compare", "Catalogue codes drafted (boosters, polynucleotides); mesotherapy not yet"),
    "Biostimulator": ("Phase 1 - finalise", "Compare", "Catalogue codes drafted"),
    "Fat dissolving": ("Phase 1 - finalise", "Compare", "No codes yet"),
    "PDO threads": ("Phase 1 - finalise", "Compare", "No codes yet"),
    "Medicine - injectable / anaesthetic / emergency": ("Phase 1 - finalise", "Compare", "No codes yet"),
    "Weight-loss medicine": ("Phase 1 - finalise", "Compare", "No codes yet"),
    "Vitamin & IV therapy": ("Phase 1 - finalise", "Compare", "No codes yet"),
    "Medicine - topical / eye / other": ("Phase 1 - finalise", "Compare", "No codes yet"),
    "Medicine - oral": ("Phase 1 - your decision", "Compare", "No codes yet; mostly general pharmacy lines"),
    "Vaccine": ("Phase 1 - your decision", "Compare", "No codes yet; 3 suppliers only"),
    "Needles, cannulas & syringes": ("Phase 1 - finalise", "Browse (compare same brand+size)", "No codes yet"),
    "Clinic consumables & PPE": ("Phase 1 - finalise", "Browse (compare same brand+size)", "No codes yet"),
    "Devices & equipment": ("Phase 1 - finalise", "Browse / Quote", "No codes yet"),
    "Skincare, haircare & peels": ("Phase 1 - finalise", "Compare (branded lines)", "No codes yet"),
    "Supplements": ("Phase 1 - your decision", "Compare (branded lines)", "No codes yet"),
    "Beauty (nails, brows, lashes, PMU, makeup)": ("Phase 1 - your decision", "Browse", "No codes yet; salon rather than clinic products"),
    "Training, services & marketing": ("Phase 2 - services", "Quote", "Moved to phase 2 with the other services"),
    "Not a product": ("Remove", "-", "Pages that are not products"),
    "Unclassified": ("Check by hand", "-", "2 rows"),
}
wb = Workbook(); ws = wb.active; ws.title = "Categories"
def head(w, cols, widths):
    w.append(cols)
    for j, x in enumerate(widths, 1):
        c = w.cell(row=1, column=j); c.font, c.fill = HF, HFILL; c.alignment = Alignment(wrap_text=True, vertical="top")
        w.column_dimensions[get_column_letter(j)].width = x
    w.freeze_panes = "B2"
def fmt(w):
    for c in w[w.max_row]: c.font = Font(name=F, size=9); c.alignment = Alignment(wrap_text=True, vertical="top")
head(ws, ["Category", "Listings", "Suppliers", "High conf.", "Medium conf.", "Listings with a catalogue code", "Proposal", "Display", "Catalogue status", "Your decision", "Note"],
     [40, 9, 9, 9, 9, 12, 22, 22, 40, 14, 30])
dv = DataValidation(type="list", formula1='"Keep,Remove,Later"', allow_blank=True); ws.add_data_validation(dv)
by = collections.defaultdict(list)
for k, r in enumerate(rows): by[r["category"]].append(k)
for cat, ks in sorted(by.items(), key=lambda kv: -len(kv[1])):
    rs = [rows[k] for k in ks]; conf = collections.Counter(r["confidence"] for r in rs)
    p = PLAN.get(cat, ("", "", ""))
    ws.append([cat, len(rs), len({r["supplier"] for r in rs}), conf["high"], conf["medium"], sum(1 for r in rs if coded.get(r["id"])), *p, "", ""])
    fmt(ws); dv.add(f"J{ws.max_row}")
ws.append(["Total", f"=SUM(B2:B{ws.max_row})"]); fmt(ws)

sg = wb.create_sheet("Inside each category")
head(sg, ["Category", "Sub-group (product type; brand for product categories - approx.)", "Listings", "Suppliers", "Examples"], [40, 50, 9, 9, 90])
for cat, ks in sorted(by.items(), key=lambda kv: -len(kv[1])):
    g = collections.defaultdict(list)
    for k in ks:
        name = ("Brand: " + brand(rows[k])) if cat in BRAND_CATS else (sub[k] or f"(other {cat.lower()})")
        g[name].append(rows[k])
    for name, rs in sorted(g.items(), key=lambda kv: -len(kv[1])):
        ex = " | ".join(list(dict.fromkeys(r["page_title"] or r["title"] for r in rs))[:5])
        sg.append([cat, name, len(rs), len({r["supplier"] for r in rs}), ex]); fmt(sg)
sg.auto_filter.ref = f"A1:E{sg.max_row}"
# scope (scripts/apply_scope.py)
sc = wb.create_sheet("Scope by category", 1)
scopes = ["Phase 1", "Phase 2 - later", "Phase 2 - services", "Later phase - nail & facial salons", "Removed - general pharmacy", "Removed - not a product", "Check by hand"]
head(sc, ["Category", "All"] + scopes, [40, 8] + [13] * len(scopes))
for cat, ks in sorted(by.items(), key=lambda kv: -len(kv[1])):
    c = collections.Counter(rows[k].get("scope", "") for k in ks)
    sc.append([cat, len(ks)] + [c.get(x, 0) or "" for x in scopes]); fmt(sc)
n = sc.max_row
sc.append(["Total"] + [f"=SUM({get_column_letter(j)}2:{get_column_letter(j)}{n})" for j in range(2, 3 + len(scopes))]); fmt(sc)
for c in sc[sc.max_row]: c.font = Font(name=F, size=9, bold=True)
md = wb.create_sheet("Medicines - review")
head(md, ["Original category", "Scope", "Group", "Now in category", "Supplier", "Product (link)"], [34, 24, 44, 34, 18, 60])
FILL = {"Phase 1": "C6EFCE", "Phase 2 - later": "FFF2CC", "Removed - general pharmacy": "F8CBAD"}
for r in sorted((r for r in rows if r.get("category_auto", "").startswith("Medicine")), key=lambda r: (r["category_auto"], r["scope"], r["scope_group"], (r["page_title"] or r["title"]).lower())):
    md.append([r["category_auto"], r["scope"], r["scope_group"], r["category"], r["supplier"], r["page_title"] or r["title"]]); fmt(md)
    md.cell(row=md.max_row, column=2).fill = PatternFill("solid", fgColor=FILL.get(r["scope"], "FFFFFF"))
    c = md.cell(row=md.max_row, column=6); c.hyperlink = r["url"]; c.font = Font(name=F, size=9, color="0563C1", underline="single")
md.auto_filter.ref = f"A1:F{md.max_row}"
p = ROOT / "output/current_list_scope.xlsx"; wb.save(p); print(p)
for cat, ks in sorted(by.items(), key=lambda kv: -len(kv[1])):
    g = collections.Counter(("B:" + brand(rows[k])) if cat in BRAND_CATS else (sub[k] or "(other)") for k in ks)
    print(f"## {cat} ({len(ks)})  " + "; ".join(f"{n[:38]} {c}" for n, c in g.most_common(9)))
