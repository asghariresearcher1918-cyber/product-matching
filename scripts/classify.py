"""Step 3 - classify each row from page + reference + image observations.

Inputs : products_input.csv, pages.jsonl, scrape_errors.csv, output/reference_catalog.csv,
         data/image_observations.csv
Outputs: output/products_grouped.csv, output/review_queue.csv, output/run_report.md

Usage: python -I scripts/classify.py [--ids pilot_ids.txt]

Principles (PROMPT.md): the title alone never decides route/strength/volume/pack/form;
status words go to their own columns; conflicts -> needs_human_review, never a guess.
"""
import argparse
import collections
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

COLS = ["id", "supplier", "title", "url", "family_id", "family_name", "variant_id", "variant_label",
        "pack_id", "pack_label", "form", "route", "rx", "vat_note", "stock_note", "is_bundle",
        "equivalent_to", "image_url", "evidence", "confidence", "needs_human_review", "review_reason"]

# ---------------------------------------------------------------- helpers
def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def first(*vals):
    for v in vals:
        if v:
            return v
    return ""


# rule 3: status/admin words -> separate columns, stripped from the name
STATUS = [
    ("rx", r"\bprescription only\b|\bprescription item\b|\bon prescription\b|\(?prescription required\)?|\bPOM\b|\bRx Only\b|\bprescription\b"),
    ("vat", r"stock item vat payable|prescription item (?:zero|no) vat|zero vat|no vat|vat payable"),
    ("stock", r"out of stock|sold out|currently unavailable|limited stock|available on request|discontinued|clearance|\(?exp(?:iry)?\.?\s*[\d./]+\)?"),
    ("other", r"training required|appropriate training (?:recommended|required)|chilled|\bnew\b|please call as only available on request"),
]


def statuses(*texts):
    out = collections.defaultdict(list)
    for t in texts:
        for k, pat in STATUS:
            for m in re.finditer(pat, t or "", re.I):
                v = m.group(0).strip(" ()").lower()
                if v not in out[k]:
                    out[k].append(v)
    return out


# rule 2: route equivalences. Case-sensitive abbreviations, case-insensitive words.
IV_RE = re.compile(r"(?i:\bintravenous(?:ly)?\b|into a vein|drip infusion|\bi\.v\.)|\bI\.?/?V\b(?![\w-])")
IM_RE = re.compile(r"(?i:\bintramuscular(?:ly)?\b|into a muscle|\bi\.m\.)|\bI\.?/?M\b(?![\w-])")
NEUTRAL_ROUTE = re.compile(r"(?i)intramuscular or intravenous|intravenous or intramuscular|\(intramuscular or intravenous\)|vitamins\s*&\s*iv\b")


def routes_in(text):
    t = NEUTRAL_ROUTE.sub(" ", text or "")
    r = set()
    if IV_RE.search(t):
        r.add("IV")
    if IM_RE.search(t):
        r.add("IM")
    return r


def route_quotes(text, n=2):
    t = NEUTRAL_ROUTE.sub(" ", text or "")
    q = []
    for rx, lab in ((IM_RE, "IM"), (IV_RE, "IV")):
        for m in list(rx.finditer(t))[:n]:
            q.append(f"{lab}: \"...{t[max(0, m.start() - 50):m.end() + 40].strip()}...\"")
    return q


# ---------------------------------------------------------------- families
FAMILIES = [  # (family_id, regex over page title / input title / brand attr, type)
    ("F-VITBC", r"pabrinex|vitamins?\s*b\s*(?:\+|&|and)\s*c|vitamin c\s*(?:&|and)?\s*b\b|vitamin c\W+im\b", "vitbc"),
    ("F-BOTOX", r"\bbotox\b", "toxin"),
    ("F-BOCOUTURE", r"bocouture", "toxin"),
    ("F-AZZALURE", r"azzalure", "toxin"),
    ("F-JUVEDERM-ULTRA", r"juv[eé]derm.*ultra", "filler"),
    ("F-TEOSYAL", r"teosyal|redensity", "filler"),
    ("F-PROFHILO", r"profhilo", "booster"),
    ("F-WEGOVY-TAB", r"wegovy.*tablet", "oral"),
    ("F-ACICLOVIR-200", r"aciclovir.*200\s*mg|aciclovir 200", "oral"),
    ("F-TSK-STERIGLIDE", r"steriglide", "device"),
    ("F-BD-MICROLANCE3", r"microlance", "device"),
]

FAMILY_NAMES = {
    "F-PABRINEX": "Pabrinex (Vitamins B & C high potency)", "F-VITBC-ASPIRE": "Vitamin B and C IV High Potency (Aspire / Vitenta)",
    "F-VITBC-DEMO": "Vitamins B+C IV High Potency (DEMO S.A. pack)", "F-VITBC-UNRESOLVED": "Vitamins B+C IV (licence holder unresolved)",
    "F-BOTOX": "BOTOX", "F-BOCOUTURE": "BOCOUTURE", "F-AZZALURE": "Azzalure", "F-JUVEDERM-ULTRA": "Juvederm Ultra",
    "F-TEOSYAL": "Teosyal", "F-PROFHILO": "Profhilo", "F-WEGOVY-TAB": "Wegovy tablets", "F-ACICLOVIR-200": "Aciclovir 200 mg oral",
    "F-TSK-STERIGLIDE": "TSK STERiGLIDE cannula", "F-BD-MICROLANCE3": "BD Microlance 3 needle",
}


def load_ref():
    ref = {}
    for r in csv.DictReader(open(OUT / "reference_catalog.csv", encoding="utf-8")):
        ref.setdefault(r["family_id"], []).append(r)
    return ref


def ref_status(ref, fam, key=None):
    rows = ref.get(fam, [])
    for r in rows:
        if key is None or key in r["variant_key"].split("|") or r["variant_key"] == key:
            return r["reference_status"], r["source_urls"].split(" ; ")[0]
    return ("not_found", "") if not rows else (rows[0]["reference_status"], rows[0]["source_urls"].split(" ; ")[0])


# ---------------------------------------------------------------- pack parsing
def num(s):
    return float(s.replace(",", "."))


def fmt(x):
    return ("%g" % x)


def parse_count_volume(t):
    """'2 x 1ml', '2x0.55ml', '1 × 2 ml', '(1x1ml)' -> (count, ml)"""
    m = re.search(r"(\d+)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*ml", t, re.I)
    if m:
        return int(m.group(1)), num(m.group(2))
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*ml\s*[x×]\s*(\d+)\b", t, re.I)
    if m:
        return int(m.group(2)), num(m.group(1))
    return None, None


# ---------------------------------------------------------------- row classification
def page_text(p):
    desc = " ".join(x for x in [p.get("short_description", ""), p.get("description", "")] if x)
    attrs = " ".join(f"{k}: {v}" for k, v in (p.get("attributes") or {}).items())
    main = p.get("main_text", "")[:3000]
    body = desc if len(desc) >= 200 else (desc + " " + main)
    return f"{body} {attrs}"


def classify(row, p, ref, img):
    title = row["title"]
    pt = p.get("page_title") or ""
    text = page_text(p)
    # status words: only from titles and the stock field (page boilerplate such as "New here?" or
    # "Directions: available on request" must not leak in); rx also from explicit legal-category fields
    st = statuses(title, pt, p.get("stock_text", ""))
    legal = re.search(r"Legal Category:\s*(POM|P|GSL)\b|Medicine Type\s+(Prescription)|\bPOM\b", text + " " + p.get("main_text", "")[:1500])
    if legal and not st["rx"]:
        st["rx"].append((legal.group(1) or legal.group(2) or "POM").lower())
    res = {c: "" for c in COLS}
    res.update(id=row["id"], supplier=row["supplier"], title=title, url=row["url"], image_url=p.get("image_url", ""))
    res["rx"] = "; ".join(st["rx"])
    res["vat_note"] = "; ".join(st["vat"])
    res["stock_note"] = "; ".join(st["stock"] + st["other"])
    reasons, evidence = [], []
    name_src = f"{pt} | {title} | {(p.get('attributes') or {}).get('Brand', '')}"
    fam, ftype = None, None
    for fid, rx, ty in FAMILIES:
        if re.search(rx, name_src, re.I):
            fam, ftype = fid, ty
            break
    res["is_bundle"] = "true" if re.search(r"\bkit\b|bundle|\s\+\s(?!lidocaine)|duodecuple|triple pack", pt + " " + title, re.I) and ftype != "filler" else "false"
    io = img or {}
    if io.get("note"):
        evidence.append(f"image: {io['image_product']} / {io.get('image_pack', '')} ({io.get('image_mfr', '')}) - {io['note']}")
    elif io:
        evidence.append(f"image: {io['image_product']} / {io.get('image_pack', '')} ({io.get('image_mfr', '')})")

    if fam is None:
        res.update(confidence="uncertain", needs_human_review="true", review_reason="no family rule matched")
        res["evidence"] = " | ".join(evidence)
        return res

    variant, pack, form, route = "", "", "", ""
    equivalent = ""
    rstat, rurl = ref_status(ref, fam)

    # ---------------- Pabrinex / Vitamins B+C ----------------
    if ftype == "vitbc":
        title_r, pt_r, text_r = routes_in(title), routes_in(pt), routes_in(text)
        img_r = {io["image_route"]} if io.get("image_route") in ("IV", "IM") else set()
        srcs = {"input title": title_r, "page title": pt_r, "page text": text_r, "image": img_r}
        page_side = pt_r | text_r | img_r
        allr = title_r | page_side
        evidence += route_quotes(text)[:2]
        # which licence / brand?
        brand_txt = (pt + " " + title + " " + text).lower()
        says_pabrinex = "pabrinex" in brand_txt
        links_aspire = "101125" in text
        img_mfr = (io.get("image_mfr") or "").lower()
        if "demo" in img_mfr:
            fam = "F-VITBC-DEMO"
            if says_pabrinex:
                reasons.append("page says Pabrinex but image shows a DEMO S.A. 'Vitamins B+C' pack (not Pabrinex, not on emc)")
            if links_aspire:
                reasons.append("page links emc 101125 (Aspire, made by Alfasigma) but image shows a DEMO S.A. pack")
            equivalent = "F-PABRINEX/IV (same composition claimed; not verified)"
        elif img_mfr in ("kyowa kirin", "archimedes") or says_pabrinex:
            fam = "F-PABRINEX"
        elif links_aspire:
            fam = "F-VITBC-ASPIRE"
            equivalent = "F-PABRINEX/IV"
        else:
            fam = "F-VITBC-UNRESOLVED"
            reasons.append("generic 'Vitamins B+C' name, page gives no licence holder/brand and no image - cannot tell Pabrinex (Grünenthal) from Vitenta (Aspire) or an import")
        # route
        if len(allr) > 1:
            parts = ", ".join(f"{k}={'/'.join(sorted(v))}" for k, v in srcs.items() if v)
            reasons.append(f"route conflict ({parts})")
            route = "conflict"
        elif not page_side and title_r:
            route = next(iter(title_r))
            reasons.append(f"route {route} appears only in the title; page text and image give no route (rule: never decide route from title alone)")
        elif not allr:
            reasons.append("no route stated anywhere on page")
        else:
            route = next(iter(allr))
        # composition check against SmPC (no B5 / B12 in Pabrinex or Vitenta)
        if re.search(r"\bB5\b|\bB12\b|cyanocobalamin|pantothen", text):
            reasons.append("page lists B5/B12, which are not in the UK SmPC composition (thiamine, riboflavin, pyridoxine, ascorbic acid, nicotinamide, glucose)")
        # ampoule volumes / pack
        vols = set(re.findall(r"(\d+)\s?ml", (pt + " " + text + " " + io.get("image_pack", "")).lower()))
        im_sig = "2" in vols and "5" in vols
        if route == "IV" and im_sig and "ampoule" in text.lower() and re.search(r"2\s?ml ampoule", text, re.I):
            reasons.append("IV listing but page describes 2 ml No.2 ampoules (IM presentation)")
        mpairs = re.search(r"(\d+)\s*(?:x\s*)?(?:pairs|dual)\b|pack of (\d+)|(\d+)\s*x\s*2\b|size:\s*(\d+)\s*(?:x\s*5\s?ml|pairs)", (pt + " " + text + " " + title), re.I)
        pairs = next((g for g in (mpairs.groups() if mpairs else []) if g), None)
        if re.search(r"single ampoule", pt + " " + title, re.I):
            ml = re.search(r"(\d+)\s?ml single ampoule", pt + " " + title, re.I)
            pack = f"1 single ampoule {ml.group(1) + ' ml' if ml else ''}".strip()
            reasons.append("sold as a single ampoule (only one of the No.1/No.2 pair) - not a UK presentation" +
                           ("; image shows a full 10-pair box" if "10 pairs" in io.get("image_pack", "") else ""))
        elif pairs:
            unit = "(5 ml + 2 ml)" if route == "IM" else "(5 ml + 5 ml)" if route == "IV" else "(volumes unclear)"
            pack = f"{pairs} pairs {unit}"
            if route == "IV" and pairs not in ("6", "10"):
                reasons.append(f"{pairs} pairs is not an emc pack size (6 or 10)")
        elif io.get("image_pack"):
            pack = f"{io['image_pack']} (from image only)"
            reasons.append("pack size only visible in the image")
        else:
            reasons.append("pack size not stated")
        if fam == "F-PABRINEX" and route == "IM":
            rstat, rurl = ref_status(ref, "F-PABRINEX", "IM")
            reasons.append("Pabrinex IM has no current emc SmPC (reference not_found; discontinuation unverified)")
        elif fam == "F-PABRINEX":
            rstat, rurl = ref_status(ref, "F-PABRINEX", "IV")
        else:
            rstat, rurl = ref_status(ref, fam)
        form = {"IV": "concentrate for solution for infusion (ampoules)", "IM": "solution for injection (ampoules)"}.get(route, "ampoules")
        variant = f"{route or 'route?'} / B+C high potency / UK" if fam != "F-VITBC-DEMO" else f"{route or 'route?'} / B+C high potency / non-UK pack (DEMO S.A.)"
        if fam == "F-PABRINEX" and io.get("note") and "generic name" in io["note"]:
            evidence.append("generic title, Pabrinex pack in image")

    # ---------------- Toxins ----------------
    elif ftype == "toxin":
        src = pt + " " + text[:600]
        if re.search(r"syringe", pt + " " + title, re.I):
            reasons.append("listing is syringes, not the toxin itself (accessory?)")
            res["is_bundle"] = "true"
        m = re.search(r"(\d+)\s*(?:allergan\s*)?(?:u|iu|units?|speywood units?)\b", pt, re.I) or re.search(r"(\d+)\s*(?:allergan\s*)?(?:u|iu|units?|speywood units?)\b", src, re.I)
        units = m.group(1) if m else ""
        if not units:
            reasons.append("strength (units) not on page")
        unit_name = {"F-BOTOX": "Allergan Units", "F-AZZALURE": "Speywood units", "F-BOCOUTURE": "units"}[fam]
        variant = f"{units} {unit_name}" if units else "strength?"
        valid = {"F-BOTOX": {"50", "100", "200"}, "F-BOCOUTURE": {"50", "100"}, "F-AZZALURE": {"125"}}[fam]
        if units and units not in valid:
            reasons.append(f"{units} units is not a UK strength for {fam}")
        n = None
        if re.search(r"dual|double|2\s*x\s*\d+\s*u|x\s*2\s*vials|\b2\s*vials|2x\d+u|size:\s*2\s*x", pt + " " + text[:400] + " " + title, re.I):
            n = 2
        elif re.search(r"single|1\s*x\s*vial|x\s*1\s*vial|size:\s*1\s*x|\(1 x|\b1\s*x\s*\d+\s*(?:u|iu|units?)\b", pt + " " + text[:400] + " " + title, re.I):
            n = 1
        if n is None and io.get("image_pack"):
            n = 2 if io["image_pack"].startswith("2") else 1
            reasons.append("vial count only from image")
        pack = f"{n} vial{'s' if n and n > 1 else ''}" if n else "vial count not stated"
        if n is None:
            reasons.append("vial count not stated on page")
        form, route = "powder for solution for injection (vial)", "IM"
        rstat, rurl = ref_status(ref, fam)
        if "101125" in text or re.search(r"medicines\.org\.uk/emc/product/\d+", text):
            evidence.append("page links emc: " + ", ".join(sorted(set(re.findall(r"emc/product/(\d+)", text)))))

    # ---------------- Fillers / boosters ----------------
    elif ftype in ("filler", "booster"):
        src = f"{pt} | {title}"
        if fam == "F-JUVEDERM-ULTRA":
            m = re.search(r"ultra\s*(smile|\d)", src, re.I)
            model = f"Ultra {m.group(1).title()}" if m else "Ultra ?"
        elif fam == "F-TEOSYAL":
            m = re.search(r"rha\s*(\d|kiss)|redensity\s*(ii|i|1|2)\b", src, re.I)
            if m and m.group(1):
                model = f"RHA {m.group(1).title()}"
            elif m:
                model = "Redensity " + {"i": "1", "ii": "2"}.get(m.group(2).lower(), m.group(2))
            else:
                model = "model?"
            if re.search(r"puresense\s*rha|rha.*puresense", src, re.I):
                reasons.append("title mixes product lines 'PureSense' and 'RHA'")
        else:
            model = "Structura" if re.search(r"structura", src, re.I) else ("H+L" if re.search(r"profhilo(?!.*(body|structura))", src, re.I) else "?")
            if re.search(r"body", src, re.I):
                model = "Body"
        lido_txt = re.search(r"lidocaine|\blido\b", pt + " " + text[:2500], re.I)
        lido = "lidocaine" if lido_txt or "lidocaine" in (io.get("image_pack", "")) else ("no lidocaine" if ftype == "booster" else "lidocaine not stated")
        if lido == "lidocaine not stated":
            reasons.append("lidocaine not stated on page - grouped with lidocaine version only provisionally")
        market = ""
        if ftype == "booster":
            holo = re.search(r"hologram", pt + " " + title + " " + text[:800], re.I) or "hologram" in io.get("note", "").lower() and "no " not in io.get("note", "").lower()[:3]
            reasons.append("hologram box: " + ("yes" if holo else "not stated") + " (kept in same variant pending owner decision)")
        variant = f"{model} / {lido}{market}"
        # pack
        size = re.search(r"Size:\s*([^A-Z]{1,20})", text)
        c, v = parse_count_volume(pt)
        if c is None:
            c, v = parse_count_volume(size.group(1) if size else "")
        if c is None:
            c2, v2 = parse_count_volume(title)
            if c2:
                reasons.append("syringe count/volume only from title")
                c, v = c2, v2
        if c is None and re.search(r"single", pt + " " + title, re.I):
            c = 1
        if c is None and size:
            m = re.match(r"\s*(\d+)\s*[x×]?\s*(\d+(?:[.,]\d+)?)?", size.group(1))
            if m:
                c = int(m.group(1))
        pack = f"{c} x {fmt(v) + ' ml' if v else '? ml'} syringe" if c else "pack not stated"
        if not c:
            reasons.append("syringe count/volume not stated on page")
        form, route = "pre-filled syringe (HA gel)", "intradermal/subcutaneous"
        rstat, rurl = ref_status(ref, fam)

    # ---------------- Oral ----------------
    elif ftype == "oral":
        src = pt + " " + text[:1200]
        m = re.search(r"(\d+(?:\.\d+)?)\s*mg", pt) or re.search(r"(\d+(?:\.\d+)?)\s*mg", title)
        strength = m.group(1) + " mg" if m else "strength?"
        disp_page = bool(re.search(r"dispersible", pt + " " + (p.get("description") or "")[:1500], re.I))
        disp_img = "dispersible" in io.get("image_product", "").lower()
        formv = "dispersible tablet" if (disp_page or disp_img) else "tablet"
        if fam == "F-ACICLOVIR-200" and disp_img and not disp_page:
            reasons.append("image shows DISPERSIBLE tablets but page/title say plain tablets")
        variant = f"{strength} / {formv} / oral"
        n = re.search(r"(?:pack of|x|\()\s*(\d+)\s*(?:tablets|\)|$)|(\d+)\s*tablets|pack\s*(\d+)", pt + " " + title + " " + text[:300], re.I)
        cnt = next((g for g in (n.groups() if n else []) if g), None)
        if not cnt and io.get("image_pack"):
            cnt = re.match(r"\d+", io["image_pack"]).group(0)
            reasons.append("tablet count only from image")
        pack = f"{cnt} tablets" if cnt else "count not stated"
        form, route = formv, "oral"
        key = "dispersible" if formv.startswith("dispersible") else "tablet"
        rstat, rurl = ref_status(ref, fam, key if fam == "F-ACICLOVIR-200" else None)

    # ---------------- Devices ----------------
    elif ftype == "device":
        src = pt + " " + title
        g = re.search(r"(\d{2})\s?g\b", src, re.I)
        ln = re.search(r"(\d+)\s?mm", src, re.I) or re.search(r"x\s*0?\.5\"?\b|1/2\"", src)
        length = (ln.group(1) + " mm") if ln and ln.groups() and ln.group(1) else ("13 mm" if ln else "length?")
        if ln and not (ln.groups() and ln.group(1)):
            if ln:
                reasons.append("length given in inches only (0.5\" = 13 mm)") if "0.5" in src else None
        variant = f"{g.group(1) + 'G' if g else 'gauge?'} x {length}"
        c = None
        for s_ in (pt, title, text[:600]):
            s_ = re.sub(r"(?i)microlance[\s-]*3", "Microlance", s_)
            cnt = re.search(r"\(?\s*(?:pack|box of|size:\s*1\s*x)\s*(\d+)\s*\)?|\bx\s*(\d+)\s*$|(\d+)\s*(?:cannulas|needles)\b", s_, re.I)
            c = next((x for x in (cnt.groups() if cnt else []) if x), None)
            if c:
                break
        if not c and io.get("image_pack", "").isdigit():
            c = io["image_pack"]
            reasons.append("pack count only from image")
        pack = f"{c} per pack" if c else "pack count not stated"
        if not c:
            reasons.append("pack count not stated")
        form, route = ("cannula" if fam == "F-TSK-STERIGLIDE" else "hypodermic needle"), "n/a"
        rstat, rurl = ref_status(ref, fam)

    res["family_id"] = fam
    res["family_name"] = FAMILY_NAMES.get(fam, fam)
    res["variant_label"] = variant
    res["variant_id"] = f"{fam}/{slug(variant)}"
    res["pack_label"] = pack
    res["pack_id"] = f"{res['variant_id']}/{slug(pack)}"
    res["form"], res["route"], res["equivalent_to"] = form, route, equivalent
    q = (p.get("description") or p.get("main_text") or "")[:160].replace("\n", " ")
    evidence.insert(0, f"page: \"{q}\"")
    if rurl:
        evidence.append(f"ref({rstat}): {rurl}")
    res["evidence"] = " | ".join(evidence)
    SOFT = ("lidocaine not stated", "length given", "pack size only visible in the image", "vial count only from image",
            "tablet count only from image", "pack count only from image", "hologram box")
    hard = [r for r in reasons if not r.startswith(SOFT)]
    if hard:
        res["confidence"] = "uncertain"
    elif rstat == "found":
        res["confidence"] = "confirmed"
    else:
        res["confidence"] = "likely"
    soft = [r for r in reasons if r.startswith(SOFT) and not r.startswith(("length given", "hologram box"))]
    if res["confidence"] == "confirmed" and soft:
        res["confidence"] = "likely"
    res["needs_human_review"] = "true" if res["confidence"] == "uncertain" else "false"
    res["review_reason"] = "; ".join(reasons)
    return res


def family_level_checks(rows):
    """Cross-supplier consistency: same variant, different unit volume, no official reference."""
    by = collections.defaultdict(list)
    for r in rows:
        if r["pack_label"] and " x " in r["pack_label"] and "ml" in r["pack_label"]:
            by[r["variant_id"]].append(r)
    notes = []
    for vid, rs in by.items():
        vols = collections.Counter(re.search(r"x ([\d.?]+) ml", r["pack_label"]).group(1) for r in rs if re.search(r"x ([\d.?]+) ml", r["pack_label"]))
        if len(vols) > 1:
            notes.append(f"{vid}: suppliers disagree on syringe volume {dict(vols)} - no official presentation read")
            for r in rs:
                r["review_reason"] = "; ".join(x for x in [r["review_reason"], f"syringe volume differs across suppliers {dict(vols)}"] if x)
                if r["confidence"] != "uncertain":
                    r["confidence"], r["needs_human_review"] = "uncertain", "true"
    return notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(ROOT / "products_input.csv", encoding="utf-8-sig")))
    if a.ids:
        want = [l.strip() for l in open(ROOT / a.ids) if l.strip()]
        order = {k: i for i, k in enumerate(want)}
        rows = sorted([r for r in rows if r["id"] in order], key=lambda r: order[r["id"]])
    pages = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "pages.jsonl", encoding="utf-8")}
    errs = {e["id"]: e for e in csv.DictReader(open(ROOT / "scrape_errors.csv", encoding="utf-8"))}
    imgs = {r["id"]: r for r in csv.DictReader(open(ROOT / "data" / "image_observations.csv", encoding="utf-8"))}
    ref = load_ref()
    out = []
    for r in rows:
        if r["id"] in pages:
            out.append(classify(r, pages[r["id"]], ref, imgs.get(r["id"])))
        else:
            e = errs.get(r["id"], {}).get("error", "not scraped")
            st = statuses(r["title"])
            out.append({**{c: "" for c in COLS}, "id": r["id"], "supplier": r["supplier"], "title": r["title"], "url": r["url"],
                        "rx": "; ".join(st["rx"]), "vat_note": "; ".join(st["vat"]), "stock_note": "; ".join(st["stock"]),
                        "is_bundle": "", "confidence": "uncertain", "needs_human_review": "true",
                        "review_reason": f"page not available ({e}) - not classified (no guessing)"})
    xnotes = family_level_checks(out)
    OUT.mkdir(exist_ok=True)
    with open(OUT / "products_grouped.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)
    fam_sup = collections.defaultdict(set)
    for r in out:
        fam_sup[r["family_id"]].add(r["supplier"])
    rq = [r for r in out if r["needs_human_review"] == "true"]
    rq.sort(key=lambda r: (-len(fam_sup[r["family_id"]]), r["family_id"], r["id"]))
    with open(OUT / "review_queue.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["suppliers_in_family"] + COLS)
        w.writeheader()
        for r in rq:
            w.writerow({"suppliers_in_family": len(fam_sup[r["family_id"]]), **r})
    json.dump({"cross_supplier_notes": xnotes}, open(OUT / "_classify_notes.json", "w"), indent=1)
    c = collections.Counter(r["confidence"] for r in out)
    print(f"rows={len(out)} families={len({r['family_id'] for r in out if r['family_id']})} "
          f"variants={len({r['variant_id'] for r in out if r['variant_id']})} packs={len({r['pack_id'] for r in out if r['pack_id']})} {dict(c)}")


if __name__ == "__main__":
    main()
