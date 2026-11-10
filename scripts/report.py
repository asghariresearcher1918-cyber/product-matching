"""Write output/run_report.md from the outputs. Usage: python -I scripts/report.py"""
import collections, csv, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
rows = list(csv.DictReader(open(OUT / "products_grouped.csv", encoding="utf-8")))
errs = list(csv.DictReader(open(ROOT / "scrape_errors.csv", encoding="utf-8")))
ref = list(csv.DictReader(open(OUT / "reference_catalog.csv", encoding="utf-8")))
notes = json.load(open(OUT / "_classify_notes.json"))
ok = [r for r in rows if r["family_id"]]
fams = collections.Counter(r["family_id"] for r in ok)
var = {r["variant_id"] for r in ok}; packs = {r["pack_id"] for r in ok}
conf = collections.Counter(r["confidence"] for r in rows)
L = ["# Run report - PILOT", "", f"Scope: {len(rows)} pilot rows (pilot_ids.txt), 10 suppliers.", "",
     "## Counts", "", f"rows {len(rows)} -> classified {len(ok)} -> families {len(fams)} -> variants {len(var)} -> packs {len(packs)}", "",
     "| confidence | rows |", "|---|---|"] + [f"| {k} | {v} |" for k, v in conf.most_common()] + ["",
     f"Errors: {len(errs)} (" + ", ".join(f"{k}: {v}" for k, v in collections.Counter(e['supplier'] for e in errs).items()) + ")", "",
     "| id | supplier | error |", "|---|---|---|"] + [f"| {e['id']} | {e['supplier']} | {e['error'][:110]} |" for e in errs] + ["",
     "Reference status: " + ", ".join(f"{k}: {v}" for k, v in collections.Counter(r['reference_status'] for r in ref).items()), "",
     "## Families -> variants -> packs", ""]
for fam in sorted(fams):
    rs = [r for r in ok if r["family_id"] == fam]
    L.append(f"### {fam} - {rs[0]['family_name']} ({len(rs)} rows, {len({r['supplier'] for r in rs})} suppliers)")
    for v in sorted({r["variant_id"] for r in rs}):
        vr = [r for r in rs if r["variant_id"] == v]
        L.append(f"- **{vr[0]['variant_label']}**")
        for pk in sorted({r["pack_id"] for r in vr}):
            pr = [r for r in vr if r["pack_id"] == pk]
            L.append(f"  - {pr[0]['pack_label']}: " + ", ".join(f"{r['id']} {r['supplier']} ({r['confidence']})" for r in pr))
    L.append("")
L += ["## Top conflicts", ""] + [f"- {r['id']} {r['supplier']} \"{r['title']}\": {r['review_reason']}" for r in rows if r["confidence"] == "uncertain" and r["family_id"]] + [""]
L += ["## Cross-supplier notes", ""] + [f"- {n}" for n in notes["cross_supplier_notes"]] + [""]
L += ["## Rules that needed changing / interpretation", "",
      "- Status words are read only from titles and the stock field; page boilerplate (\"New here?\", \"Directions: available on request\", category \"Vitamins & IV\") produced false status/route hits.",
      "- \"Vitamins & IV\" (Ask Pharmacy category label) is neutral, not a route.",
      "- A pack count/vial count visible only in the product image lowers confidence to 'likely' (not 'uncertain'): the image is part of the page.",
      "- Profhilo 'UK hologram' kept as a note, not a variant, until the owner decides (see open questions).",
      "- 'Lidocaine not stated' rows are grouped with the lidocaine variant provisionally and marked 'likely' (UK Juvederm Ultra/Teosyal packs seen are lidocaine versions).",
      ""]
(OUT / "run_report.md").write_text("\n".join(L), encoding="utf-8")
print("run_report.md written")
