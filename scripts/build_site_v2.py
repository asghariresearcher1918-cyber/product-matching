"""Build the v2 site: the SAME Basis prototype, but driven by the AestheticsProcure C01-C14 taxonomy
(scripts/taxonomy_map.py -> catalogue/final/taxonomy_v2.csv), fully separate from v1 (output/site/basis_v2.html).
Top-level menu = the 14 C-categories + the owner-approved standalone Weight Management; each product keeps a
breadcrumb (primary category > subcategory) and its taxonomy IDs. Prices still pending supplier connection.
Usage: python -I scripts/build_site_v2.py <prototype.html>"""
import collections, csv, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pack_size import size_of, resolve_pack, pack_label, display_name
from read_rules import read_pack, read_size, read_packaging

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1])
OUT = ROOT / "output/site"; OUT.mkdir(parents=True, exist_ok=True)

# top-level C-id -> (display label, icon). Primary ids like 'C03.02' resolve by their 'C##' prefix; 'WLM' is standalone.
TOP = {
 "C01": ("Dermal Fillers", "🧴"), "C02": ("Botulinum Toxins", "💉"),
 "C03": ("Skin Rejuvenation & Regeneration", "✨"), "C04": ("Fat Dissolving & Body Contouring", "🫧"),
 "C05": ("Threads", "🧵"), "C06": ("Skincare & Chemical Peels", "🧪"),
 "C07": ("Hair & Scalp Treatments", "💆"), "C08": ("Pharmacy (Medicines)", "💊"),
 "C09": ("IV, IM & Wellness", "💧"), "C10": ("Clinical Consumables", "🧰"),
 "C11": ("Infection Control & PPE", "🧤"), "C12": ("Devices & Equipment", "🔌"),
 "C13": ("Surgical & Medical Supplies", "🩹"), "C14": ("Beauty & Salon Supplies", "💅"),
 "WLM": ("Weight Management", "⚖️"),
}
POM_TOP = {"C02", "C08", "WLM"}          # prescription-only top-levels (toxins, medicines/vaccines, weight-loss)


def top_of(pid):
    if pid.startswith("WLM"): return "WLM"
    m = re.match(r"(C\d\d)", pid)
    return m.group(1) if m else "C08"


def sslug(s): return re.sub(r"[^a-z0-9]+", "", s.lower())[:24] or "sup"
def pkey(uid): return re.sub(r"[^A-Za-z0-9]+", "_", uid).strip("_")


def build_data():
    """Build the PRODUCTS and SUPPLIERS front-end objects from the master catalogue + v2 taxonomy.
    Shared by the full site build (main) and the data-only patcher, so pack/size are defined once."""
    prods = {r["uid"]: r for r in csv.DictReader(open(ROOT / "catalogue/final/master_catalogue.csv", encoding="utf-8"))}
    tax = {r["uid"]: r for r in csv.DictReader(open(ROOT / "catalogue/final/taxonomy_v2.csv", encoding="utf-8"))}

    members = collections.defaultdict(set); examples = collections.defaultdict(list); supnames = {}
    for r in csv.DictReader(open(ROOT / "catalogue/final/master_listing_index.csv", encoding="utf-8")):
        if not r.get("supplier"): continue
        sk = sslug(r["supplier"]); supnames[sk] = r["supplier"]; members[r["uid"]].add(sk)
        t = (r.get("listing_title") or "").strip()
        if t and len(examples[r["uid"]]) < 2 and t.lower() not in [x.lower() for x in examples[r["uid"]]]:
            examples[r["uid"]].append(t[:70])

    SUPPLIERS = {sk: {"name": nm, "delivery": 0, "freeOver": 0, "pro": False, "speed": "TBC", "speedDays": 2,
                      "remoteExtraDays": 0, "rating": 0, "reviewCount": 0, "reviews": []} for sk, nm in sorted(supnames.items())}

    # product uid -> image URLs (referenced straight from the pharmacy CDN; one listing's own gallery = distinct
    # angles, de-duplicated — we do NOT merge every supplier's near-duplicate photo).
    imgurl = {}
    imgcsv = ROOT / "catalogue/final/listing_images.csv"
    if imgcsv.exists():
        for r in csv.DictReader(open(imgcsv, encoding="utf-8")):
            u = [x for x in (r.get("image_urls") or "").split("|") if x.startswith("http")]
            if u:
                imgurl[r["id"]] = u
    MAPS = [("toxin", "TOX"), ("filler", "FIL"), ("booster", "BST"), ("biostim", "BIO"), ("fat", "FAT"),
            ("thread", "THR"), ("weight", "WGT"), ("medicine", "MED"), ("skincare", "SKN"), ("needle", "NDL"),
            ("consumable", "CON"), ("device", "DEV"), ("bty", "BTY"), ("sup", "SUP"), ("vac", "VAC")]
    # embedded base64 thumbnails (data URIs) so images show inside the claude.ai preview, which blocks external CDN
    # images. Per-LISTING thumbnails (build_listing_thumbs.py) let each supplier show its OWN photo in a product's
    # comparison, so same-named brand-less listings can be told apart.
    import json as _json
    lthumbs = {}
    ltj = ROOT / "catalogue/final/listing_thumbs.json"
    if ltj.exists():
        lthumbs = _json.loads(ltj.read_text())
    uid_images = {}
    uid_lids = {}                                       # uid -> [listing ids] (to read pack/size by the owner rule)
    uid_supthumb = collections.defaultdict(dict)       # uid -> {supplier_slug: index into THUMBS pool}
    thumb_pool = {}                                    # data-URI -> index (dedupe: identical photos stored once)
    for stem, tag in MAPS:
        p = ROOT / f"catalogue/final/{stem}_listing_map.csv"
        if not p.exists():
            continue
        for m in csv.DictReader(open(p, encoding="utf-8")):
            code = m.get("code", "")
            if not code:
                continue
            uid = f"{tag}:{code}"
            uid_lids.setdefault(uid, []).append(m.get("id", ""))   # listing ids, to read pack/size by the owner rule
            u = imgurl.get(m.get("id", ""))
            if u and uid not in uid_images:                # first listing that has images = the product's gallery
                uid_images[uid] = u[:4]
            th = lthumbs.get(m.get("id", ""))
            sk = sslug(m.get("supplier", ""))
            if th and sk and sk not in uid_supthumb[uid]:  # first thumb per supplier for this product
                idx = thumb_pool.get(th)
                if idx is None:
                    idx = thumb_pool[th] = len(thumb_pool)
                uid_supthumb[uid][sk] = idx

    PRODUCTS = {}
    for uid, r in prods.items():
        t = tax.get(uid)
        if not t: continue
        pid = t["primary_category_id"]; top = top_of(pid)
        disp, _ = TOP.get(top, (t["primary_category"] or "Other", "📦"))
        sub = t["subcategory"] or ""
        subid = t["subcategory_id"] or ""
        crumb = f'{top} {TOP.get(top,["",""])[0]}' + (f' › {sub} ({subid})' if sub else (f' › {t["primary_category"]}' if pid != top else ""))
        pom = top in POM_TOP
        name = (r["product"] or uid).strip()
        pack = r["key_spec"]
        # SIZE and PACK are read by the ONE shared owner rule (read_rules), identically for every category, from the
        # product's own listing page(s) — not per-category guesses. First listing that states a value wins.
        _lids = [x for x in uid_lids.get(uid, []) if x][:4]
        size = ""
        for _lid in (_lids or [None]):
            size = read_size(name, _lid)
            if size:
                break
        size = size or size_of(r["key_spec"]) or (r["key_spec"] or "")
        qty = ""; unit = ""
        for _lid in (_lids or [None]):
            qty, unit, _nested = read_packaging(name, _lid)   # owner rule: pack + the shop's real unit word (box/pack/case…)
            if qty:
                break
        if not qty:
            qty, _ = resolve_pack(name, r["pack"])      # fall back to the matched catalogue pack (branded pen/vial/syringe)
        name = display_name(name, qty, unit)                           # distinguish pack variants of the same item
        nsup = int(r["suppliers"])
        offers = {sk: [] for sk in sorted(members.get(uid, []))}
        supplier_names = ", ".join(supnames[sk] for sk in sorted(members.get(uid, [])) if sk in supnames) or "—"
        cat_label = f'{disp}' + (f" › {sub}" if sub else "")
        made = f" Made by {r['manufacturer']}." if r["manufacturer"] else ""
        avail_txt = ("Compared across %d suppliers in our catalogue." % nsup if nsup > 1
                     else "Currently listed by a single supplier (price comparison turns on when a second supplier carries it).")
        desc = f"{name} — {disp}" + (f" › {sub}" if sub else "") + f".{made} {avail_txt}"
        # fixed product-page layout (owner spec): these seven rows always shown, in this order; Size left blank when
        # the product has no volume/strength; Official reference appended when a licence/SmPC link exists.
        details = [
            ["Category", cat_label],
            ["Brand", r["brand"] or "non brand"],
            ["Size (volume / strength)", size],
            ["Pack (units per pack)", qty],
            ["Supplier", supplier_names],
            ["Prescription", "Required" if pom else "Not required"],
            ["Availability", "In stock" if nsup >= 1 else "Out of stock"],
        ]
        if r["source"].startswith("http"):
            details.append(["Official reference", r["source"]])
        _sth = uid_supthumb.get(uid, {})
        PRODUCTS[pkey(uid)] = {"name": name, "pack": pack_label(size, qty, unit), "size": size, "qty": qty,
                               "category": disp, "group": sub or t["primary_category"],
                               "pom": pom, "suppliers": nsup, "defaultQty": 1, "offers": offers,
                               "desc": desc, "details": details, "examples": examples.get(uid, []),
                               "images": uid_images.get(uid, []),
                               "supThumbs": _sth}      # per-supplier photos as indices into THUMBS; the product
                                                       # thumb is derived JS-side (first value)
    THUMBS = [None] * len(thumb_pool)
    for uri, idx in thumb_pool.items():
        THUMBS[idx] = uri
    return PRODUCTS, SUPPLIERS, THUMBS


def main():
    PRODUCTS, SUPPLIERS, THUMBS = build_data()
    html = SRC.read_text(encoding="utf-8")
    js_sup = "var SUPPLIERS = " + json.dumps(SUPPLIERS, ensure_ascii=False) + ";"
    js_prd = "var PRODUCTS = " + json.dumps(PRODUCTS, ensure_ascii=False, separators=(",", ":")) + ";"
    js_thm = "var THUMBS = " + json.dumps(THUMBS, ensure_ascii=False, separators=(",", ":")) + ";"
    html, n1 = re.subn(r"var SUPPLIERS = \{.*?\n  \};", lambda m: js_sup, html, count=1, flags=re.S)
    html, n2 = re.subn(r"var PRODUCTS = \{.*?\n  \};", lambda m: js_prd, html, count=1, flags=re.S)
    html, nt = re.subn(r"var THUMBS = \[.*?\];", lambda m: js_thm, html, count=1, flags=re.S)
    assert n1 == 1 and n2 == 1, f"block replace failed: SUP={n1} PRD={n2}"

    order = [TOP[k][0] for k in ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11", "C12", "C13", "C14", "WLM"]]
    chips = "\n".join(f'        <button class="chip" data-cat="{d}">{d}</button>' for d in order)
    html, n3 = re.subn(r'(<button class="chip" data-cat="Dermal Fillers">.*?PPE &amp; Aftercare</button>)',
                       lambda m: chips.strip(), html, count=1, flags=re.S)
    iconmap = "var map = " + json.dumps({d: i for d, i in TOP.values()}, ensure_ascii=False) + ";"
    html, n4 = re.subn(r"var map = \{.*?\n    \};", lambda m: iconmap, html, count=1, flags=re.S)

    html = re.sub(r"connections:\{[^}]*\}", "connections:{}", html, count=1)
    html = re.sub(r"var LAST_ORDER = \{[^}]*\};", "var LAST_ORDER = {};", html, count=1)
    html = html.replace(
        "  function fmt(pence){ return '£' + (pence/100).toFixed(2); }",
        "  function fmt(pence){ return '£' + (pence/100).toFixed(2); }\n"
        "  function pomLock(key){ return !!(PRODUCTS[key] && PRODUCTS[key].pom && !state.verified); }\n"
        "  function priceCell(key,best){ return pomLock(key) ? '🔒 Login' : (best ? fmt(best.unit) : '—'); }")
    html = html.replace("(best?fmt(best.unit):'—')", "priceCell(k,best)")
    html = html.replace("' offer'+(offerCount===1?'':'s')+'", "' supplier'+(offerCount===1?'':'s')+'")
    html = html.replace(
        "This category isn\\'t live in the MVP. Dermal Fillers, Skin Boosters and Cannulas are available to compare today.",
        "Prices appear once suppliers are connected. You can browse every category and product now; comparison turns on per supplier as they go live.")
    html = html.replace('<div class="qty-row">', '<div class="p-about" id="productAbout"></div>\n\n      <div class="qty-row">', 1)
    html = html.replace(
        "    document.getElementById('productLowest').textContent = cheapestPublic ? fmt(cheapestPublic.unit) : '—';",
        "    document.getElementById('productLowest').textContent = pomLock(key) ? 'Login to view price' : (cheapestPublic ? fmt(cheapestPublic.unit) : '—');\n"
        "    var _ab=document.getElementById('productAbout'); if(_ab) _ab.innerHTML = buildAbout(p);", 1)
    helpers = r"""
  function esc(s){ return (s==null?'':String(s)).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
  function buildAbout(p){
    var h='<div class="pa-title">About this product</div>';
    if(p.images&&p.images.length){ h+='<div class="pa-gallery">'+p.images.map(function(u,i){
      return '<img src="'+esc(u)+'" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"'+(i===0?' class="main"':'')+'>';
    }).join('')+'</div>'; }
    if(p.details&&p.details.length){ h+='<dl class="pa-details">';
      p.details.forEach(function(d){ var v=(d[0]==='Official reference')?'<a href="'+esc(d[1])+'" target="_blank" rel="noopener">View official source ↗</a>':esc(d[1]);
        h+='<dt>'+esc(d[0])+'</dt><dd>'+(v===''?'—':v)+'</dd>'; }); h+='</dl>'; }
    if(p.desc){ h+='<div class="pa-sec">Description</div><p class="pa-desc">'+esc(p.desc)+'</p>'; }
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
  .pa-sec{font-weight:600;color:var(--ink-faint);margin:16px 0 6px;text-transform:uppercase;letter-spacing:.04em;font-size:11px;}
  .pa-gallery{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;}
  .pa-gallery img{width:84px;height:84px;object-fit:contain;background:#fff;border:1px solid var(--border);border-radius:8px;padding:4px;}
  .pa-gallery img.main{width:180px;height:180px;}
  @media(max-width:520px){.pa-gallery img.main{width:140px;height:140px;}}
  .pa-details{display:grid;grid-template-columns:max-content 1fr;gap:7px 20px;margin:0;font-size:14px;}
  .pa-details dt{color:var(--ink-faint);font-weight:600;}
  .pa-details dd{margin:0;color:var(--ink);min-width:0;word-break:break-word;}
  .pa-examples{margin-top:16px;font-size:13px;color:var(--ink-soft);}
  .pa-ex-label{font-weight:600;color:var(--ink-faint);margin-bottom:5px;text-transform:uppercase;letter-spacing:.04em;font-size:11px;}
  .pa-examples ul{margin:0;padding-inline-start:18px;}
  .pa-examples li{margin:2px 0;}
</style>"""
    html = html.replace("</style>", css, 1)
    html = html.replace("matches.slice(0,4).forEach", "matches.forEach")
    banner = ('<div style="background:#1f3a5f;color:#fff;font:600 13px/1.4 Inter,sans-serif;padding:8px 16px;text-align:center;">'
              'v2 taxonomy build (C01–C14) — ' + str(len(PRODUCTS)) + ' products, ' + str(len(SUPPLIERS)) +
              ' suppliers. Prices pending supplier connection; prescription-only items hidden until verified.</div>')
    html = html.replace("<body>", "<body>\n" + banner, 1)

    (OUT / "basis_v2.html").write_text(html, encoding="utf-8")
    print("wrote", OUT / "basis_v2.html", f"({len(html)//1024} KB)")
    print(f"products {len(PRODUCTS)} | suppliers {len(SUPPLIERS)} | chips n3={n3} icon n4={n4}")
    print("top-level categories:", dict(collections.Counter(p["category"] for p in PRODUCTS.values())))


if __name__ == "__main__":
    main()
