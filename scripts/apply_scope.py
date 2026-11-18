"""Add phase-1 scope to output/all_products_categorised.csv (run after categorize_all.py).
Adds columns: category_auto (category before scope moves), scope, scope_group. Idempotent.
Rules: data/medicine_scope.py (medicine categories) + CATEGORY_SCOPE below. Nothing is deleted.
Usage: python -I scripts/apply_scope.py"""
import collections, csv, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from medicine_scope import RULES, DEFAULT

CATEGORY_SCOPE = {
    "Training, services & marketing": "Phase 2 - services",
    "Not a product": "Removed - not a product",
    "Unclassified": "Check by hand",
    "Beauty (nails, brows, lashes, PMU, makeup)": "Phase 1 - owner to decide",
    "Supplements": "Phase 1 - owner to decide",
}
ACTION = {"keep": "Phase 1", "phase2": "Phase 2 - later", "remove": "Removed - general pharmacy"}

def main():
    p = ROOT / "output/all_products_categorised.csv"
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    for r in rows:
        r["category_auto"] = r.get("category_auto") or r["category"]
        cat = r["category_auto"]; r["category"] = cat
        name = ((r.get("page_title") or "") + " | " + r["title"]).lower()
        if cat in RULES:
            group, action = next(((g, a) for g, a, rx in RULES[cat] if re.search(rx, name)), DEFAULT)
            if action.startswith("move:"):
                r["category"] = action[5:]; action = "keep"
                group = f"moved from {cat}"
            r["scope"], r["scope_group"] = ACTION[action], group
        else:
            r["scope"], r["scope_group"] = CATEGORY_SCOPE.get(cat, "Phase 1"), ""
    cols = [c for c in rows[0].keys() if c not in ("category_auto", "scope", "scope_group")] + ["category_auto", "scope", "scope_group"]
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    for cat in RULES:
        rs = [r for r in rows if r["category_auto"] == cat]
        print(f"## {cat} ({len(rs)})")
        for (s, g), n in sorted(collections.Counter((r["scope"], r["scope_group"]) for r in rs).items()):
            print(f"   {n:4d}  {s:28s} {g}")
    print(collections.Counter(r["scope"] for r in rows))

if __name__ == "__main__":
    main()
