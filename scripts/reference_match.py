"""Match supplier listings to authoritative brand references (data/reference/*.csv) for branded categories.
For a brand that has a reference, every listing is mapped to a real reference product: NAME, pack and volume come
from the reference (fixing parsed-text errors - decimal splits, fake line variants); lidocaine and pack multiplier
come from the listing where allowed. Hologram / UK&ROI packaging is folded into the base product (not a separate code).
Obvious multi-product promo bundles are flagged for review. Brands with no reference keep their current entry.
Runs for fillers and boosters; rewrites each *_products.csv + *_listing_map.csv and writes reference_names.csv.
Usage: python -I scripts/reference_match.py   (after filler_catalogue.py and booster_catalogue.py)"""
import collections, csv, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from page_facts import page_text, image_text   # owner rule: read the whole page, then the image, before defaulting
except Exception:
    def page_text(_i): return ""
    def image_text(_i): return ""
FINAL = ROOT / "catalogue/final"
MANUF = {"Teosyal": "Teoxane", "Juvederm": "Allergan / AbbVie", "Stylage": "Vivacy", "Restylane": "Galderma",
         "Belotero": "Merz", "Revolax": "Across (Korea)", "Profhilo": "IBSA"}

CATS = [
 dict(kind="filler", ref="fillers.csv", lmap="filler_listing_map.csv", prod="filler_products.csv", tag="FIL", prefix="FILLER"),
 dict(kind="booster", ref="boosters.csv", lmap="booster_listing_map.csv", prod="booster_products.csv", tag="BST", prefix="BST"),
 dict(kind="skincare", ref="skincare.csv", lmap="skincare_listing_map.csv", prod="skincare_products.csv", tag="SKN", prefix="SKIN"),
 dict(kind="toxin", ref="toxins.csv", lmap="toxin_listing_map.csv", prod="toxin_products.csv", tag="TOX", prefix="TOX"),
 dict(kind="fat", ref="fat.csv", lmap="fat_listing_map.csv", prod="fat_products.csv", tag="FAT", prefix="FAT"),
 dict(kind="biostim", ref="biostim.csv", lmap="biostim_listing_map.csv", prod="biostim_products.csv", tag="BIO", prefix="BIO"),
]
ACCESSORY = re.compile(r"roller banner|\bbanner\b|poster|sticker|lanyard|t-?shirt|brochure|leaflet|display stand|shelf", re.I)
BUNDLE = re.compile(r"\bfree\b|get 1|get one|\+ ?1 ?x|buy 1 get|bundle|worth £|multibuy", re.I)


_PACK_STRICT = (r"box of\s*(\d+)", r"pack of\s*(\d+)",
                r"(\d+)\s*x\s*\d+(?:\.\d+)?\s*ml",     # 10 x 8ml / 10x8ml
                r"ml\s*x\s*(\d+)",                      # 8ml x 10 / 10mlx8
                r"\b(\d+)\s*(?:vials?|pcs|pieces|syringes?)\b")  # 10 vials
_PACK_LOOSE = (r"\bx\s*(\d+)\b", r"(\d+)\s*x\b")        # generic x10 / 10x (titles only)


_PACK_EXPLICIT = (r"box contents?:?\s*(\d+)\s*vials?", r"box of\s*(\d+)", r"pack of\s*(\d+)",
                  r"contains?\s*(\d+)\s*vials?")


def pack_count(text, strict=False):
    """How many vials/syringes in the pack. Returns None when the text does not state it (so the caller can read the
    page / image before defaulting). strict=True uses only vial/box/ml-anchored patterns (safe on long page text)."""
    for rx in (_PACK_STRICT if strict else _PACK_STRICT + _PACK_LOOSE):
        m = re.search(rx, text)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 60:
                return n
    return None


def pack_from_doc(text, brand):
    """Read the pack from a product PAGE or image where the text may list many other products (supplier price-lists).
    Only trust a pack token that sits next to THIS product's own brand name, so 'relfydess pack of 10' on the same
    page can't be mis-read as this product's pack. Returns None if the brand's own window states no pack."""
    bl = brand.lower()
    pats = _PACK_EXPLICIT + _PACK_STRICT
    usage = re.compile(r"divide|split|reconstitut|dissolv|draw up|mix|inject|per session|each area")
    for mb in re.finditer(re.escape(bl), text):
        window = text[mb.start():mb.start() + 150]       # the brand and the bracket/line right after it
        for rx in pats:
            mm = re.search(rx, window)
            if mm:
                n = int(mm.group(1))
                before = window[max(0, mm.start() - 40):mm.start()]   # skip usage text ("divide into 3 syringes")
                if 1 <= n <= 60 and not usage.search(before):
                    return n
    return None


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
    refbrands = sorted(ref, key=len, reverse=True)   # longest first: 'Linerase Hydro' wins over 'Linerase'
    cur = {r["code"]: r for r in csv.DictReader(open(FINAL / cfg["prod"], encoding="utf-8"))}
    listings = list(csv.DictReader(open(FINAL / cfg["lmap"], encoding="utf-8")))

    maps, prods, passthrough = [], {}, set()
    for m in listings:
        tl = m["title"].lower()
        tlsq = re.sub(r"[^a-z0-9]", "", tl)   # squashed (ignore spaces/punct): 'lipolab' ~ 'lipo lab'
        brand = m.get("brand", "")
        rb = (next((b for b in refbrands if re.search(r"\b" + re.escape(b.lower()) + r"\b", tl)), None)
              or next((b for b in refbrands if re.sub(r"[^a-z0-9]", "", b.lower()) in tlsq), None)
              or (brand if brand in refbrands else None))
        if not rb:
            maps.append(dict(m, matched="passthrough")); passthrough.add(m.get("code", "")); continue
        if ACCESSORY.search(tl):
            maps.append(dict(m, code="", brand=rb, matched="review-accessory",
                             decision="marketing / accessory (banner, poster...) - not a product")); continue
        if BUNDLE.search(tl):
            maps.append(dict(m, code="", brand=rb, matched="review-bundle",
                             decision="promo bundle / multi-item listing - not a single product")); continue
        best = match_one(tl, ref[rb])
        if best is None:
            maps.append(dict(m, code="", brand=rb, matched="review-nomatch", decision=f"{rb}: no reference product matched")); continue
        lv = best.get("lidocaine", "no")
        lido = True if lv == "yes" else (False if lv == "no" else bool(re.search(r"lidocaine|\+?lido\b|with lido", tl)))
        base_n, vol = pack_vol(best["pack"])
        packn, pack_src = pack_count(tl), "title"
        if packn is None and m.get("id"):                 # owner rule: read the whole page, then the image, before defaulting
            packn = pack_from_doc(page_text(m["id"]).lower(), rb); pack_src = "page"   # only trust a pack beside THIS brand
            if packn is None:
                packn = pack_from_doc((image_text(m["id"]) or "").lower(), rb); pack_src = "image(OCR)"
        if packn is None:
            packn, pack_src = base_n, "assumed (not stated)"
        if "kit" in best["product_name"].lower():
            packn = base_n; pack_src = "reference (kit)"  # a Kit is a fixed bundle - take its pack from the reference
        name = best["product_name"]
        line = re.sub(r"^" + re.escape(rb) + r"\s*", "", name).strip() or name
        pack_size = ""
        if cfg["kind"] == "biostim":
            # real commercial name = <canonical> [with Lidocaine] (<market pack>); Pack size is a separate attribute.
            strength = best.get("strength", "")
            # rule: whenever the name carries mg or ml, prefix the unit count too, even when it is 1 (e.g. '1 x 200mg')
            if strength:                                   # powder -> unit count x strength (mg)
                pack_size = f"{packn} x {strength}"
                mkt = pack_size                            # e.g. 'AestheFill (1 x 200mg)'
            elif vol:                                      # gel / liquid -> unit count x volume (ml)
                pack_size = f"{packn} x {vol}ml"
                mkt = pack_size                            # e.g. 'Radiesse (1 x 1.5ml)'
            else:                                          # no mg/ml stated -> just the vial count, no 'N x'
                pack_size = f"{packn} vials" if packn > 1 else "1 vial"
                mkt = (f"{packn} vials" if packn > 1 else "")
            disp = name + (" with Lidocaine" if lido else "") + (f" ({mkt})" if mkt else "")
            sizetok = re.sub(r"[^A-Za-z0-9]+", "", best.get("variant", "") or strength or vol or "")
            code = slug(cfg["prefix"], rb, sizetok, "LIDO" if lido else "", f"{packn}X" if packn > 1 else "")
            uid = cfg["tag"] + ":" + code
            refnames[uid] = disp
            maps.append(dict(m, code=code, brand=rb, line=line, matched="reference",
                             decision=f"{disp}; pack {packn} ({pack_src})"))
        else:
            # hologram / ROI packaging is NOT a separate product -> no market in the code
            code = slug(cfg["prefix"], rb, re.sub(r"[^A-Za-z0-9]+", "", line), "LIDO" if lido else "", f"{packn}X" if packn > 1 else "")
            uid = cfg["tag"] + ":" + code
            refnames[uid] = name + (" with lidocaine" if lido and lv not in ("yes", "no") else "")
            maps.append(dict(m, code=code, brand=rb, line=line, matched="reference",
                             decision=f"{name}; {vol}ml; pack {packn} ({pack_src}); {'+lido' if lido else 'no lido'}"))
        if cfg["kind"] == "filler":
            p = prods.setdefault(code, dict(code=code, brand=rb, line=line, equivalence_group=rb, manufacturer=MANUF.get(rb, ""),
                                            ha="yes", volume_ml=vol, lidocaine="yes" if lido else "no", syringes_per_pack=packn,
                                            market="UK/std", brand_verified="yes (reference)", source=best["source"], suppliers=set(), listings=0))
        elif cfg["kind"] == "booster":
            p = prods.setdefault(code, dict(code=code, active_class=best.get("active_class", ""), brand=rb, line=line,
                                            volume=(vol + "ml") if vol else "", pack=packn, market="", manufacturer=MANUF.get(rb, ""),
                                            brand_verified="yes (reference)", suppliers=set(), listings=0))
        elif cfg["kind"] == "skincare":
            p = prods.setdefault(code, dict(code=code, function=best.get("active_class", ""), brand=rb, name=name,
                                            size=best["pack"], brand_verified="yes (reference)", suppliers=set(), listings=0))
        elif cfg["kind"] == "toxin":
            p = prods.setdefault(code, dict(code=code, brand=rb, molecule=best.get("molecule", ""),
                                            equivalence_group=best.get("active_class", ""), manufacturer=best.get("manufacturer", ""),
                                            units_per_vial=best.get("units", ""), unit_type=best.get("unit_type", ""),
                                            volume_ml=best.get("volume", ""), vials_per_pack=packn, total_units="",
                                            licensed_use="", official_pack_sizes="", note="", source=best["source"],
                                            status="reference", suppliers=set(), listings=0))
        elif cfg["kind"] == "biostim":
            p = prods.setdefault(code, dict(code=code, brand=rb, variant=best.get("variant", ""),
                                            active_agent=best.get("active_agent", ""), equivalence_group=best.get("equivalence_group", ""),
                                            manufacturer=best.get("manufacturer", ""), strength=best.get("strength", ""),
                                            volume_ml=vol, vials_per_pack=packn, pack_size=pack_size, lidocaine="yes" if lido else "no",
                                            agent_verified=("yes (reference)" if best.get("active_agent") != "unknown" else "confirm with supplier"),
                                            note=best.get("equivalence_group", ""), source=best["source"], suppliers=set(), listings=0))
        else:  # fat dissolving
            p = prods.setdefault(code, dict(code=code, brand=rb, variant=best.get("variant", ""),
                                            active_agent=best.get("active_agent", ""), equivalence_group=best.get("active_class", ""),
                                            manufacturer=best.get("manufacturer", ""), volume_ml=best.get("volume", ""),
                                            vials_per_pack=packn, agent_verified="yes (reference)", note="",
                                            source=best["source"], suppliers=set(), listings=0))
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
    elif cfg["kind"] == "skincare":
        pc = ["code", "function", "brand", "name", "size", "suppliers", "listings"]
        skey = lambda p: (p.get("function", ""), p["brand"], p["code"])
    elif cfg["kind"] == "toxin":
        pc = ["code", "brand", "molecule", "equivalence_group", "manufacturer", "units_per_vial", "unit_type", "volume_ml",
              "vials_per_pack", "total_units", "licensed_use", "official_pack_sizes", "note", "source", "status", "suppliers", "listings"]
        skey = lambda p: (p["brand"], p["code"])
    elif cfg["kind"] == "biostim":
        pc = ["code", "brand", "variant", "active_agent", "equivalence_group", "manufacturer", "strength", "volume_ml",
              "vials_per_pack", "pack_size", "lidocaine", "agent_verified", "suppliers", "listings", "note", "source"]
        skey = lambda p: (p.get("equivalence_group", ""), p["brand"], p["code"])
    else:  # fat dissolving
        pc = ["code", "brand", "variant", "active_agent", "equivalence_group", "manufacturer", "volume_ml",
              "vials_per_pack", "agent_verified", "suppliers", "listings", "note"]
        skey = lambda p: (p.get("active_agent", ""), p["brand"], p["code"])
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
