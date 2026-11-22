"""Standalone 'decide a rule' workbook for the biostimulator items that could NOT be auto-resolved.
Groups the flagged products by issue type and, for each, gives the pharmacies, listing count, example titles and a
concrete question to answer so we can set a rule. Usage: python -I scripts/biostim_flag_report.py"""
import collections, csv
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"
F = "Arial"
HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
SM, WRAP = Font(name=F, size=9), Alignment(wrap_text=True, vertical="top")
LINK = Font(name=F, size=9, color="0563C1", underline="single")

prods = {p["uid"]: p for p in csv.DictReader(open(FINAL / "master_catalogue.csv", encoding="utf-8")) if p["category"] == "Biostimulator"}
bysup, titles, link = collections.defaultdict(set), collections.defaultdict(list), {}
for m in csv.DictReader(open(FINAL / "master_listing_index.csv", encoding="utf-8")):
    if m["category"] != "Biostimulator":
        continue
    bysup[m["uid"]].add(m["supplier"])
    if len(titles[m["uid"]]) < 3 and m.get("listing_title"):
        titles[m["uid"]].append(f"{m['supplier']}: {m['listing_title']}")
    link.setdefault(m["uid"], m.get("url", ""))

# (uid-match, issue, rule question)
def issue(p):
    g = p["equivalence_group"].lower(); man = p["manufacturer"].strip().lower()
    if "hybrid" in g:
        return ("HYBRID (CaHA + HA)", "This is both a filler and a biostimulator. Which ONE category should it live in on the site?")
    if "ask the supplier" in g or "unconfirmed" in g:
        return ("Active agent unknown", "The page states no molecule. Keep in Biostimulator flagged, move to Skin boosters, or ask the supplier for the agent?")
    if "not a biostimulator" in g or "ha booster" in g:
        return ("HA booster, not a stimulator", "Confirmed HA skin booster. Move to 'Skin booster / PN / mesotherapy', or keep here?")
    if man in ("", "not stated", "not named", "korea", "unknown"):
        return ("No manufacturer found", "No maker/importer could be verified. Accept the pharmacy-consensus name, or exclude until confirmed?")
    return ("", "")

rows = []
for uid, p in prods.items():
    label, q = issue(p)
    if label:
        rows.append((label, p, q))
order = {"HYBRID (CaHA + HA)": 0, "HA booster, not a stimulator": 1, "Active agent unknown": 2, "No manufacturer found": 3}
rows.sort(key=lambda r: (order.get(r[0], 9), r[1]["product"]))

wb = Workbook(); ws = wb.active; ws.title = "Decide a rule"
cols = ["Issue", "Product (as listed)", "Equivalence group", "Manufacturer (found?)", "Question to answer",
        "Pharmacies", "Listings", "Example listing titles", "Open a listing"]
widths = [24, 34, 26, 30, 50, 10, 8, 52, 16]
ws.append(cols)
for j, w in enumerate(widths, 1):
    c = ws.cell(row=1, column=j); c.font, c.fill, c.alignment = HF, HFILL, WRAP
    ws.column_dimensions[get_column_letter(j)].width = w
ws.freeze_panes = "A2"
for label, p, q in rows:
    ws.append([label, p["product"], p["equivalence_group"], p["manufacturer"] or "(none found)", q,
               len(bysup.get(p["uid"], [])), p["listings"], "\n".join(titles.get(p["uid"], [])), "open"])
    for c in ws[ws.max_row]:
        c.font, c.alignment = SM, WRAP
    u = link.get(p["uid"], "")
    if u.startswith("http"):
        c = ws.cell(row=ws.max_row, column=9); c.hyperlink = u; c.font = LINK
ws.auto_filter.ref = f"A1:I{ws.max_row}"

out = ROOT / "output/biostim_FLAGGED_for_rules.xlsx"
wb.save(out)
print("wrote", out, "-", len(rows), "items to decide")
