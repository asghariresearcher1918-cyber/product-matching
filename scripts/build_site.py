"""Load the real master catalogue into the Basis front-end prototype (self-contained, for testing).
Replaces the hard-coded PRODUCTS / SUPPLIERS with our 6,809 products and real suppliers, expands the category
chips + icons to our 15 categories, gates POM products (toxins, medicines, weight-loss, vaccines) behind the
verify flow per the compliance rule, and leaves the UI / logic untouched. Offers carry the real supplier
membership but NO prices yet (price tiers empty = 'pending supplier connection').
Input:  the uploaded prototype HTML (path arg) + catalogue/final/master_catalogue.csv + master_listing_index.csv
Output: output/site/basis.html
Usage: python -I scripts/build_site.py <prototype.html>"""
import collections, csv, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUT = ROOT / "output/site"; OUT.mkdir(parents=True, exist_ok=True)

POM_CATS = {"Toxin", "Medicines", "Weight-loss medicine", "Vaccine"}
# our category -> (display label, emoji icon)
CATDISPLAY = {
 "Toxin": ("Botulinum Toxins", "💉"),
 "Dermal filler": ("Dermal Fillers", "🧴"),
 "Skin booster / PN / mesotherapy": ("Skin Boosters & Meso", "💧"),
 "Biostimulator": ("Biostimulators", "✨"),
 "Fat dissolving": ("Fat Dissolving", "🫧"),
 "PDO threads": ("PDO Threads", "🧵"),
 "Weight-loss medicine": ("Weight-loss (POM)", "⚖️"),
 "Medicines": ("Medicines (POM)", "💊"),
 "Skincare, haircare & peels": ("Skincare & Peels", "🧪"),
 "Needles, cannulas & syringes": ("Needles, Cannulas & Syringes", "🪡"),
 "Clinic consumables & PPE": ("Consumables & PPE", "🧤"),
 "Devices & equipment": ("Devices & Equipment", "🔌"),
 "Beauty (nails/brows/lashes/PMU/makeup)": ("Beauty", "💅"),
 "Supplements": ("Supplements", "🟢"),
 "Vaccine": ("Vaccines (POM)", "🩹"),
}


def sslug(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower())[:24] or "sup"


def pkey(uid):
    return re.sub(r"[^A-Za-z0-9]+", "_", uid).strip("_")


def main():
    prods = list(csv.DictReader(open(ROOT / "catalogue/final/master_catalogue.csv", encoding="utf-8")))
    # supplier membership per uid
    members = collections.defaultdict(set)
    supnames = {}
    for r in csv.DictReader(open(ROOT / "catalogue/final/master_listing_index.csv", encoding="utf-8")):
        if not r.get("supplier"): continue
        sk = sslug(r["supplier"]); supnames[sk] = r["supplier"]; members[r["uid"]].add(sk)

    SUPPLIERS = {sk: {"name": nm, "delivery": 0, "freeOver": 0, "pro": False,
                      "speed": "TBC", "speedDays": 2, "remoteExtraDays": 0,
                      "rating": 0, "reviewCount": 0, "reviews": []} for sk, nm in sorted(supnames.items())}

    PRODUCTS = {}
    for r in prods:
        cat = r["category"]
        disp = CATDISPLAY.get(cat, (cat, "📦"))[0]
        pack = " ".join(x for x in [r["key_spec"], ("(" + r["market"] + ")") if r["market"] else ""] if x).strip()
        name = (r["product"] or r["uid"]).strip()
        offers = {sk: [] for sk in sorted(members.get(r["uid"], []))}  # real supplier membership, prices pending
        PRODUCTS[pkey(r["uid"])] = {"name": name, "pack": pack or "—", "category": disp,
                                    "group": r["equivalence_group"], "pom": cat in POM_CATS,
                                    "suppliers": int(r["suppliers"]), "defaultQty": 1, "offers": offers}

    html = SRC.read_text(encoding="utf-8")

    # 1) replace SUPPLIERS and PRODUCTS object literals
    js_sup = "var SUPPLIERS = " + json.dumps(SUPPLIERS, ensure_ascii=False) + ";"
    js_prd = "var PRODUCTS = " + json.dumps(PRODUCTS, ensure_ascii=False, separators=(",", ":")) + ";"
    html, n1 = re.subn(r"var SUPPLIERS = \{.*?\n  \};", lambda m: js_sup, html, count=1, flags=re.S)
    html, n2 = re.subn(r"var PRODUCTS = \{.*?\n  \};", lambda m: js_prd, html, count=1, flags=re.S)
    assert n1 == 1 and n2 == 1, f"block replace failed: SUP={n1} PRD={n2}"

    # 2) category chips (expand to our categories)
    chips = "\n".join(f'        <button class="chip" data-cat="{d}">{d}</button>'
                      for d, _ in sorted({v for v in CATDISPLAY.values()}, key=lambda x: x[0]))
    html, n3 = re.subn(r'(<button class="chip" data-cat="Dermal Fillers">.*?PPE &amp; Aftercare</button>)',
                       lambda m: chips.strip(), html, count=1, flags=re.S)

    # 3) categoryIcon map
    iconmap = "var map = " + json.dumps({d: i for d, i in CATDISPLAY.values()}, ensure_ascii=False) + ";"
    html, n4 = re.subn(r"var map = \{.*?\n    \};", lambda m: iconmap, html, count=1, flags=re.S)

    # 4) neutralise prototype-specific state that referenced old supplier/product keys
    html = re.sub(r"connections:\{[^}]*\}", "connections:{}", html, count=1)
    html = re.sub(r"var LAST_ORDER = \{[^}]*\};", "var LAST_ORDER = {};", html, count=1)

    # 5) POM gating: hide prescription-only products from public lists unless verified (compliance)
    html = html.replace(
        "    var keys = Object.keys(PRODUCTS);\n    if(!query) return keys;",
        "    var keys = Object.keys(PRODUCTS).filter(function(k){ return state.verified || !PRODUCTS[k].pom; });\n    if(!query) return keys;")
    html = html.replace(
        "    Object.keys(PRODUCTS).forEach(function(k){\n      var cat = PRODUCTS[k].category;\n      if(!seenCats[cat]){ seenCats[cat] = true; picks.push(k); }\n    });",
        "    Object.keys(PRODUCTS).forEach(function(k){\n      if(PRODUCTS[k].pom && !state.verified) return;\n      var cat = PRODUCTS[k].category;\n      if(!seenCats[cat]){ seenCats[cat] = true; picks.push(k); }\n    });")

    # 6) wording: 'offers' -> 'suppliers' on cards (no prices yet), and the empty-state copy
    html = html.replace("' offer'+(offerCount===1?'':'s')+'", "' supplier'+(offerCount===1?'':'s')+'")
    html = html.replace(
        "This category isn\\'t live in the MVP. Dermal Fillers, Skin Boosters and Cannulas are available to compare today.",
        "Prices appear once suppliers are connected. You can browse every category and product now; comparison turns on per supplier as they go live.")

    # 7) test banner so it is clear this is the data-load step, prices pending
    banner = ('<div style="background:#0E7C66;color:#fff;font:600 13px/1.4 Inter,sans-serif;'
              'padding:8px 16px;text-align:center;">Test build — real catalogue loaded ('
              + str(len(PRODUCTS)) + ' products, ' + str(len(SUPPLIERS)) + ' suppliers). '
              'Prices are pending supplier connection. Prescription-only items are hidden until you verify.</div>')
    html = html.replace("<body>", "<body>\n" + banner, 1)

    (OUT / "basis.html").write_text(html, encoding="utf-8")
    print("wrote", OUT / "basis.html", f"({len(html)//1024} KB)")
    print(f"products {len(PRODUCTS)} | suppliers {len(SUPPLIERS)} | chips n3={n3} icon n4={n4}")
    pom = sum(1 for p in PRODUCTS.values() if p["pom"])
    print(f"POM-gated products: {pom} | public: {len(PRODUCTS)-pom}")
    print("categories:", dict(collections.Counter(p["category"] for p in PRODUCTS.values())))


if __name__ == "__main__":
    main()
