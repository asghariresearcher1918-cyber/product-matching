"""Match supplier listings to authoritative brand references (data/reference/*.csv) for branded categories.
For a brand that has a reference, every listing is mapped to a real reference product: NAME, pack and volume come
from the reference (fixing parsed-text errors - decimal splits, fake line variants); lidocaine and pack multiplier
come from the listing where allowed. Hologram / UK&ROI packaging is folded into the base product (not a separate code).
Obvious multi-product promo bundles are flagged for review. Brands with no reference keep their current entry.
Runs for fillers and boosters; rewrites each *_products.csv + *_listing_map.csv and writes reference_names.csv.
Usage: python -I scripts/reference_match.py   (after filler_catalogue.py and booster_catalogue.py)"""
import collections, csv, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"
MANUF = {"Teosyal": "Teoxane", "Juvederm": "Allergan / AbbVie", "Stylage": "Vivacy", "Restylane": "Galderma",
         "Belotero": "Merz", "Revolax": "Across (Korea)", "Profhilo": "IBSA"}

CATS = [
 dict(kind="filler", ref="fillers.csv", lmap="filler_listing_map.csv", prod="filler_products.csv", tag="FIL", prefix="FILLER"),
 dict(kind="booster", ref="boosters.csv", lmap="booster_listing_map.csv", prod="booster_products.csv", tag="BST", prefix="BST"),
 dict(kind="skincare", ref="skincare.csv", lmap="skincare_listing_map.csv", prod="skincare_products.csv", tag="SKN", prefix="SKIN"),
]
BUNDLE = re.compile(r"\bfree\b|get 1|get one|\+ ?1 ?x|buy 1 get|bundle|worth £|multibuy", re.I)


def pack_vol(pack):
    m = re.search(r"(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*ml", pack or "", re.I)
    if m: return int(m.group(1)), m.group(2)
    m = re.search(r"(\d+(?:\.\d+)?)\s*ml", pack or "")
    return 1, (m.group(1) if m else "")


def slug(*p):
    s = "-".join(x for x in p if x)
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9.]+", "-", s).strip("-")).upper()


def match_one(tl, products):
    best, blen = None, -1
    for p in products:
        for a in p["alias_list"]:
            if a and a in tl and len(a) > blen:
                best, blen = p, len(a)
    return best or next((p for p in products if p["default"]), None)


def run(cfg, refnames):
    refpath = ROOT / "data/reference" / cfg["ref"]
    ref = collections.defaultdict(list)
    for r in csv.DictReader(open(refpath, encoding="utf-8")):
        r["alias_list"] = [a for a in r["aliases"].split("|") if a]
        ref[r["brand"]].append(r)
    refbrands = set(ref)
    cur = {r["code"]: r for r in csv.DictReader(open(FINAL / cfg["prod"], encoding="utf-8"))}
    listings = list(csv.DictReader(open(FINAL / cfg["lmap"], encoding="utf-8")))

    maps, prods, passthrough = [], {}, set()
    for m in listings:
        tl = m["title"].lower()
        brand = m.get("brand", "")
        rb = next((b for b in refbrands if re.search(r"\b" + re.escape(b.lower()) + r"\b", tl)), None) or (brand if brand in refbrands else None)
        if not rb:
            maps.append(dict(m, matched="passthrough")); passthrough.add(m.get("code", "")); continue
        if BUNDLE.search(tl):
            maps.append(dict(m, code="", brand=rb, matched="review-bundle",
                             decision="promo bundle / multi-item listing - not a single product")); continue
        best = match_one(tl, ref[rb])
        if best is None:
            maps.append(dict(m, code="", brand=rb, matched="review-nomatch", decision=f"{rb}: no reference product matched")); continue
        lv = best.get("lidocaine", "no")
        lido = True if lv == "yes" else (False if lv == "no" else bool(re.search(r"lidocaine|\+?lido\b|with lido", tl)))
        base_n, vol = pack_vol(best["pack"])
        mt = re.search(r"(\d+)\s*x\s*\d|\bx\s*(\d+)\b|\b(\d+)\s*(?:syringes?|vials?|pack)\b", tl)
        packn = int(next((g for g in (mt.groups() if mt else []) if g), base_n)) if mt else base_n
        if "kit" in best["product_name"].lower():
            packn = base_n  # a Kit is a fixed bundle - take its pack from the reference, not the listing
        name = best["product_name"]
        line = re.sub(r"^" + re.escape(rb) + r"\s*", "", name).strip() or name
        # hologram / ROI packaging is NOT a separate product -> no market in the code
        code = slug(cfg["prefix"], rb, re.sub(r"[^A-Za-z0-9]+", "", line), "LIDO" if lido else "", f"{packn}X" if packn > 1 else "")
        uid = cfg["tag"] + ":" + code
        refnames[uid] = name + (" with lidocaine" if lido and lv not in ("yes", "no") else "")
        maps.append(dict(m, code=code, brand=rb, line=line, matched="reference",
                         decision=f"{name}; {vol}ml; pack {packn}; {'+lido' if lido else 'no lido'}"))
        if cfg["kind"] == "filler":
            p = prods.setdefault(code, dict(code=code, brand=rb, line=line, equivalence_group=rb, manufacturer=MANUF.get(rb, ""),
                                            ha="yes", volume_ml=vol, lidocaine="yes" if lido else "no", syringes_per_pack=packn,
                                            market="UK/std", brand_verified="yes (reference)", source=best["source"], suppliers=set(), listings=0))
        elif cfg["kind"] == "booster":
            p = prods.setdefault(code, dict(code=code, active_class=best.get("active_class", ""), brand=rb, line=line,
                                            volume=(vol + "ml") if vol else "", pack=packn, market="", manufacturer=MANUF.get(rb, ""),
                                            brand_verified="yes (reference)", suppliers=set(), listings=0))
        else:  # skincare
            p = prods.setdefault(code, dict(code=code, function=best.get("active_class", ""), brand=rb, name=name,
                                            size=best["pack"], brand_verified="yes (reference)", suppliers=set(), listings=0))
        p["suppliers"].add(m["supplier"]); p["listings"] += 1

    for p in prods.values():
        p["suppliers"] = len(p["suppliers"])
    for code in passthrough:
        if code and code in cur and code not in prods:
            prods[code] = cur[code]

    if cfg["kind"] == "filler":
        pc = ["code", "brand", "line", "equivalence_group", "manufacturer", "ha", "volume_ml", "lidocaine",
              "syringes_per_pack", "market", "brand_verified", "suppliers", "listings", "source"]
        skey = lambda p: (p["brand"], p["line"], p["code"])
    elif cfg["kind"] == "booster":
        pc = ["code", "active_class", "brand", "line", "volume", "pack", "market", "manufacturer", "suppliers", "listings"]
        skey = lambda p: (p.get("active_class", ""), p["brand"], p["code"])
    else:  # skincare
        pc = ["code", "function", "brand", "name", "size", "suppliers", "listings"]
        skey = lambda p: (p.get("function", ""), p["brand"], p["code"])
    with open(FINAL / cfg["prod"], "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=pc, extrasaction="ignore"); w.writeheader()
        w.writerows(sorted(prods.values(), key=skey))
    cols = list(listings[0].keys()) + [c for c in ("matched",) if c not in listings[0]]
    with open(FINAL / cfg["lmap"], "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(maps)

    matched = sum(1 for m in maps if m.get("matched") == "reference")
    review = sum(1 for m in maps if str(m.get("matched", "")).startswith("review"))
    print(f"[{cfg['kind']}] listings {len(maps)} | matched {matched} | review {review} | passthrough {sum(1 for m in maps if m.get('matched')=='passthrough')}")
    for b in sorted(refbrands):
        n = len([p for p in prods.values() if p["brand"] == b and "reference" in str(p.get("brand_verified", ""))])
        print(f"    {b}: {n} codes")


def main():
    refnames = {}
    for cfg in CATS:
        run(cfg, refnames)
    with open(FINAL / "reference_names.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["uid", "name"]); w.writeheader()
        w.writerows([{"uid": u, "name": n} for u, n in refnames.items()])
    print("reference_names:", len(refnames))


if __name__ == "__main__":
    main()
