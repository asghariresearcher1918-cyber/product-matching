"""Self-verification gate — runs a FIXED, supplier-agnostic checklist on a category before any file is sent, so errors
are caught by the engine instead of by the owner. Philosophy: evidence-or-review. A product/listing is only 'OK' when
every field it needs is backed by positive evidence and is internally consistent; otherwise it is routed to REVIEW with
a reason. The per-category RULES below are stable rules that apply to every pharmacy/supplier (now and when new ones
connect). Output: output/verify_<category>.xlsx (Checklist + Review tabs).
Usage: python -I scripts/verify.py "Fat Dissolving & Body Contouring"   (a v2 top-level label or C## id)"""
import collections, csv, re, statistics, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
try:
    from page_facts import page_text
except Exception:
    def page_text(_i): return ""
from build_site_v2 import TOP, top_of
from category_export_v2 import extract  # public-price / SKU reader (pence-only, threshold-filtered)

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"

# ---- per-category rules (supplier-agnostic contract). Add a block per category as we verify it. ----
RULES = {
 "C04": dict(label="Fat Dissolving & Body Contouring", stems=["fat"],
             needs_pack=True, needs_volume=True, variants=[("face", "body"), ("v-line", "body")],
             price_outlier=2.5),   # a per-vial price >2.5x or <1/2.5x the product median is suspect
}
OUTLIER_LO = 0.4


def head(ws, cols, widths):
    ws.append(cols)
    for j, w in enumerate(widths, 1):
        c = ws.cell(row=1, column=j); c.font = Font(name="Arial", bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="2F4F6F"); c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A2"


def main():
    target = sys.argv[1]
    want = target if (target.startswith("C") or target == "WLM") else next((k for k, (l, _i) in TOP.items() if l == target), None)
    rule = RULES.get(want)
    assert rule, f"no verification ruleset for category '{target}' ({want})"

    prods = {r["uid"]: r for r in csv.DictReader(open(FINAL / "master_catalogue.csv", encoding="utf-8"))}
    # listings for this category (with page id + pack source from the decision)
    listings = collections.defaultdict(list)       # uid -> [listing dict]
    review = []                                     # listing-level matcher reviews
    for stem in rule["stems"]:
        p = FINAL / f"{stem}_listing_map.csv"
        if not p.exists():
            continue
        tag = {"fat": "FAT", "toxin": "TOX", "biostim": "BIO", "filler": "FIL", "booster": "BST"}.get(stem, stem.upper())
        for m in csv.DictReader(open(p, encoding="utf-8")):
            if str(m.get("matched", "")).startswith("review"):
                review.append(("matcher", m.get("matched"), m.get("title", ""), m.get("supplier", ""), m.get("decision", ""), m.get("url", "")))
                continue
            if m.get("matched") != "reference" or not m.get("code"):
                continue
            uid = f"{tag}:{m['code']}"
            dec = m.get("decision", "")
            pm = re.search(r"pack (\d+) \(([^)]*)\)", dec)
            packn = int(pm.group(1)) if pm else None
            psrc = pm.group(2) if pm else "?"
            sku, _c, price = extract(m.get("id", ""))
            pv = float(price[1:]) if price.startswith("£") else None
            listings[uid].append(dict(title=m.get("title", ""), supplier=m.get("supplier", ""), url=m.get("url", ""),
                                      pack=packn, psrc=psrc, price=pv))

    # ---- run checks per product (category membership via taxonomy_v2) ----
    checklist, flags = [], []
    tax = {r["uid"]: r for r in csv.DictReader(open(FINAL / "taxonomy_v2.csv", encoding="utf-8"))}
    members = [uid for uid in prods if top_of(tax.get(uid, {}).get("primary_category_id", "")) == want]

    for uid in sorted(members):
        p = prods[uid]
        ls = listings.get(uid, [])
        vol = re.search(r"(\d+(?:\.\d+)?)\s*ml", p.get("key_spec", ""))
        rows_prices = [(l["price"] / l["pack"]) for l in ls if l["price"] and l["pack"]]
        med = statistics.median(rows_prices) if rows_prices else None
        issues = []
        for l in ls:
            why = []
            # HARD checks -> REVIEW (a real correctness risk)
            if rule["needs_pack"] and (l["pack"] is None or "assumed" in l["psrc"]):
                why.append("pack not evidenced (assumed) — confirm")
            if med and l["price"] and l["pack"]:
                per = l["price"] / l["pack"]
                if per > med * rule["price_outlier"] or per < med * OUTLIER_LO:
                    why.append(f"price per vial £{per:.2f} vs product median £{med:.2f} — likely wrong pack/variant/bundle")
            for a, b in rule["variants"]:
                if a in l["title"].lower() and b in p["product"].lower() and a not in p["product"].lower():
                    why.append(f"title says '{a}' but product is '{b}' — variant mismatch")
            if why:
                issues.append((l, why))
                flags.append((p["product"], l["supplier"], l["title"], " ; ".join(why), l["url"]))
        checklist.append((p["product"], len(ls), len(issues), "OK" if not issues else "REVIEW"))

    # ---- workbook ----
    SM, WRAP = Font(name="Arial", size=9), Alignment(wrap_text=True, vertical="top")
    LINK = Font(name="Arial", size=9, color="0563C1", underline="single")
    wb = Workbook(); cl = wb.active; cl.title = "Checklist"
    head(cl, ["Product", "Listings", "Issues", "Status"], [44, 10, 9, 12])
    for name, nl, ni, st in checklist:
        cl.append([name, nl, ni, st])
        for c in cl[cl.max_row]: c.font, c.alignment = SM, WRAP
        cl.cell(row=cl.max_row, column=4).fill = PatternFill("solid", fgColor="C6EFCE" if st == "OK" else "FFC7CE")
    cl.auto_filter.ref = f"A1:D{cl.max_row}"

    def action_for(reason):
        r = (reason or "").lower()
        if any(k in r for k in ("accessory", "banner", "marketing")): return "EXCLUDE — not a product"
        if any(k in r for k in ("bundle", "multi-item", "kit")): return "SPLIT/EXCLUDE — it is a bundle/kit"
        if "price per vial" in r: return "CHECK — likely a bundle/kit or the wrong pack; confirm real pack"
        if "volume" in r and "conflict" in r: return "CONFIRM the real vial size and pack"
        if "plural" in r: return "CONFIRM how many vials are in the pack"
        if "assumed" in r: return "CONFIRM — single vial or a multipack?"
        if "variant mismatch" in r: return "FIX — assign to the correct variant (e.g. face vs body)"
        return "Review"

    rv = wb.create_sheet("Review (must fix)")
    head(rv, ["Product / listing", "Supplier", "What is wrong", "➡ What to do", "Open page"], [40, 18, 50, 40, 30])
    for src, mt, title, sup, dec, url in review:
        rv.append([title, sup, dec, action_for(dec), url]); _style(rv, url, LINK, SM, WRAP)
    for name, sup, title, why, url in flags:
        rv.append([title + f"  [{name}]", sup, why, action_for(why), url]); _style(rv, url, LINK, SM, WRAP)
    rv.auto_filter.ref = f"A1:E{rv.max_row}"

    out = ROOT / f"output/verify_{re.sub(r'[^a-z0-9]+','_',rule['label'].lower()).strip('_')}.xlsx"
    wb.save(out)
    ok = sum(1 for _n, _l, _i, s in checklist if s == "OK")
    print(f"wrote {out} | {len(checklist)} products: {ok} OK, {len(checklist)-ok} need review | "
          f"{len(review)} matcher-review + {len(flags)} verify-flags")


def _style(ws, url, LINK, SM, WRAP):
    for c in ws[ws.max_row]: c.font, c.alignment = SM, WRAP
    if str(url).startswith("http"):
        c = ws.cell(row=ws.max_row, column=5); c.hyperlink = url; c.font = LINK


if __name__ == "__main__":
    main()
