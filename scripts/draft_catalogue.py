"""Draft MASTER CATALOGUE (product codes) built from our own supplier data, for the domain owner to approve.

Every supplier listing in scope is parsed from its PAGE (page title, size fields, description), never the input
title alone; listings that agree are grouped into one product code (brand + line + strength + lidocaine + pack).
Status of each code:
  official            pack matches an official presentation in catalogue/ (emc SmPC / manufacturer IFU)
  consensus           seen at >= 2 suppliers with the same line/strength/lidocaine/pack
  single_supplier     seen at one supplier only -> needs confirmation
  incomplete          line or pack size could not be read from the page -> needs completion
Output: output/master_catalogue_draft.xlsx  (+ csv copies in catalogue/draft/)
Usage: python -I scripts/draft_catalogue.py
"""
import collections
import csv
import json
import re
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
CAT = ROOT / "catalogue"

NON_PRODUCT = [
    ("marketing_or_accessory", r"poster|banner|leaflet|consultation form|ruler|mirror|headband|merchandise|post treatment guide|cooling pack|opener|brochure|display|stand\b"),
    ("training_or_service", r"\bcourse\b|training (package|bundle)|in-?clinic|webinar"),
    ("bundle", r"bundle|buy \d|\bget \d|combination|\bfree\b|mix and match|\+ ?\d+ ?x|\bkit\b(?!.*(body|lemon))"),
    ("non_injectable", r"cream|serum|cleanser|micellar|\bmask|peel|spf|sunscreen|supplement|drink|gummies|microneedl|\broller\b|pen tip|eyelash|lip balm|patch|haenkenium|figura|\bpura\b|nanosoft|pearls|spacer|gift|collection|aftercare|advice|heat ?cool|cooling|\bduo\b(?!.*(ultimate|syringe))|ice pack|cosmetic"),
]
STATUS_WORDS = r"prescription item|stock item|vat payable|zero vat|pay vat|no vat|on prescription|prescription only|\(?pom\)?|training (required|recommended)|appropriate|proof of|out of stock|available on request|limited stock|clone|uk official|official|ce marked|new\b|\(exp[^)]*\)|exp\.?\s?[\d./]+"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def num(s):
    return float(s.replace(",", "."))


def fmt(x):
    return ("%g" % x) if x is not None else "?"


def parse_pack(*texts):
    """-> (count, volume_ml, source_index) from the first text that states it."""
    for k, t in enumerate(texts):
        if not t:
            continue
        m = re.search(r"(\d+)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*ml\b", t, re.I)
        if m:
            return int(m.group(1)), num(m.group(2)), k
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*ml\s*[x×]\s*(\d+)\b", t, re.I)
        if m:
            return int(m.group(2)), num(m.group(1)), k
        m = re.search(r"(?:pack consists of|box contents|each box contains|contains)[:\s]*(\d+|one|two)\s*(?:x\s*)?(\d+(?:[.,]\d+)?)\s*ml", t, re.I)
        if m:
            c = {"one": 1, "two": 2}.get(m.group(1).lower(), None) or int(m.group(1))
            return c, num(m.group(2)), k
    return None, None, None


def parse_single_volume(t):
    m = re.search(r"\b(\d+(?:[.,]\d+)?)\s*ml\b", t or "", re.I)
    return num(m.group(1)) if m else None


def main():
    rows = list(csv.DictReader(open(ROOT / "data" / "scope_rows.csv", encoding="utf-8")))
    pages = {}
    for l in open(ROOT / "pages.jsonl", encoding="utf-8"):
        p = json.loads(l)
        pages[p["id"]] = p
    fams = list(csv.DictReader(open(CAT / "families.csv", encoding="utf-8")))
    vars_ = list(csv.DictReader(open(CAT / "variants.csv", encoding="utf-8")))
    pres = list(csv.DictReader(open(CAT / "presentations.csv", encoding="utf-8")))
    srcs = list(csv.DictReader(open(CAT / "sources.csv", encoding="utf-8")))
    errs = {e["id"]: e["error"] for e in csv.DictReader(open(ROOT / "scrape_errors.csv", encoding="utf-8"))}

    def brand_fams(brand):
        b = brand.split("/")[0].split("(")[0].strip().lower()
        return [f for f in fams if f["brand"].lower().startswith(b[:6]) or b.startswith(f["brand"].lower()[:6])]

    listings = []
    for r in rows:
        i = r["id"]
        L = {"id": i, "supplier": r["supplier"], "title": r["title"], "url": r["url"], "brand": r["brand"], "category": r["category"]}
        p = pages.get(i)
        if not p:
            listings.append(L | {"kind": "", "code": "", "flags": f"page not available: {errs.get(i, 'not scraped')}"})
            continue
        pt = p.get("page_title") or ""
        desc = " ".join(x for x in [p.get("short_description") or "", p.get("description") or ""] if x)
        main = (p.get("main_text") or "")[:2500]
        body = desc if len(desc) > 200 else (desc + " " + main)
        name = pt if len(pt) > 3 and not re.search(r"pharmacy$", pt, re.I) else r["title"]
        flags = []
        kind = "product"
        for k, rx in NON_PRODUCT:
            if re.search(rx, name, re.I):
                kind = k
                break
        L["kind"] = kind
        L["page_title"] = name
        # ---- line
        fl = brand_fams(r["brand"])
        real = [f for f in fl if f["line"] and not f["line"].startswith("(")]
        line, fid = "", ""
        if r["category"] == "toxin":
            tf = [f for f in fl if not f["line"]]
            if tf:
                line, fid = tf[0]["brand"], tf[0]["family_id"]
        for src in ((name, r["title"]) if not line else ()):
            for f in sorted(real, key=lambda f: -len(f["aliases"])):
                if re.search(f["aliases"], src, re.I):
                    line, fid = f["line"], f["family_id"]
                    break
            if line:
                break
        if not line:
            if real:
                flags.append("line not recognised (check name)")
            # brands without defined lines: derive a provisional line from the page name
            t = re.sub(r"\(.*?\)|\[.*?\]", " ", name.lower())
            t = re.sub(STATUS_WORDS, " ", t)
            t = re.sub(r"\d+\s*[x×]\s*[\d.,]+\s*ml|[\d.,]+\s*ml|\bx\s?\d+|\d+\s?x\b|with lidocaine|lidocaine|lido\b|\binj\b|\.|-|–|single|syringe[s]?|vials?|dermal filler|skin booster|filler", " ", t)
            words = [w for w in re.findall(r"[a-z0-9+]+", t) if w not in r["brand"].lower().replace("/", " ").split()]
            line = " ".join(words[:3]).title() or "(base)"
            fid = "F-" + slug(r["brand"].split("/")[0].split("(")[0] + " " + line)
            L["line_status"] = "provisional (derived from page names)"
        else:
            L["line_status"] = "catalogue"
        L["line"], L["family_id"] = line, fid
        # ---- strength (toxins and dosed products)
        strength = ""
        if r["category"] == "toxin":
            m = re.search(r"(\d+)\s*(?:allergan\s*)?(?:u|iu|units?|speywood)\b", name, re.I) or re.search(r"(\d+)\s*(?:allergan\s*)?(?:u|iu|units?|speywood)\b", body[:600], re.I)
            strength = (m.group(1) + " U") if m else ""
            if not strength:
                flags.append("strength not on page")
        L["strength"] = strength
        # ---- lidocaine
        lt = name + " " + body[:3000]
        if re.search(r"without lido|non[- ]?lido|no lidocaine|lidocaine[- ]free|\bplain\b", lt, re.I):
            lido = "no"
        elif re.search(r"lidocaine|\blido\b|lignocaine|mepivacaine", lt, re.I):
            lido = "yes"
        else:
            lido = "not stated" if r["category"] != "toxin" else "n/a"
        L["lidocaine"] = lido
        # ---- market (variant only where it matters: Korean brands sold in UK and Korean versions)
        market = ""
        if re.search(r"korea|korean", lt, re.I):
            market = "KR"
        elif re.search(r"\buk\b|ce[- ]?marked|official|fox ?group|supplied for uk", lt, re.I):
            market = "UK/CE"
        L["market"] = market
        # ---- pack
        size = re.search(r"Size:\s*([^A-Z]{1,25})", body)
        c, v, k = parse_pack(name, size.group(1) if size else "", body[:2000], r["title"])
        src_name = ["page title", "size field", "page text", "listing title only"][k] if k is not None else ""
        if c is None:
            if r["category"] == "toxin":
                if re.search(r"dual|double|twin|2\s*x\s*\d+\s*u|x\s*2\s*vials|\b2\s*vials|2x\d+u", name + " " + body[:400], re.I):
                    c, src_name = 2, "page"
                elif re.search(r"single|1\s*x\s*vial|\(1 x|\b1\s*x\s*\d+\s*(?:u|iu|units?)\b", name + " " + body[:400], re.I):
                    c, src_name = 1, "page"
            else:
                vol = parse_single_volume(name)
                if vol:
                    c, v, src_name = (1, vol, "page title (single unit assumed)")
        if v is not None and r["category"] not in ("toxin",) and v >= 5 and not re.search(r"body|vial|hyacorp|sculptra|aqualyx|10\s?ml|\b\d+\s?x\s?(5|8|10)\s?ml", name, re.I):
            flags.append(f"implausible syringe volume {fmt(v)} ml (decimal point lost?) - pack left blank")
            c, v, src_name = None, None, ""
        if src_name == "listing title only":
            flags.append("pack only in listing title (not on page)")
        L["count"], L["volume_ml"], L["pack_source"] = c, v, src_name
        unit = "vial" if r["category"] == "toxin" else "syringe/vial"
        L["unit"] = unit
        if kind == "product" and c is None:
            flags.append("pack size not on page")
        L["flags"] = "; ".join(flags)
        listings.append(L)

    # ---------------- group into product codes
    KR_BRANDS = ("Revolax", "Regenovue", "Hyaron", "Neuramis", "Dermaheal", "Aquashine", "Rejuran", "EPTQ", "Juvelook", "Gouri", "AestheFill", "Prostrolane")
    def vkey(L):
        return (L["family_id"], L["strength"], "yes" if L["lidocaine"] == "yes" else ("no" if L["lidocaine"] == "no" else "n/s"), L["market"] if L["brand"].startswith(("Revolax", "Regenovue", "Hyaron", "Neuramis", "Dermaheal", "Aquashine", "Rejuran", "EPTQ", "Juvelook", "Gouri", "AestheFill")) else "")

    prods = [L for L in listings if L.get("kind") == "product"]
    # lidocaine 'not stated' joins the family's lidocaine variant if every other listing of that family/pack states lidocaine
    by_fp = collections.defaultdict(set)
    for L in prods:
        if L["lidocaine"] in ("yes", "no"):
            by_fp[(L["family_id"], L["count"], L["volume_ml"])].add(L["lidocaine"])
    for L in prods:
        if L["lidocaine"] == "not stated":
            s = by_fp.get((L["family_id"], L["count"], L["volume_ml"]), set())
            if len(s) == 1:
                L["lidocaine_assumed"] = next(iter(s))
                L["flags"] = "; ".join(x for x in [L["flags"], f"lidocaine not stated on page - assumed '{next(iter(s))}' from other suppliers"] if x)
    # official presentations
    off = collections.defaultdict(list)
    for p in pres:
        if p["reference_status"] == "official":
            v = next(x for x in vars_ if x["variant_id"] == p["variant_id"])
            off[v["family_id"]].append(p)
    src_by_f = {s["family_id"]: s["url"] for s in srcs}

    codes = {}
    for L in prods:
        lido = L.get("lidocaine_assumed") or L["lidocaine"]
        lido_tag = {"yes": "L", "no": "NL"}.get(lido, "")
        vol = fmt(L["volume_ml"]) + "ml" if L["volume_ml"] else ""
        brand_s = slug(L["brand"].split("/")[0].split("(")[0])[:10].upper()
        market = L["market"] if L["brand"].startswith(KR_BRANDS) else ""
        L["market"] = market
        if not L["count"] or (L["category"] != "toxin" and not vol) or L["line"] == "(base)":
            # no pack size / no line on the page: not a product code; listed under 'Needs information'
            L["code"] = ""
            L["needs"] = "pack size" if L["line"] != "(base)" else "product line"
            continue
        pack = f"{L['count']}x{vol}" if vol else f"{L['count']}x"
        code = "-".join(x for x in [brand_s, "" if slug(L["line"]) == slug(L["brand"].split("/")[0].split("(")[0]) else slug(L["line"]).upper()[:14], L["strength"].replace(" ", ""), lido_tag, market.replace("/", ""), pack.upper()] if x)
        L["code"] = code
        c = codes.setdefault(code, {"code": code, "category": L["category"], "brand": L["brand"], "line": L["line"], "line_status": L["line_status"],
                                    "family_id": L["family_id"], "strength": L["strength"], "lidocaine": lido, "market": L["market"],
                                    "count": L["count"], "volume_ml": L["volume_ml"], "unit": L["unit"], "listings": [], "suppliers": set()})
        c["listings"].append(L)
        c["suppliers"].add(L["supplier"])
    for c in codes.values():
        ofp = off.get(c["family_id"], [])
        is_off = False
        if ofp:
            if c["category"] == "toxin":
                is_off = bool(c["strength"]) and c["count"] in (1, 2, 3, 6, 10)
            else:
                is_off = any(p["unit_volume_ml"] and c["volume_ml"] is not None and num(p["unit_volume_ml"]) == c["volume_ml"] and str(c["count"]) in p["units_per_pack"] for p in ofp)
        if is_off:
            st = "official"
        elif len(c["suppliers"]) >= 2:
            st = "consensus"
        else:
            st = "single_supplier"
        c["status"] = st
        c["source"] = src_by_f.get(c["family_id"], "") if st == "official" else ""
        if ofp and not is_off and st != "incomplete":
            c["note"] = "family has an official reference but this pack is not one of its official presentations (split pack, bundle or error?)"
        else:
            c["note"] = ""

    # ---------------- write CSVs
    out_dir = CAT / "draft"
    out_dir.mkdir(exist_ok=True)
    order = {"official": 0, "consensus": 1, "single_supplier": 2}
    clist = sorted(codes.values(), key=lambda c: (order[c["status"]], c["category"], c["brand"], c["line"], c["code"]))
    with open(out_dir / "master_products.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code", "status", "category", "brand", "line", "strength", "lidocaine", "market", "units_per_pack", "volume_ml", "suppliers", "listings", "source", "note"])
        for c in clist:
            w.writerow([c["code"], c["status"], c["category"], c["brand"], c["line"], c["strength"], c["lidocaine"], c["market"], c["count"], c["volume_ml"],
                        len(c["suppliers"]), len(c["listings"]), c["source"], c["note"]])
    with open(out_dir / "listing_to_code.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        cols = ["id", "supplier", "title", "url", "kind", "code", "brand", "line", "strength", "lidocaine", "market", "count", "volume_ml", "pack_source", "flags"]
        w.writerow(cols)
        for L in listings:
            w.writerow([L.get(k, "") for k in cols])

    # ---------------- Excel
    wb = Workbook()
    F = "Arial"
    hdr_font = Font(name=F, bold=True, color="FFFFFF")
    hdr_fill = PatternFill("solid", fgColor="2F4F6F")
    inp_fill = PatternFill("solid", fgColor="FFFF00")
    st_fill = {"official": "C6EFCE", "consensus": "DDEBF7", "single_supplier": "FFF2CC", "incomplete": "F8CBAD"}

    def sheet(ws, headers, widths):
        ws.append(headers)
        for j, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=j)
            cell.font, cell.fill = hdr_font, hdr_fill
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            ws.column_dimensions[get_column_letter(j)].width = widths[j - 1]
        ws.freeze_panes = "A2"

    # Read me
    ws = wb.active
    ws.title = "Read me"
    st = collections.Counter(c["status"] for c in clist)
    kinds = collections.Counter(L.get("kind") or "page not available" for L in listings)
    lines = [
        ("Master catalogue - DRAFT for approval (toxins + fillers / skin boosters / biostimulators)", True),
        ("Built from our own supplier data: each listing's page was read (page title, size fields, description), never the listing title alone.", False),
        ("Listings that agree on brand + line + strength + lidocaine + pack are grouped into one product code.", False),
        ("", False),
        ("Status of each product code:", True),
        (f"official ({st['official']}) - matches an official presentation (emc SmPC or manufacturer IFU); source link given", False),
        (f"consensus ({st['consensus']}) - the same presentation is sold by 2 or more suppliers; not yet checked against an official document", False),
        (f"single_supplier ({st['single_supplier']}) - seen at one supplier only; please confirm it exists", False),
        (f"Needs information ({sum(1 for L in listings if L.get('needs'))} listings) - line or pack size could not be read from the page; see sheet 'Needs information'", False),
        ("", False),
        ("What to do (yellow columns in sheet 'Master products'):", True),
        ("Approve? : choose Yes / No / Edit.   Correct name / pack : write the correct value if 'Edit'.   Notes : anything else.", False),
        ("Example: code TEOSYAL-RHA-3-L-2X1.2ML, Approve? = Yes ; code ...-2X1ML with a wrong line, Approve? = Edit, Correct = 'RHA 2, 2 x 1 ml'.", False),
        ("", False),
        ("Sheets:", True),
        ("Master products - one row per proposed product code (what the site would list)", False),
        ("Supplier listings - every supplier listing with the code it was matched to and any flags", False),
        ("Not products - posters, creams, bundles, courses etc. found under these brands (kept out of the comparison)", False),
        ("", False),
        (f"Totals: {len(listings)} listings in scope; " + ", ".join(f"{k}: {v}" for k, v in kinds.most_common()) +
         f"; {len(clist)} proposed product codes from {len({c['brand'] for c in clist})} brands.", False),
        ("'Listings' count in Master products is a COUNTIF formula over 'Supplier listings'; 'Suppliers' is a distinct count computed when the file was built.", False),
    ]
    for t, b in lines:
        ws.append([t])
        ws.cell(row=ws.max_row, column=1).font = Font(name=F, bold=b, size=12 if b else 10)
    ws.column_dimensions["A"].width = 140

    # Master products
    ws = wb.create_sheet("Master products")
    H = ["Code", "Status", "Category", "Brand", "Line", "Strength", "Lidocaine", "Market", "Units per pack", "Volume per unit (ml)",
         "Suppliers", "Listings", "Official source", "Example listings", "Note", "Approve?", "Correct name / pack", "Notes"]
    sheet(ws, H, [34, 15, 14, 18, 22, 9, 10, 8, 8, 10, 9, 9, 30, 60, 40, 10, 26, 26])
    dv = DataValidation(type="list", formula1='"Yes,No,Edit"', allow_blank=True)
    ws.add_data_validation(dv)
    for n, c in enumerate(clist, start=2):
        ex = " | ".join(f"{L['supplier']}: {L['url']}" for L in c["listings"][:3])
        ws.append([c["code"], c["status"], c["category"], c["brand"], c["line"], c["strength"], c["lidocaine"], c["market"],
                   c["count"], c["volume_ml"], len(c["suppliers"]), f"=COUNTIF('Supplier listings'!$F:$F,A{n})", c["source"], ex, c["note"], "", "", ""])
        for j in range(1, len(H) + 1):
            cell = ws.cell(row=n, column=j)
            cell.font = Font(name=F, size=9)
            cell.alignment = Alignment(vertical="top", wrap_text=j in (14, 15))
        ws.cell(row=n, column=2).fill = PatternFill("solid", fgColor=st_fill[c["status"]])
        if c["source"]:
            ws.cell(row=n, column=13).hyperlink = c["source"]
            ws.cell(row=n, column=13).font = Font(name=F, size=9, color="0563C1", underline="single")
        for j in (16, 17, 18):
            ws.cell(row=n, column=j).fill = inp_fill
        dv.add(f"P{n}")
    ws.auto_filter.ref = f"A1:{get_column_letter(len(H))}{ws.max_row}"
    ws.cell(row=1, column=16).comment = Comment("Fill in: Yes / No / Edit", "draft")

    # Supplier listings
    ws = wb.create_sheet("Supplier listings")
    H2 = ["ID", "Supplier", "Listing title", "Page name", "Link", "Code", "Brand", "Line", "Lidocaine", "Units", "Volume (ml)", "Pack read from", "Flags"]
    sheet(ws, H2, [9, 20, 40, 40, 12, 34, 16, 20, 10, 7, 9, 20, 60])
    for L in listings:
        if L.get("kind") not in ("product", ""):
            continue
        ws.append([L["id"], L["supplier"], L["title"], L.get("page_title", ""), "open", L.get("code", ""), L["brand"], L.get("line", ""),
                   L.get("lidocaine", ""), L.get("count"), L.get("volume_ml"), L.get("pack_source", ""), L.get("flags", "")])
        n = ws.max_row
        ws.cell(row=n, column=5).hyperlink = L["url"]
        for j in range(1, len(H2) + 1):
            ws.cell(row=n, column=j).font = Font(name=F, size=9, color="0563C1" if j == 5 else "000000", underline="single" if j == 5 else None)
    ws.auto_filter.ref = f"A1:{get_column_letter(len(H2))}{ws.max_row}"

    # Needs information
    ws = wb.create_sheet("Needs information")
    H4 = ["ID", "Supplier", "Brand", "Line (if known)", "Missing", "Page name", "Link", "Flags"]
    sheet(ws, H4, [9, 20, 18, 22, 12, 50, 10, 50])
    for L in listings:
        if not L.get("needs"):
            continue
        ws.append([L["id"], L["supplier"], L["brand"], L["line"] if L["line"] != "(base)" else "", L["needs"], L.get("page_title", ""), "open", L.get("flags", "")])
        n = ws.max_row
        ws.cell(row=n, column=7).hyperlink = L["url"]
        for j in range(1, len(H4) + 1):
            ws.cell(row=n, column=j).font = Font(name=F, size=9, color="0563C1" if j == 7 else "000000")
    ws.auto_filter.ref = f"A1:H{ws.max_row}"

    # Not products
    ws = wb.create_sheet("Not products")
    H3 = ["ID", "Supplier", "Brand", "Kind", "Page name", "Link"]
    sheet(ws, H3, [9, 20, 18, 22, 60, 12])
    for L in listings:
        if L.get("kind") in ("product", ""):
            continue
        ws.append([L["id"], L["supplier"], L["brand"], L["kind"], L.get("page_title", ""), "open"])
        n = ws.max_row
        ws.cell(row=n, column=6).hyperlink = L["url"]
        for j in range(1, len(H3) + 1):
            ws.cell(row=n, column=j).font = Font(name=F, size=9, color="0563C1" if j == 6 else "000000")
    ws.auto_filter.ref = f"A1:F{ws.max_row}"

    out = ROOT / "output" / "master_catalogue_draft.xlsx"
    wb.save(out)
    print(out, "| codes:", dict(st), "| listings:", dict(kinds))


if __name__ == "__main__":
    main()
