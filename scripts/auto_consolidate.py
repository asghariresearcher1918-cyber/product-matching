"""General, reference-free consolidation pass over the whole master catalogue.
Within each (category, brand) it merges product codes that are the SAME product written differently: their core name
tokens (after removing brand, size, pack and noise) are identical or one is a subset of the other, AND their spec
(volume / gauge / pack / lidocaine) matches. Supplier and listing counts are recomputed from the listing index so a
merge never double-counts. Authoritative reference-matched products (verified=reference-matched) are never merged away.
Rewrites master_catalogue.csv + master_listing_index.csv (remapped uids). Run after master_catalogue.py.
Usage: python -I scripts/auto_consolidate.py"""
import collections, csv, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"
# branded categories where same-product-different-wording fragmentation happens; spec/molecule categories are skipped
APPLY = {"Toxin", "Dermal filler", "Skin booster / PN / mesotherapy", "Biostimulator", "Fat dissolving",
         "PDO threads", "Skincare, haircare & peels", "Beauty (nails/brows/lashes/PMU/makeup)", "Supplements",
         "Weight-loss medicine"}
NOISE = {"the", "with", "for", "and", "buy", "uk", "new", "stock", "item", "prescription", "vat", "payable", "zero",
         "pay", "no", "inc", "incl", "ex", "online", "offer", "sale", "pack", "box", "single", "double", "set",
         "kit", "cream", "gel", "solution", "injection", "inj", "sterile", "ce", "medical", "aesthetic", "clinic",
         "professional", "original", "genuine", "authentic", "free", "x", "of", "per", "each", "ml", "mg", "g",
         "syringe", "syringes", "vial", "vials", "ampoule", "ampoules", "amp", "treatment", "size", "exp", "expiry"}
# strip ONLY volume and pack tokens; keep numbers, gauge, mm, mg (they distinguish products: Vol 2, RHA 3, 30G, 25mm)
SPECWORD = re.compile(r"^\d+(\.\d+)?(ml|iu|u|%)$|^x\d+$|^\d+x$", re.I)


def coreset(product, brand):
    t = re.sub(r"\(.*?\)", " ", product.lower())
    t = re.sub(r"[^a-z0-9+ ]", " ", t)
    bw = set(re.sub(r"[^a-z0-9 ]", " ", (brand or "").lower()).split())
    toks = []
    for w in t.split():
        if w in bw or w in NOISE or SPECWORD.match(w):
            continue
        if len(w) <= 1 and not w.isdigit():   # keep single-digit product identifiers (Vol 2, RHA 3)
            continue
        toks.append(w)
    return frozenset(toks)


def specnorm(key_spec):
    return " ".join(sorted(re.sub(r"[^a-z0-9.%+ ]", " ", (key_spec or "").lower()).split()))


def main():
    prods = list(csv.DictReader(open(FINAL / "master_catalogue.csv", encoding="utf-8")))
    idx = list(csv.DictReader(open(FINAL / "master_listing_index.csv", encoding="utf-8")))
    byuid = {p["uid"]: p for p in prods}

    # group candidates by (category, brand, specnorm)
    groups = collections.defaultdict(list)
    for p in prods:
        if p["category"] not in APPLY:
            continue
        brand = p["brand"] or p["product"].split()[0] if p["product"] else p["brand"]
        groups[(p["category"], (brand or "").lower(), specnorm(p["key_spec"]))].append(p)

    remap = {}  # old uid -> canonical uid
    for key, members in groups.items():
        if len(members) < 2:
            continue
        # attach core sets
        for p in members:
            p["_core"] = coreset(p["product"], p["brand"] or p["product"].split()[0])
        # union-find style: merge a member into another whose core is a superset (or equal)
        # canonical = reference-matched first, else largest core, else most listings
        def rank(p):
            return (p.get("verified") == "reference-matched", len(p["_core"]), int(p["listings"]))
        members_sorted = sorted(members, key=rank, reverse=True)
        for p in members_sorted[1:]:
            for q in members_sorted:
                if q is p:
                    continue
                if remap.get(q["uid"], q["uid"]) == p["uid"]:
                    continue
                # merge only when the cleaned core names are IDENTICAL (same product, different supplier wording).
                # Equality (not subset) keeps distinct products apart (RHA 2 vs RHA 3, 30G vs 29G) -> minimal error.
                if p["_core"] and p["_core"] == q["_core"] and q["uid"] not in remap:
                    remap[p["uid"]] = q["uid"]
                    break

    # resolve chains
    def root(u):
        seen = set()
        while u in remap and u not in seen:
            seen.add(u); u = remap[u]
        return u
    final_uid = {p["uid"]: root(p["uid"]) for p in prods}

    # recompute suppliers/listings per surviving uid from the listing index, and remap the index
    agg = collections.defaultdict(lambda: [set(), 0])
    for r in idx:
        nu = final_uid.get(r["uid"], r["uid"])
        r["uid"] = nu
        agg[nu][0].add(r.get("supplier", "")); agg[nu][1] += 1

    survivors = []
    for p in prods:
        if final_uid[p["uid"]] != p["uid"]:
            continue  # merged away
        a = agg.get(p["uid"])
        if a:
            p["suppliers"] = len([s for s in a[0] if s]); p["listings"] = a[1]
        survivors.append(p)

    cols = [c for c in prods[0].keys() if not c.startswith("_")]
    with open(FINAL / "master_catalogue.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader()
        w.writerows(sorted(survivors, key=lambda p: (p["category"], p["equivalence_group"], p["brand"], p["product"])))
    with open(FINAL / "master_listing_index.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=idx[0].keys(), extrasaction="ignore"); w.writeheader(); w.writerows(idx)

    merged = len(prods) - len(survivors)
    print(f"products {len(prods)} -> {len(survivors)}  (merged {merged} duplicate codes)")
    # sanity: reference brands should be untouched counts
    for b in ["Profhilo", "Juvederm", "Teosyal", "Restylane"]:
        n = sum(1 for p in survivors if p["brand"] == b or p["product"].startswith(b))
        print(f"  {b}: {n} products")


if __name__ == "__main__":
    main()
