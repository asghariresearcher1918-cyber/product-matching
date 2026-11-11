"""Step 5 - draft a stratified gold set (rows for the domain owner to label) and score results against it.
Usage: python -I scripts/gold_sample.py sample [N]   -> gold/gold_set_to_label.csv
       python -I scripts/gold_sample.py score         -> accuracy of output/scope/products_grouped.csv vs gold/gold_set_labelled.csv"""
import collections, csv, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
LABEL_COLS = ["gold_kind", "gold_family (brand + line)", "gold_lidocaine (yes/no)", "gold_market (UK/KR/other)",
              "gold_strength", "gold_unit_count", "gold_unit_volume_ml", "notes"]

def sample(n):
    rows = list(csv.DictReader(open(ROOT / "data" / "scope_rows.csv", encoding="utf-8")))
    random.seed(20261111)
    by = collections.defaultdict(list)
    for r in rows:
        by[r["brand"]].append(r)
    # every brand sold by >=2 suppliers gets at least 1 row; big brands get more (sqrt-proportional); tricky words oversampled
    tricky = lambda r: any(w in r["title"].lower() for w in ("clone", "replaced", "alternative", "uk", "korea", "single", "lido", "bundle", "kit"))
    pick = []
    brands = sorted(by, key=lambda b: -len({r["supplier"] for r in by[b]}))
    weights = {b: len(by[b]) ** 0.5 for b in brands if len({r["supplier"] for r in by[b]}) >= 2}
    tot = sum(weights.values())
    for b, w in weights.items():
        k = max(1, round(n * w / tot))
        pool = sorted(by[b], key=lambda r: (not tricky(r), random.random()))
        pick += pool[: min(k, len(pool))]
    pick = pick[:n]
    out = ROOT / "gold" / "gold_set_to_label.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "supplier", "brand", "title", "url"] + LABEL_COLS)
        for r in sorted(pick, key=lambda r: (r["brand"], r["title"])):
            w.writerow([r["id"], r["supplier"], r["brand"], r["title"], r["url"]] + [""] * len(LABEL_COLS))
    print(out, len(pick), "rows,", len({r['brand'] for r in pick}), "brands")

def score():
    g = {r["id"]: r for r in csv.DictReader(open(ROOT / "gold" / "gold_set_labelled.csv", encoding="utf-8"))}
    p = {r["id"]: r for r in csv.DictReader(open(ROOT / "output" / "scope" / "products_grouped.csv", encoding="utf-8"))}
    fields = [("gold_lidocaine (yes/no)", "lidocaine"), ("gold_unit_count", "unit_count"), ("gold_unit_volume_ml", "unit_volume_ml"), ("gold_kind", "kind")]
    for gk, pk in fields:
        pairs = [(g[i][gk].strip().lower(), p[i][pk].strip().lower()) for i in g if i in p and g[i][gk].strip()]
        ok = sum(a == b for a, b in pairs)
        print(f"{pk}: {ok}/{len(pairs)} = {ok / max(1, len(pairs)):.1%}")
    fam = [(g[i]["gold_family (brand + line)"].lower(), p[i]["family_name"].lower()) for i in g if i in p and g[i]["gold_family (brand + line)"]]
    print("family:", sum(a == b for a, b in fam), "/", len(fam))

if __name__ == "__main__":
    sample(int(sys.argv[2]) if len(sys.argv) > 2 else 250) if sys.argv[1] == "sample" else score()
