"""Master clinic-needs list (data/clinic_needs_master.py) -> output/clinic_needs_master.xlsx
For every item: requirement level + official source, and coverage in our 11,755 listings and in wholesaler category menus.
Usage: python -I scripts/needs_master_xlsx.py"""
import collections, csv, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from clinic_needs_master import ITEMS, SOURCES
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

F = "Arial"; HF, HFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F4F6F")
COV = {"Good": "C6EFCE", "Weak": "FFF2CC", "Missing": "F8CBAD", "Service / fit-out": "DDEBF7"}
LEV = {"Required": "F4B084", "Recommended": "FFE699", "If offered": "E2EFDA", "Standard practice": "EDEDED", "Optional": "FFFFFF"}
WS = {"Williams Medical": "wms", "Medisave": "medisave", "Henry Schein": "hs", "Physique": "physique", "Ellisons": "ellisons", "Salons Direct": "salonsdirect"}
wcats = {k: [l.strip().lower() for l in open(ROOT / f"data/wholesaler_categories/{v}.txt", encoding="utf-8") if l.strip()] for k, v in WS.items()}
rows = [r for r in csv.DictReader(open(ROOT / "output/all_products_categorised.csv", encoding="utf-8")) if r["category"] != "Not a product"]
texts = [(r["page_title"] + " | " + r["title"]).lower() for r in rows]

out = []
for sec, item, spec, clinic, level, src, kind, freq, access, mode, pat in ITEMS:
    m = re.fullmatch(r"<cat:(.+)>", pat)
    if m:
        hits = [r for r in rows if m.group(1) in r["category"]]; wpat = None
    else:
        rx = re.compile(pat); hits = [r for r, t in zip(rows, texts) if rx.search(t)]; wpat = rx
    sups = collections.Counter(r["supplier"] for r in hits)
    if kind in ("Service", "Fixture"): cov = "Service / fit-out"
    elif not hits: cov = "Missing"
    else: cov = "Good" if len(sups) >= 3 and len(hits) >= 5 else "Weak"
    wh = [k for k, cats in wcats.items() if wpat and any(wpat.search(c) for c in cats)]
    ex = " | ".join(list(dict.fromkeys((r["page_title"] or r["title"]) for r in hits))[:4])
    out.append(dict(sec=sec, item=item, spec=spec, clinic=clinic, level=level, src=src, kind=kind, freq=freq, access=access, mode=mode,
                    n=len(hits), s=len(sups), cov=cov, wh=", ".join(wh), ex=ex, hits=hits))

def head(ws, cols, widths):
    ws.append(cols)
    for j, w in enumerate(widths, 1):
        c = ws.cell(row=1, column=j); c.font, c.fill = HF, HFILL; c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "C2"

def fmt(ws):
    for c in ws[ws.max_row]: c.font = Font(name=F, size=9); c.alignment = Alignment(wrap_text=True, vertical="top")

wb = Workbook(); rd = wb.active; rd.title = "Read me"
cnt = collections.Counter(o["cov"] for o in out); lv = collections.Counter(o["level"] for o in out)
txt = [
 ("Clinic needs master list - UK aesthetic & skin clinics (phase 1)", True),
 (f"{len(out)} items in {len(dict.fromkeys(o['sec'] for o in out))} sections, built from official guidance (sheet 'Sources') and six wholesaler catalogues.", False),
 (f"Requirement level: Required {lv['Required']} | Recommended {lv['Recommended']} | If offered {lv['If offered']} (only when the clinic offers that treatment) | Standard practice {lv['Standard practice']} | Optional {lv['Optional']}.", False),
 ("  Required / Recommended = named in official guidance (CQC, Resuscitation Council UK, JCCP premises standards, ACE Group, HTM 07-01 waste, Sharps Regulations 2013, MHRA laser guidance, HSE).", False),
 ("  If offered = the treatment is on the DHSC licensing lists (green / amber / red) - the clinic needs it only if it offers that treatment.", False),
 ("  Standard practice = not named by guidance, but stocked by virtually every clinic (seen across wholesaler catalogues).", False),
 (f"Our coverage (11,755 listings, 24 suppliers): Good {cnt['Good']} (3+ suppliers, 5+ listings) | Weak {cnt['Weak']} | Missing {cnt['Missing']} | Service or fit-out (not a product) {cnt['Service / fit-out']}.", False),
 ("  Coverage is found by keyword matching on product names - approximate. Check the Examples column and the 'Matches' sheet.", False),
 ("'Wholesaler categories' = which of Williams Medical, Medisave, Henry Schein, Physique, Ellisons, Salons Direct has a matching category in its menu (where to recruit suppliers).", False),
 ("Access (proposal): Public = anyone sees price | Professional = verified healthcare professional | POM = verified professional + prescription.", False),
 ("Mode (proposal): Compare = same product from several suppliers | Browse = many brands, buyer chooses | Quote = request a quote.", False),
 ("Legal note (JCCP): only prescribers entitled to wholesale stock (doctors, dentists) may hold stock of prescription-only medicines such as emergency kits; nurse/pharmacist independent prescribers cannot.", False),
 ("Your columns in 'Master list': Keep? (Yes / No / Later) and Note.", True),
]
for t, b in txt:
    rd.append([t]); rd.cell(row=rd.max_row, column=1).font = Font(name=F, size=12 if b else 10, bold=b)
rd.column_dimensions["A"].width = 160

ml = wb.create_sheet("Master list")
cols = ["Section", "Item", "Specs / note", "Clinic", "Requirement", "Official source", "Kind", "Reorder", "Access", "Mode",
        "Our listings", "Our suppliers", "Our coverage", "Wholesaler categories", "Examples in our list", "Keep?", "Note"]
head(ml, cols, [24, 46, 34, 9, 13, 20, 13, 11, 11, 9, 9, 9, 12, 30, 60, 8, 26])
dv = DataValidation(type="list", formula1='"Yes,No,Later"', allow_blank=True); ml.add_data_validation(dv)
for o in out:
    ml.append([o["sec"], o["item"], o["spec"], o["clinic"], o["level"], o["src"], o["kind"], o["freq"], o["access"], o["mode"],
               o["n"], o["s"], o["cov"], o["wh"], o["ex"], "", ""])
    fmt(ml); n = ml.max_row; dv.add(f"P{n}")
    ml.cell(row=n, column=13).fill = PatternFill("solid", fgColor=COV[o["cov"]])
    ml.cell(row=n, column=5).fill = PatternFill("solid", fgColor=LEV[o["level"]])
ml.auto_filter.ref = f"A1:Q{ml.max_row}"; last = ml.max_row

sm = wb.create_sheet("By section", 1)
lvls = ["Required", "Recommended", "If offered", "Standard practice", "Optional"]; covs = ["Good", "Weak", "Missing", "Service / fit-out"]
head(sm, ["Section", "Items"] + lvls + covs, [36, 8] + [11] * 9)
rng = lambda c: f"'Master list'!${c}$2:${c}${last}"
secs = list(dict.fromkeys(o["sec"] for o in out))
for i, s in enumerate(secs, start=2):
    sm.cell(row=i, column=1, value=s); sm.cell(row=i, column=2, value=f"=COUNTIF({rng('A')},$A{i})")
    for k, v in enumerate(lvls, start=3): sm.cell(row=i, column=k, value=f'=COUNTIFS({rng("A")},$A{i},{rng("E")},"{v}")')
    for k, v in enumerate(covs, start=8): sm.cell(row=i, column=k, value=f'=COUNTIFS({rng("A")},$A{i},{rng("M")},"{v}")')
    fmt(sm)
t = len(secs) + 2
sm.cell(row=t, column=1, value="Total")
for k in range(2, 12):
    L = get_column_letter(k); sm.cell(row=t, column=k, value=f"=SUM({L}2:{L}{t-1})")
for c in sm[t]: c.font = Font(name=F, bold=True)

gp = wb.create_sheet("Gaps to fill", 2)
head(gp, ["Section", "Item", "Requirement", "Official source", "Our coverage", "Our suppliers", "Wholesaler categories", "Mode"], [24, 46, 13, 20, 12, 9, 34, 9])
order = {"Required": 0, "Recommended": 1, "If offered": 2, "Standard practice": 3, "Optional": 4}
for o in sorted([o for o in out if o["cov"] in ("Missing", "Weak")], key=lambda o: (order[o["level"]], o["cov"] != "Missing", o["sec"])):
    gp.append([o["sec"], o["item"], o["level"], o["src"], o["cov"], o["s"], o["wh"], o["mode"]]); fmt(gp)
    gp.cell(row=gp.max_row, column=5).fill = PatternFill("solid", fgColor=COV[o["cov"]])
    gp.cell(row=gp.max_row, column=3).fill = PatternFill("solid", fgColor=LEV[o["level"]])
gp.auto_filter.ref = f"A1:H{gp.max_row}"

so = wb.create_sheet("Sources")
head(so, ["Key", "Source", "Link"], [10, 110, 70])
for k, (name, url) in SOURCES.items():
    so.append([k, name, url]); fmt(so)
    if url.startswith("http") and " " not in url:
        c = so.cell(row=so.max_row, column=3); c.hyperlink = url; c.font = Font(name=F, size=9, color="0563C1", underline="single")

mt = wb.create_sheet("Matches")
head(mt, ["Item", "Supplier", "Product (link)", "Our category"], [46, 20, 60, 34])
for o in out:
    if len(o["hits"]) > 300: continue  # whole categories (fillers, skincare...) - see all_products_categorised.xlsx
    for r in o["hits"]:
        mt.append([o["item"], r["supplier"], r["page_title"] or r["title"], r["category"]]); fmt(mt)
        c = mt.cell(row=mt.max_row, column=3); c.hyperlink = r["url"]; c.font = Font(name=F, size=9, color="0563C1", underline="single")
mt.auto_filter.ref = f"A1:D{mt.max_row}"
p = ROOT / "output/clinic_needs_master.xlsx"; wb.save(p); print(p)
print(len(out), cnt, lv)
for o in out:
    if o["cov"] in ("Missing", "Weak"): print(f"{o['cov']:8s}{o['s']:3d} {o['level'][:11]:11s} {o['item'][:70]:70s} | {o['wh']}")
