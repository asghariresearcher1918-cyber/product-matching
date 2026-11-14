"""Categorise ALL rows from their product pages (not the title alone).

Each row gets votes from independent signals, each pointing to one category:
  S1 supplier's own category (breadcrumb, WooCommerce product_cat, Shopify type/vendor, URL path, 'Category' field)
  S2 page title (the product name shown on the page)
  S3 brand dictionary (known brands -> category)
  S4 legal / medicine-type fields shown on the page (Legal Category: POM / P / GSL / MD, Medicine Type ...)
  S5 description text (weaker)
  S6 listing title (weakest; used alone only as a last resort)
confidence: high = >=2 independent signals agree and no strong conflict; medium = one strong signal; low = weak/conflicting
Rows with low confidence go to the manual review list; manual decisions live in data/category_overrides.csv (id,category,note).
Outputs: output/all_products_categorised.csv, output/category_review.csv
Usage: python -I scripts/categorize_all.py
"""
import collections
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CATS = [
    "Toxin", "Dermal filler", "Skin booster / polynucleotide / mesotherapy", "Biostimulator", "Fat dissolving",
    "PDO threads", "Vitamin & IV therapy", "Weight-loss medicine", "Medicine - injectable / anaesthetic / emergency",
    "Medicine - oral", "Medicine - topical / eye / other", "Vaccine", "Needles, cannulas & syringes",
    "Clinic consumables & PPE", "Devices & equipment", "Skincare, haircare & peels", "Supplements",
    "Beauty (nails, brows, lashes, PMU, makeup)", "Training, services & marketing", "Not a product",
]

# keyword rules: (category, regex). Order matters only for ties. Applied to names and to supplier categories.
R = [
    ("Not a product", r"^\s*\d+\s*$|\bdelivery\b(?!.*(system|device|pen))|postage|shipping charge|gift ?card|voucher|deposit\b|test product"),
    ("Training, services & marketing", r"\bcourse\b|training (course|day|package|bundle)|masterclass|webinar|demo day|\bpull[- ]?up banner|poster|leaflet|brochure|consultation form|aftercare (advice|card)|post treatment guide|marketing|merchandise|display stand|certificate\b|\bacademy\b|clinic sign"),
    ("Vaccine", r"vaccin|\bmmr\b|influenza|\bflu\b(?!id)|hepatitis [ab]|engerix|twinrix|gardasil|priorix|typhim|havrix|rabies|shingrix|bexsero|menquadfi|nimenrix|\bpfs\b.*vacc"),
    ("Toxin", r"botulinum|\bbotox\b|bocouture|azzalure|dysport|alluzience|letybo|relfydess|nuceiva|xeomin|\btoxins?\b"),
    ("Weight-loss medicine", r"wegovy|mounjaro|saxenda|ozempic|rybelsus|tirzepatide|semaglutide|liraglutide|orlistat|mysimba|foundayo|weight[- ]?loss"),
    ("PDO threads", r"\bpdo\b|\bthreads?\b|\bcogs?\b(?!nac)|silhouette soft|definisse|aptos|\bmint\b.*(lift|thread)|fishbone"),
    ("Fat dissolving", r"fat[- ]?dissolv|lipolys|lipolytic|aqualyx|lemon ?bottle|lipo ?lab|\bppc\b|deoxychol|desoface|desobody|alidya|celluerase|skinny bottle|pine bottle|kabelline|\blipo\b|body contour(ing)? (solution|injection)|aqualyx|cellulite injection|\bbelkyra|kybella"),
    ("Biostimulator", r"sculptra|radiesse|ellans[eé]|\bplla\b|poly[- ]?l[- ]?lactic|pdlla|calcium hydroxylapatite|\bcaha\b|harmonyca|aesplla|juvelook|lenisna|gouri|pllacell|aesthefill|lanluma|julaine|ecolla|linerase|collagen stimulat|biostimul"),
    ("Dermal filler", r"dermal fillers?|\bfillers?\b(?!.*(needle|cannula|pen\b|syringe filler|kit bag))|juv[eé]derm|teosyal|redensity|\brha\s?\d|restylane|belotero|stylage|revolax|saypha|perfectha|revanesse|neuramis|regenovue|\beptq\b|e\.?p\.?t\.?q|monalisa|kairax|hyacorp|nexfill|volifil|teofil|starfill|intraline|luxfill|bellast|lumifil|illuma|aessoa|hyalmass|genefill|desirial|revofil|lapiena|kysense|maili|skinfill|ouye|puri ?lips|aliaxin|croma|hyaluronic acid (gel|filler)"),
    ("Skin booster / polynucleotide / mesotherapy", r"skin ?boosters?|polynucleotide|\bpn[- ]?hpt|\bpdrn\b|profhilo|jalupro|sunekos|plinest|newest|nucleofill|rejuran|viscoderm|seventy ?hyal|ejal|lumi[- ]?(pro|pn|eyes)|vitaran|polyphil|dermaheal|plenhyage|karisma|hyaron|aquashine|sosum|stayve|cytocare|ameela|longevha|reversha|neofound|dermaren|pluryal|medisco|prostrolane|richesse|elaxen|repadern|ulti ?pro|purasomes|exosome|mesotherap|meso\b|\bnctf|biorevital|hydro ?booster|\bprp\b|prf\b|platelet"),
    ("Vitamin & IV therapy", r"pabrinex|vitamins? b\s?\+\s?c|vitamin b ?12|hydroxocobalamin|cyanocobalamin|neocytamen|glutathione|\bnad\+?|vitamin c (inj|ampoule|im|iv)|ascorbic acid (inj|amp)|\biv (drip|therapy|bag|infusion|vitamin)|biotin.*(inj|im|amp)|vitamin d3? (inj|ampoule)|colecalciferol inj|ergocalciferol inj|magnesium sulph?ate inj|thiamine inj|\binfusion\b(?! pump)"),
    ("Needles, cannulas & syringes", r"needles?\b|cannula|cannulae|syringes?\b|microlance|steriglide|\b\d{2}\s?g\b\s*x|\bluer\b|butterfly|venflon|pen needles|insulin syring|blunt tip|tsk\b|sterican|agani|unisharp|novofine|mekon|nanoneedle|nanocannula|micro ?cannula"),
    ("Clinic consumables & PPE", r"gloves?\b|swabs?\b|gauze|sharps|clinical waste|apron|gown|face ?mask(?!.*(sheet|hydrat|collagen|gold|led|cooling|calming|lift|serum))|face shield|couch roll|bed roll|tissue|dressing|plaster|tape\b|micropore|transpore|tegaderm|wipes?\b|disinfect|sanitis|sanitiz|antisept|alcohol (swab|wipe|gel)|chlorhex|hibi|clinell|clinisept|spatula|gallipot|kidney dish|tray\b|container|tourniquet|cotton (wool|pad|bud)|ice pack|cold pack|hot ?cold|first aid|spill kit|body fluid|bin\b|thermometer|ultrasound gel|hair net|mob cap|overshoe|sterile water|\bpads?\b(?!.*(peel|cleans))|lip wand|applicator"),
    ("Devices & equipment", r"machine|device|\blaser\b|hifu|\bled\b|radiofrequency|\brf\b|microneedling (pen|device|system)|dermapen|skinpen|\bpen\b(?!.*(needle|kwik|flextouch|epi|auto|insulin|inj|prefilled|pre-filled))|cartridges?|handpiece|hand piece|centrifuge|hydrafacial|cryo|lamp|magnifier|loupe|chair|couch\b|trolley|stool|fridge|refrigerator|steriliser|autoclave|scales?\b|tablet stand|spacer device|nebuli[sz]er|oximeter|blood pressure|glucose meter|dermaroller|derma roller|roller\b|microdermabrasion|ultrasonic|electroporation|plasma pen|jet ?peel|mesogun|meso gun|injector gun|vibrating|massager"),
    ("Beauty (nails, brows, lashes, PMU, makeup)", r"\bnail|polish|gel ?polish|builder gel|cuticle|manicure|pedicure|\bbrow|lash|lamination|tint\b|henna|microblad|\bpmu\b|permanent make|tattoo|pigment|eyeliner|lipstick|lip gloss|mascara|foundation\b(?!.*kit)|concealer|makeup|make-up|glitter|nail art|\bwax\b|waxing|tanning|spray tan|eyebrow|eyelash|lip liner|brush\b"),
    ("Supplements", r"supplement|capsules?\b(?=.*(daily|vitamin|collagen|biotin|omega|probiotic|hair|skin|nails))|gummies|collagen (drink|shot|powder|sachet|liquid)|liposomal|multivitamin|vitamin (d|c)\s?\d*\s?(iu|mg)?\s*(tablet|capsule|spray|drops|gummies)|omega|probiotic|nutrition|heliocare (oral|360 oral|capsule)|drink\b|sachets?\b(?!.*(serum|cream))|\bpowder\b(?=.*(drink|collagen|protein))"),
    ("Skincare, haircare & peels", r"\bpeels?\b|peeling|\btca\b|\bserum|cream\b|moisturi[sz]|cleanser|cleansing|toner\b|\bspf\b|sunscreen|sun cream|\bmask\b|masque|exfoliat|retinol|retinal|vitamin c (serum|cream)|hyaluronic (serum|cream)|eye cream|eye (gel|contour)|lotion|balm\b|micellar|essence\b|ampoules? (skin|face)|skincare|skin care|shampoo|conditioner|hair (loss|growth|care|serum|tonic)|scalp|body (wash|oil|cream)|face (wash|oil)|lip (care|balm|treatment|booster)|neostrata|heliocare|mesoestetic|obagi|zo skin|skinceuticals|is clinical|alastin|medik8|dermaceutic|\bpca skin|environ|murad|cosmedix|exuviance|dermalogica|image skincare|bioderma|la roche|avene|cerave|cetaphil|eucerin|biorepeel|prx|bienpeel|enerpeel|aftermed|pre ?procedure|post ?procedure (cream|balm|gel|kit)|recovery (cream|balm)"),
    ("Medicine - oral", r"tablets?\b|capsules?\b|caplets?|oral (solution|suspension|spray)|\bsyrup\b|lozenge|dispersible|orodispersible|effervescent|soluble tablets?|\bmg\b.*\bx\s?\d+\s*$"),
    ("Medicine - topical / eye / other", r"\bcream\b(?=.*(\d+\s?%|\d+\s?g\b|bp\b|hydrocortisone|clotrimazole|fucidin|aciclovir|emla|lmx|ametop|numbing|anaesthetic|pom))|ointment|eye drops|ear drops|nasal spray|inhaler|accuhaler|evohaler|pessar|suppositor|vaginal|patch(es)?\b(?=.*(mg|mcg|nicotine|hrt|estradiol))|\bgel\b(?=.*\d+\s?%)|numbing cream|emla|lmx|ametop|minims|eye ointment|shampoo(?=.*(ketocon|nizoral|coal tar))|scalp application|cutaneous|transdermal|foam\b(?=.*%)"),
    ("Medicine - injectable / anaesthetic / emergency", r"lidocaine|lignocaine|xylocaine|articaine|septanest|mepivacaine|scandonest|bupivacaine|marcain|citanest|prilocaine|adrenaline|epipen|jext|emerade|epinephrine|hyaluronidase|hyalase|liporase|hylenex|disolvidase|chlorphenamine inj|hydrocortisone (inj|sodium)|solu-cortef|kenalog|triamcinolone|depo-?medrone|methylpred|dexamethasone inj|ampoules?\b|\bamps?\b|\bvials?\b|injection|for injection|solution for inj|\binj\b|sodium chloride|saline|water for injection|bacteriostatic|glucagon|glucagen|naloxone|atropine|salbutamol neb|ondansetron inj|testosterone|nebido|sustanon|ferinject|venofer|heparin|enoxaparin|clexane|\bpfs\b|pre-?filled pen|kwikpen|flextouch"),
]

# supplier-category vocabulary -> category (supplier categories are the strongest signal when present)
SUP = [
    ("Toxin", r"toxin|botulinum|anti[- ]?wrinkle inj"),
    ("Dermal filler", r"dermal fill|\bfillers?\b|lip fill"),
    ("Skin booster / polynucleotide / mesotherapy", r"skin ?booster|polynucleotide|mesotherap|exosome|biorevital|profhilo|\bprp\b"),
    ("Biostimulator", r"biostimul|collagen stimul|plla|sculptra|radiesse"),
    ("Fat dissolving", r"fat dissolv|lipolys|fat dissolvers|body contour"),
    ("PDO threads", r"thread"),
    ("Vitamin & IV therapy", r"vitamin inj|iv therap|iv drip|vitamins? & iv|vitamin shots|\biv\b"),
    ("Weight-loss medicine", r"weight[- ]?(loss|management)"),
    ("Vaccine", r"vaccin|travel health"),
    ("Needles, cannulas & syringes", r"needle|cannula|syringe"),
    ("Clinic consumables & PPE", r"consumable|clinic supplies|clinical supplies|\bppe\b|gloves|infection control|disinfect|sharps|first aid|dressings|wound care|surgical"),
    ("Devices & equipment", r"equipment|device|machine|microneedling|furniture|laser|electrical"),
    ("Beauty (nails, brows, lashes, PMU, makeup)", r"\bnails?\b|brows?\b|lash|pmu|permanent make|tattoo|make ?up|beauty salon"),
    ("Supplements", r"supplement|nutrition|nutraceutical|wellbeing|wellness"),
    ("Skincare, haircare & peels", r"skin ?care|skincare|peels?|cosmeceutical|hair ?care|haircare|sun ?care|cleans|serum|moistur|masks?\b|aftercare|post[- ]treatment care|retail"),
    ("Medicine - injectable / anaesthetic / emergency", r"anaesthetic|anesthetic|emergency|hyaluronidase|diluent|injectable medic|\bampoules?\b|solutions"),
    ("Medicine - oral", r"tablets|capsules|oral"),
    ("Medicine - topical / eye / other", r"topical|eye care|dermatolog|skin conditions|creams & ointments"),
    ("Medicine - unspecified", r"pharmaceutical|pharmacy|medicines?\b|prescription|\bpom\b|antibiotic|general pharmacy|pharmacy products"),
    ("Training, services & marketing", r"training|course|marketing|merchandise|academy"),
]
MED_FORMS = ("Medicine - oral", "Medicine - topical / eye / other", "Medicine - injectable / anaesthetic / emergency")


def votes(text, rules):
    out = []
    for cat, rx in rules:
        m = re.search(rx, text or "", re.I)
        if m:
            out.append((cat, m.group(0)))
    return out


def classify(row, page, brand_cat, override):
    if override:
        return override["category"], "high", f"manual: {override.get('note', '')}", []
    if "medicines.org.uk" in row["url"]:
        return "Not a product", "high", "url is an emc medicine page, not a supplier product page", []
    score = collections.Counter()
    ev = []

    def add(src, w, hits, limit=1):
        for cat, kw in hits[:limit]:
            score[cat] += w
            ev.append(f"{src}:{cat.split(' ')[0]}('{kw}')")

    pt = (page or {}).get("page_title") or ""
    if re.search(r"pharmacy$|^shop$", pt.strip(), re.I):
        pt = ""
    sc = (page or {}).get("supplier_category") or ""
    desc = " ".join(x for x in [(page or {}).get("short_description") or "", (page or {}).get("description") or ""] if x)[:1500]
    # S1 supplier category: all matches count (supplier may list several), strongest weight
    s1 = votes(sc, SUP)
    add("supplier_cat", 3, s1, limit=2)
    # S2 page title: first matching rule (rules are ordered from most to least specific)
    s2 = votes(pt, R)
    add("page_title", 3, s2)
    # S3 brand
    if brand_cat:
        score[brand_cat] += 2
        ev.append(f"brand:{brand_cat.split(' ')[0]}")
    # S4 legal fields
    if re.search(r"Legal Category:\s*(POM|P)\b|Medicine Type\s+Prescription|POM:\s*Yes", sc + " " + desc):
        score["Medicine - unspecified"] += 2
        ev.append("legal:POM/P")
    if re.search(r"Legal Category:\s*(MD)\b|Filler:\s*Yes", sc):
        score["Dermal filler" if "Filler: Yes" in sc else "Devices & equipment"] += 1 if "Filler: Yes" not in sc else 2
    if "Toxin: Yes" in sc:
        score["Toxin"] += 3
    # S5 description
    add("description", 1, votes(desc, R))
    # S6 listing title (weak unless nothing else)
    s6 = votes(row["title"], R)
    add("listing_title", 2 if not (s1 or s2) else 1, s6)
    if not score:
        return "", "low", "no signal (no page and no recognisable words)", []
    # resolve 'Medicine - unspecified' into a medicine form when a form signal exists
    if score.get("Medicine - unspecified"):
        forms = [c for c in MED_FORMS if score.get(c)]
        u = score.pop("Medicine - unspecified")
        if forms:
            score[max(forms, key=lambda c: score[c])] += u
        elif not any(score.get(c) for c in CATS):
            score["Medicine - topical / eye / other"] += 0  # keep empty; handled below
            return "Medicine (form not stated)", "low", "; ".join(ev), []
        else:
            score["Medicine - injectable / anaesthetic / emergency"] += 0
    ranked = score.most_common()
    top, s_top = ranked[0]
    s_2 = ranked[1][1] if len(ranked) > 1 else 0
    srcs = {e.split(":")[0] for e in ev if top.split(" ")[0] in e}
    strong = srcs & {"supplier_cat", "page_title", "brand", "legal"}
    if len(srcs) >= 2 and strong and s_top - s_2 >= 2:
        conf = "high"
    elif strong and s_top - s_2 >= 1:
        conf = "medium"
    else:
        conf = "low"
    alts = [c for c, s in ranked[1:3] if s >= s_top - 1]
    return top, conf, "; ".join(ev), alts


def main():
    rows = list(csv.DictReader(open(ROOT / "products_input.csv", encoding="utf-8-sig")))
    pages = {}
    for l in open(ROOT / "pages.jsonl", encoding="utf-8"):
        p = json.loads(l)
        pages[p["id"]] = p
    errs = {e["id"]: e["error"] for e in csv.DictReader(open(ROOT / "scrape_errors.csv", encoding="utf-8"))}
    brand_map = {"toxin": "Toxin", "filler": "Dermal filler", "skin booster": "Skin booster / polynucleotide / mesotherapy",
                 "polynucleotide": "Skin booster / polynucleotide / mesotherapy", "biostimulator": "Biostimulator"}
    brands = [(b["regex"], brand_map[b["category"]]) for b in csv.DictReader(open(ROOT / "data" / "brands_scope.csv", encoding="utf-8"))]
    ov_path = ROOT / "data" / "category_overrides.csv"
    overrides = {o["id"]: o for o in csv.DictReader(open(ov_path, encoding="utf-8"))} if ov_path.exists() else {}
    out = []
    for r in rows:
        p = pages.get(r["id"])
        name = ((p or {}).get("page_title") or "") + " " + r["title"]
        bc = next((c for rx, c in brands if re.search(rx, name, re.I)), "")
        cat, conf, ev, alts = classify(r, p, bc, overrides.get(r["id"]))
        out.append({"id": r["id"], "supplier": r["supplier"], "title": r["title"], "url": r["url"],
                    "page_title": (p or {}).get("page_title", ""), "supplier_category": (p or {}).get("supplier_category", ""),
                    "category": cat or "Unclassified", "confidence": conf, "alternatives": " / ".join(alts),
                    "page_status": "read" if p else f"not available: {errs.get(r['id'], 'not scraped')}",
                    "evidence": ev})
    cols = list(out[0].keys())
    with open(ROOT / "output" / "all_products_categorised.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    rev = [o for o in out if o["confidence"] == "low" or o["category"] in ("Unclassified", "Medicine (form not stated)")]
    with open(ROOT / "output" / "category_review.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rev)
    c = collections.Counter(o["category"] for o in out)
    k = collections.Counter(o["confidence"] for o in out)
    print("rows", len(out), "| confidence", dict(k), "| review", len(rev), "| pages read", sum(o["page_status"] == "read" for o in out))
    for cat, n in c.most_common():
        print(f"  {n:5d} {cat}")


if __name__ == "__main__":
    main()
