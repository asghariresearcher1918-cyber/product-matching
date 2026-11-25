"""Expand option-dropdown pages into one listing row PER purchasable option, using the structured variant data
(scripts/variants.py). A page that sells '1x 10ml £25' and '5x 10ml £95' becomes two rows, each carrying its own pack
(baked into the title so the matcher reads it), price and sku. Rows without real multi-pack options are left untouched.
Non-destructive: writes back to the same *_listing_map.csv, adding opt_price / opt_sku columns.
Usage: python -I scripts/expand_variants.py fat   (listing-map stem; run AFTER the catalogue, BEFORE reference_match)"""
import csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from variants import page_variants

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"


def main():
    stem = sys.argv[1]
    path = FINAL / f"{stem}_listing_map.csv"
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    cols = list(rows[0].keys())
    for c in ("opt_price", "opt_sku"):
        if c not in cols:
            cols.append(c)

    out, expanded = [], 0
    for r in rows:
        if r.get("opt_price") or r.get("opt_sku"):           # already an expanded option row -> keep (idempotent)
            out.append(r); continue
        vs = [v for v in page_variants(r.get("id", "")) if v.get("pack")]
        packs = {v["pack"] for v in vs}
        if len(packs) < 2:                                   # no real option dropdown -> keep the row as-is
            out.append(r); continue
        expanded += 1
        base = re.sub(r"\s*[-–(].*$", "", r["title"]).strip() or r["title"]   # drop any pack suffix on the raw title
        for v in sorted(vs, key=lambda v: v["pack"]):
            nr = dict(r)
            vol = v["volume_ml"] or ""
            nr["title"] = f"{base} ({v['pack']} x {vol})".strip()            # bake the option's pack so the matcher reads it
            nr["opt_price"] = v["price"]
            nr["opt_sku"] = v["sku"]
            out.append(nr)

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(out)
    print(f"{stem}: {len(rows)} rows -> {len(out)} rows ({expanded} option pages expanded into per-option offers)")


if __name__ == "__main__":
    main()
