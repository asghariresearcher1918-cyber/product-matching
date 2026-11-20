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
# one-line explainer per real category (what the product class is)
CATBLURB = {
 "Toxin": "a botulinum toxin type A injectable for muscle-relaxing (prescription-only) treatments",
 "Dermal filler": "a hyaluronic-acid dermal filler for restoring volume and contour",
 "Skin booster / PN / mesotherapy": "an injectable skin booster / bio-remodelling or mesotherapy treatment for skin quality",
 "Biostimulator": "a collagen-stimulating injectable (biostimulator) for gradual volume and skin firmness",
 "Fat dissolving": "an injectable fat-dissolving (lipolysis) treatment",
 "PDO threads": "an absorbable thread for lifting and tightening",
 "Weight-loss medicine": "a prescription weight-management medicine",
 "Medicines": "a clinic medicine (prescription-only / pharmacy item)",
 "Skincare, haircare & peels": "a professional cosmeceutical skincare, haircare or chemical-peel product",
 "Needles, cannulas & syringes": "an injection consumable (needle, cannula or syringe)",
 "Clinic consumables & PPE": "a clinic consumable / personal protective equipment item",
 "Devices & equipment": "a clinic device, machine or device consumable",
 "Beauty (nails/brows/lashes/PMU/makeup)": "a beauty product (nails, brows, lashes, PMU or makeup)",
 "Supplements": "an oral supplement / nutraceutical",
 "Vaccine": "a vaccine (prescription-only)",
}
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
    # supplier membership + example listing titles per uid
    members = collections.defaultdict(set)
    examples = collections.defaultdict(list)
    supnames = {}
    for r in csv.DictReader(open(ROOT / "catalogue/final/master_listing_index.csv", encoding="utf-8")):
        if not r.get("supplier"): continue
        sk = sslug(r["supplier"]); supnames[sk] = r["supplier"]; members[r["uid"]].add(sk)
        t = (r.get("listing_title") or "").strip()
        if t and len(examples[r["uid"]]) < 2 and t.lower() not in [x.lower() for x in examples[r["uid"]]]:
            examples[r["uid"]].append(t[:70])

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
        nsup = int(r["suppliers"])
        # description + key details from our catalogue data
        blurb = CATBLURB.get(cat, "a clinic product")
        made = f" Made by {r['manufacturer']}." if r["manufacturer"] else ""
        avail = (f"Compared across {nsup} suppliers in our catalogue." if nsup > 1
                 else "Currently listed by a single supplier (price comparison turns on when a second supplier carries it).")
        desc = f"{name} is {blurb}.{made} {avail}"
        details = [["Brand", r["brand"]], ["Manufacturer", r["manufacturer"]], ["Category", disp],
                   ["Equivalence group", r["equivalence_group"]], ["Spec / pack", pack],
                   ["Market variant", r["market"]], ["Suppliers (our catalogue)", str(nsup)]]
        if cat in POM_CATS:
            details.append(["Legal", "Prescription-only (POM) — price shown to verified professionals only"])
        if r["source"].startswith("http"):
            details.append(["Official reference", r["source"]])
        details = [[k, v] for k, v in details if v]
        PRODUCTS[pkey(r["uid"])] = {"name": name, "pack": "", "category": disp,
                                    "group": r["equivalence_group"], "pom": cat in POM_CATS,
                                    "suppliers": nsup, "defaultQty": 1, "offers": offers,
                                    "desc": desc, "details": details, "examples": examples.get(r["uid"], [])}

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

    # 6b) product "About" section: markup, render call, helpers and styles
    html = html.replace('<div class="qty-row">',
                        '<div class="p-about" id="productAbout"></div>\n\n      <div class="qty-row">', 1)
    html = html.replace(
        "    document.getElementById('productLowest').textContent = cheapestPublic ? fmt(cheapestPublic.unit) : '—';",
        "    document.getElementById('productLowest').textContent = cheapestPublic ? fmt(cheapestPublic.unit) : '—';\n"
        "    var _ab=document.getElementById('productAbout'); if(_ab) _ab.innerHTML = buildAbout(p);", 1)
    helpers = r"""
  function esc(s){ return (s==null?'':String(s)).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
  function buildAbout(p){
    var h='<div class="pa-title">About this product</div>';
    if(p.desc) h+='<p class="pa-desc">'+esc(p.desc)+'</p>';
    if(p.details&&p.details.length){ h+='<dl class="pa-details">';
      p.details.forEach(function(d){ var v=(d[0]==='Official reference')?'<a href="'+esc(d[1])+'" target="_blank" rel="noopener">View official source ↗</a>':esc(d[1]);
        h+='<dt>'+esc(d[0])+'</dt><dd>'+v+'</dd>'; }); h+='</dl>'; }
    if(p.examples&&p.examples.length){ h+='<div class="pa-examples"><div class="pa-ex-label">Listed by suppliers as</div><ul>'+
      p.examples.map(function(x){return '<li>'+esc(x)+'</li>';}).join('')+'</ul></div>'; }
    return h;
  }
  /* ---------------- PRODUCT VIEW ---------------- */"""
    html = html.replace("  /* ---------------- PRODUCT VIEW ---------------- */", helpers, 1)
    css = """
  .p-about{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md);padding:18px 20px;margin-top:18px;}
  .pa-title{font-family:var(--font-display);font-size:18px;font-weight:600;margin-bottom:10px;}
  .pa-desc{margin:0 0 14px;color:var(--ink-soft);max-width:68ch;}
  .pa-details{display:grid;grid-template-columns:max-content 1fr;gap:7px 20px;margin:0;font-size:14px;}
  .pa-details dt{color:var(--ink-faint);font-weight:600;}
  .pa-details dd{margin:0;color:var(--ink);min-width:0;word-break:break-word;}
  .pa-examples{margin-top:16px;font-size:13px;color:var(--ink-soft);}
  .pa-ex-label{font-weight:600;color:var(--ink-faint);margin-bottom:5px;text-transform:uppercase;letter-spacing:.04em;font-size:11px;}
  .pa-examples ul{margin:0;padding-inline-start:18px;}
  .pa-examples li{margin:2px 0;}
</style>"""
    html = html.replace("</style>", css, 1)

    # 6c) show more matches in the search autocomplete (was capped at 4)
    html = html.replace("matches.slice(0,4)", "matches.slice(0,10)")

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
