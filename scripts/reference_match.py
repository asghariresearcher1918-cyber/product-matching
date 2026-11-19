"""Match supplier filler listings to the authoritative brand reference (data/reference/fillers.csv).
For brands that have a reference, each listing is mapped to a real reference product: the product NAME, pack and
volume come from the reference (fixing parsed-text errors like decimal splits and fake line variants); lidocaine and
pack multiplier are taken from the listing where the product allows it. Brands with no reference keep their current
catalogue entry. Obvious multi-product promo bundles are flagged for review, not coded as a product.
Rewrites catalogue/final/filler_products.csv + filler_listing_map.csv and writes catalogue/final/reference_names.csv
(uid -> authoritative display name) for the master to use. Run before master_catalogue.py.
Usage: python -I scripts/reference_match.py"""
import collections, csv, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"
MANUF = {"Teosyal": "Teoxane", "Juvederm": "Allergan / AbbVie", "Stylage": "Vivacy",
         "Restylane": "Galderma", "Belotero": "Merz", "Revolax": "Across (Korea)"}


def load_reference():
    ref = collections.defaultdict(list)
    for r in csv.DictReader(open(ROOT / "data/reference/fillers.csv", encoding="utf-8")):
        r["alias_list"] = [a for a in r["aliases"].split("|") if a]
        ref[r["brand"]].append(r)
    return ref


def pack_vol(pack):
    m = re.search(r"(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*ml", pack, re.I)
    if m: return int(m.group(1)), m.group(2)
    m = re.search(r"(\d+(?:\.\d+)?)\s*ml", pack)
    return 1, (m.group(1) if m else "")


def slug(*p):
    s = "-".join(x for x in p if x)
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9.]+", "-", s).strip("-")).upper()


def main():
    ref = load_reference()
    refbrands = set(ref)
    cur_products = {r["code"]: r for r in csv.DictReader(open(FINAL / "filler_products.csv", encoding="utf-8"))}
    listings = list(csv.DictReader(open(FINAL / "filler_listing_map.csv", encoding="utf-8")))

    maps, prods, refnames = [], {}, {}
    passthrough_codes = set()
    for m in listings:
        title = m["title"]; tl = title.lower()
        brand = m.get("brand", "")
        # detect a reference brand from the title even if our old brand label differs
        rb = next((b for b in refbrands if re.search(r"\b" + re.escape(b.lower()) + r"\b", tl)), None) or (brand if brand in refbrands else None)
        if not rb:
            # no reference for this brand -> keep the existing catalogue code untouched
            maps.append(dict(m, matched="passthrough")); passthrough_codes.add(m.get("code", "")); continue
        if re.search(r"\bfree\b|get 1|get one|bundle|\+ 1|buy 1 get|x\s*\d+.*\+", tl) and len(re.findall(r"\d", tl)) > 3:
            maps.append(dict(m, code="", brand=rb, matched="review-bundle",
                             decision="promo bundle / multi-item listing - not a single product")); continue
        # pick the reference product: longest matching alias, else the brand default
        best, blen = None, -1
        for p in ref[rb]:
            for a in p["alias_list"]:
                if a in tl and len(a) > blen:
                    best, blen = p, len(a)
        if best is None:
            best = next((p for p in ref[rb] if p["default"]), None)
        if best is None:
            maps.append(dict(m, code="", brand=rb, matched="review-nomatch",
                             decision=f"{rb}: no reference product matched")); continue
        # lidocaine
        lv = best["lidocaine"]
        lido = True if lv == "yes" else (False if lv == "no" else bool(re.search(r"lidocaine|lido\b|\+lido|with lido", tl)))
        base_n, vol = pack_vol(best["pack"])
        mt = re.search(r"(\d+)\s*x\s*\d|x\s*(\d+)\b|\b(\d+)\s*(?:syringes?|vials?)\b", tl)
        packn = int(next((g for g in (mt.groups() if mt else []) if g), base_n)) if mt else base_n
        market = "HG" if re.search(r"hologram", tl) else ("ROI" if re.search(r"\broi\b|irish|ireland", tl) else "")
        name = best["product_name"]
        line = re.sub(r"^" + re.escape(rb) + r"\s*", "", name).strip() or name
        code = slug("FILLER", rb, re.sub(r"[^A-Za-z0-9]+", "", line), "LIDO" if lido else "", f"{packn}X" if packn > 1 else "", market)
        grp = rb
        uid = "FIL:" + code
        refnames[uid] = name + (" with lidocaine" if lido and lv not in ("yes", "no") else "")
        maps.append(dict(m, code=code, brand=rb, line=line, matched="reference", decision=f"{name}; {vol}ml; pack {packn}; {'+lido' if lido else 'no lido'}"))
        p = prods.setdefault(code, dict(code=code, brand=rb, line=line, equivalence_group=grp, manufacturer=MANUF.get(rb, ""),
                                        ha="yes", volume_ml=vol, lidocaine="yes" if lido else "no", syringes_per_pack=packn,
                                        market=market or "UK/std", brand_verified="yes (reference)", source=best["source"],
                                        suppliers=set(), listings=0))
        p["suppliers"].add(m["supplier"]); p["listings"] += 1

    # finalise reference-matched products
    for p in prods.values():
        p["suppliers"] = len(p["suppliers"])
    # add back the untouched products for non-reference brands
    for code in passthrough_codes:
        if code and code in cur_products and code not in prods:
            prods[code] = cur_products[code]

    pc = ["code", "brand", "line", "equivalence_group", "manufacturer", "ha", "volume_ml", "lidocaine",
          "syringes_per_pack", "market", "brand_verified", "suppliers", "listings", "source"]
    with open(FINAL / "filler_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc, extrasaction="ignore"); w.writeheader()
        w.writerows(sorted(prods.values(), key=lambda p: (p["brand"], p["line"], p["code"])))
    with open(FINAL / "filler_listing_map.csv", "w", newline="", encoding="utf-8") as f:
        cols = list(listings[0].keys()) + [c for c in ("matched",) if c not in listings[0]]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(maps)
    with open(FINAL / "reference_names.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["uid", "name"]); w.writeheader()
        w.writerows([{"uid": u, "name": n} for u, n in refnames.items()])

    matched = sum(1 for m in maps if m.get("matched") == "reference")
    review = sum(1 for m in maps if str(m.get("matched", "")).startswith("review"))
    passth = sum(1 for m in maps if m.get("matched") == "passthrough")
    print(f"listings: {len(maps)} | reference-matched: {matched} | review(bundle/nomatch): {review} | passthrough(no ref brand): {passth}")
    print(f"reference-matched product codes: {sum(1 for p in prods.values() if isinstance(p.get('brand_verified',''), str) and 'reference' in str(p.get('brand_verified','')))}")
    for b in sorted(refbrands):
        codes = [p for p in prods.values() if p["brand"] == b and "reference" in str(p.get("brand_verified", ""))]
        print(f"  {b}: {len(codes)} codes")


if __name__ == "__main__":
    main()
