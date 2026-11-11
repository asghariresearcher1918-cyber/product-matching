"""Reference catalogue ("master list") for toxins + fillers/skin boosters/biostimulators.

Writes four linked tables to catalogue/:
  families.csv      family_id, brand, line, manufacturer, category, aliases (regex), reference_status
  variants.csv      variant_id, family_id, label, attributes (json), reference_status
  presentations.csv presentation_id, variant_id, unit, unit_volume_ml, units_per_pack, pack_sizes, needles, reference_status
  sources.csv       source_id, family_id, url, local_copy, quote, read_on

reference_status: official (read from emc SmPC / manufacturer IFU), supplier_consensus (to be filled from
>=2 suppliers agreeing, NOT official), not_found. Nothing here is invented: every official fact has a quote
in sources.csv. Usage: python -I scripts/build_catalogue.py
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "catalogue"
EMC = "https://www.medicines.org.uk/emc/product/"
READ_ON = "2026-11-11"
F, V, P, S = [], [], [], []


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def fam(brand, line, manufacturer, category, aliases, status, sources=()):
    fid = "F-" + slug(f"{brand} {line}" if line else brand)
    F.append(dict(family_id=fid, brand=brand, line=line, manufacturer=manufacturer, category=category,
                  aliases=aliases, reference_status=status))
    for url, local, quote in sources:
        S.append(dict(source_id=f"S{len(S) + 1:04d}", family_id=fid, url=url, local_copy=local, quote=quote, read_on=READ_ON))
    return fid


def var(fid, label, attrs, status):
    vid = f"{fid}/{slug(label)}"
    V.append(dict(variant_id=vid, family_id=fid, label=label, attributes=json.dumps(attrs, ensure_ascii=False), reference_status=status))
    return vid


def pres(vid, unit, unit_volume_ml, units_per_pack, pack_sizes, needles, status):
    pid = f"{vid}/{slug(f'{units_per_pack}x{unit_volume_ml}{unit}')}"
    P.append(dict(presentation_id=pid, variant_id=vid, unit=unit, unit_volume_ml=unit_volume_ml, units_per_pack=units_per_pack,
                  pack_sizes=pack_sizes, needles=needles, reference_status=status))


# ======================================================== TOXINS (emc SmPC, official)
def toxin(brand, manufacturer, aliases, strengths, unit_name, form, pack_sizes, quotes):
    fid = fam(brand, "", manufacturer, "toxin", aliases, "official",
              [(EMC + n + "/smpc", f"refcache/www.medicines.org.uk/emc_product_{n}_smpc.html", q) for n, q in quotes])
    for st in strengths:
        vid = var(fid, f"{st} {unit_name}", {"strength": f"{st} {unit_name}", "form": form, "route": "IM"}, "official")
        pres(vid, "vial", "", 1, pack_sizes, "", "official")


toxin("Botox", "AbbVie Ltd", r"\bbotox\b|vistabel", ["50", "100", "200"], "Allergan Units", "powder for solution for injection",
      "1, 2, 3 or 6 cartons of 1 vial",
      [("6185", "Carton comprising one 50 Allergan Unit vial ... Packs containing one, two, three or six cartons."),
       ("859", "Carton comprising one 100 Allergan Unit vial ... Packs containing one, two, three or six cartons."),
       ("436", "Carton comprising one 200 Allergan Unit vial ... Packs containing one, two, three or six cartons.")])
toxin("Bocouture", "Merz Pharmaceuticals GmbH", r"bocouture", ["50", "100"], "units", "powder for solution for injection",
      "1, 2, 3 or 6 vials", [("600", "BOCOUTURE 50 units ... Pack sizes of 1, 2, 3 or 6 vials."),
                             ("7418", "BOCOUTURE 100 units ... Pack sizes of 1, 2, 3 or 6 vials.")])
toxin("Azzalure", "Ipsen Ltd", r"azzalure", ["125"], "Speywood units", "powder for solution for injection", "1 or 2 vials",
      [("6584", "125 Speywood units in a powder in a vial ... Pack size of 1 or 2 vial(s).")])
toxin("Alluzience", "Ipsen Biopharm Ltd", r"alluzience", ["125"], "Speywood units (200 SU/ml, 0.625 ml)", "solution for injection",
      "1 or 2 vials; multipack 6 x 2 vials",
      [("13798", "Each vial contains 125 Speywood units ... in 0.625 ml of solution ... Pack containing 1 or 2 vials ... A multipack contains 6 individual packs, each including 2 vials")])
toxin("Dysport", "Ipsen Ltd", r"dysport", ["300", "500"], "units", "powder for solution for injection", "1 or 2 vials",
      [("964", "containing 300 units of botulinum toxin type A ... Pack sizes of 1 or 2 vials."),
       ("7261", "containing 500 units of botulinum toxin type A ... Pack sizes of 1 or 2 vials.")])
toxin("Letybo", "Croma-Pharma GmbH", r"letybo", ["50"], "units", "powder for solution for injection",
      "1 or 2 vials; multipacks 2 (2x1) and 6 (6x1)",
      [("13707", "Packs containing 1 vial or 2 vials. Multipack containing 2 (2 packs of 1) vials Multipack containing 6 (6 packs of 1) vials")])
toxin("Nuceiva", "Evolus Pharma B.V.", r"nuceiva", ["50"], "units", "powder for solution for injection", "1 vial",
      [("14178", "NUCEIVA 50 Units ... Pack size of one.")])
toxin("Relfydess", "Ipsen Biopharm Ltd", r"relfydess", ["150"], "units (100 U/ml, 1.5 ml)", "solution for injection", "1 or 10 vials",
      [("100710", "Each vial contains 150 units of botulinum toxin type A in 1.5 mL of solution ... Pack containing 1 or 10 vials")])

# ======================================================== TEOSYAL (Teoxane EU IFU, official)
TX = "https://www.teoxane.com/en/dermal-fillers-ifus"
TEO = [  # line, alias regex, ifu code, (volumes), syringes per box, needles, quote
    ("RHA 1", r"rha\s?1\b", "230508", ["1"], "2", "2 x 30G1/2\" per syringe", "q.s. ad 1 mL ... Each box contains two pre-filled syringes of TEOSYAL RHA® 1"),
    ("RHA 2", r"rha\s?2\b", "230510", ["1"], "2", "2 x 30G1/2\" per syringe", "q.s. ad 1 mL ... Each box contains two pre-filled syringes of TEOSYAL RHA® 2"),
    ("RHA 3", r"rha\s?3\b", "230511+230954", ["1", "1.2"], "2", "2 x 27G1/2\" per syringe",
     "IFU 230511 (2024): q.s. ad 1 mL; IFU 230954 'RHA 3 LIDO 1.2 mL' (Oct 2025): q.s. ad 1.2 mL ... Each box contains two pre-filled syringes"),
    ("RHA 4", r"rha\s?4\b", "230512", ["1.2"], "2", "2 x 27G1/2\" per syringe", "q.s. ad 1.2 mL ... Each box contains two pre-filled syringes of TEOSYAL RHA® 4"),
    ("RHA Kiss", r"rha\s?kiss(?!\s?volume)", "230507", ["0.7"], "2", "2 x 30G1/2\" per syringe", "q.s. ad 0.7 mL ... Each box contains two pre-filled syringes of TEOSYAL RHA KISS®"),
    ("RHA Kiss Volume", r"rha\s?kiss\s?volume", "230950", ["1"], "2", "2 x 30G1/2\" per syringe", "q.s. ad 1mL ... Each box contains two pre-filled syringes of RHA® Kiss Volume Lido"),
    ("PureSense Redensity 1", r"redensity\s?(?:1|i)\b(?!i)", "230516", ["1", "3"], "1 or 2", "2 x 30G1/2\" per syringe",
     "q.s. ad 1 mL** ... **also available in syringe of 3 mL ... Each box contains one or two pre-filled syringes"),
    ("PureSense Redensity 2", r"redensity\s?(?:2|ii)\b", "230518", ["1"], "2", "2 x 30G1/2\" per syringe", "q.s. ad 1 mL ... Each box contains two pre-filled syringes of TEOSYAL® PureSense REDENSITY 2"),
    ("PureSense Ultra Deep", r"ultra\s?deep", "230522", ["1.2"], "2", "2 x 25G1\" per syringe", "q.s. ad 1.2 mL ... Each box contains two pre-filled syringes of TEOSYAL® PureSense ULTRA DEEP"),
    ("PureSense Kiss", r"puresense\s?kiss|teosyal\s?(?:27g\s?)?kiss", "230513", ["1"], "2", "2 x 27G1/2\" per syringe", "q.s. ad 1 mL ... Each box contains two pre-filled syringes of TEOSYAL PureSense KISS®"),
]
for line, al, code, vols, n, needles, q in TEO:
    fid = fam("Teosyal", line, "Teoxane SA", "filler", al, "official",
              [(TX, f"refcache/ifu/teoxane/ (IFU {code})", q)])
    vid = var(fid, "lidocaine 0.3%", {"lidocaine": True, "market": "EU/UK (CE)"}, "official")
    for v in vols:
        pres(vid, "pre-filled syringe", v, n, f"box of {n}", needles, "official")
for line, al in [("PureSense Deep Lines", r"deep\s?lines"), ("PureSense Global Action", r"global\s?action"),
                 ("PureSense Ultimate", r"ultimate"), ("PureSense First Lines", r"first\s?lines"), ("PureSense Touch Up", r"touch\s?up")]:
    fid = fam("Teosyal", line, "Teoxane SA", "filler", al, "not_found",
              [(TX, "refcache/rendered/teoxane_ifus.html", "not in Teoxane's current EU IFU list (possibly discontinued - unverified)")])
    var(fid, "lidocaine (per supplier pages)", {"lidocaine": True}, "supplier_consensus")

# ======================================================== OTHER TOP BRANDS (lines only; facts = supplier consensus, NOT official)
LINES = {
    ("Juvederm", "Allergan Aesthetics (AbbVie)", "filler"): [
        ("Ultra 2", r"ultra\s?2\b"), ("Ultra 3", r"ultra\s?3\b"), ("Ultra 4", r"ultra\s?4\b"), ("Ultra Smile", r"(ultra\s?)?smile"),
        ("Volift", r"volift(?!\s?re-?\s?touch)"), ("Volift Retouch", r"volift\s?re-?\s?touch"), ("Volbella", r"volbella"),
        ("Volite", r"volite"), ("Voluma", r"voluma\b"), ("Volux", r"volux"), ("Skinvive", r"skinvive")],
    ("Restylane", "Galderma", "filler"): [
        ("Restylane (Classic)", r"restylane\s?(classic|classyc)?\s*(?:lido|$|\(|\d)"), ("Lyft", r"lyft"), ("Kysse", r"kysse"), ("Refyne", r"refyne"),
        ("Defyne", r"defyne"), ("Volyme", r"volyme"), ("Eyelight", r"eyelight"), ("Fynesse", r"fynesse"),
        ("Skinboosters Vital", r"vital(?!\s?light)"), ("Skinboosters Vital Light", r"vital\s?light")],
    ("Belotero", "Merz Aesthetics", "filler"): [
        ("Soft", r"\bsoft\b"), ("Balance", r"balance"), ("Intense", r"intense"), ("Volume", r"volume"),
        ("Lips Shape", r"lips?\s?shape|shape\s?lips"), ("Lips Contour", r"lips?\s?cont|contour\s?lips"), ("Revive", r"revive")],
    ("Stylage", "Laboratoires Vivacy", "filler"): [
        ("S", r"stylage\s?(?:bi-?\s?(?:soft|flex)\s?)?s\b"), ("M", r"stylage\s?(?:bi-?\s?(?:soft|flex)\s?)?m\b"), ("L", r"stylage\s?(?:bi-?\s?(?:soft|flex)\s?)?l\b"),
        ("XL", r"\bxl\b"), ("XXL", r"\bxxl\b"), ("Special Lips", r"special\s?lips"), ("Lips Plus", r"lips\s?plus"),
        ("Hydro", r"hydro(?!\s?max)"), ("HydroMax", r"hydro\s?max")],
    ("Revolax", "Across Co. (Korea)", "filler"): [("Fine", r"fine"), ("Deep", r"deep"), ("Sub-Q", r"sub[\s-]?q")],
    ("Profhilo", "IBSA", "skin booster"): [("H+L", r"profhilo(?!.*(structura|body|haenk|figura|pura|cream))"), ("Structura", r"structura"), ("Body", r"profhilo\s?body")],
    ("Plinest / Newest", "Mastelli", "polynucleotide"): [
        ("Plinest", r"plinest(?!\s?(eye|hair|fast|one))"), ("Plinest Eye", r"plinest\s?eye"), ("Plinest Hair", r"plinest\s?hair"),
        ("Plinest Fast", r"plinest\s?fast"), ("Plinest One", r"plinest\s?one"), ("Newest", r"newest(?!\s?one)"), ("Newest One", r"newest\s?one")],
    ("Jalupro", "Professional Derma", "skin booster"): [
        ("Classic", r"jalupro\s?(classic|amino|2 ?x ?30)|jalupro$"), ("HMW", r"hmw"), ("Super Hydro", r"super\s?hydro"), ("Young Eye", r"young\s?eye")],
    ("Seventy Hyal", "Seventy (Korea)", "skin booster"): [("2000", r"seventy\s?hyal")],
    ("Sunekos", "Professional Derma", "skin booster"): [
        ("200", r"sunekos\s?200\b"), ("1200", r"1200"), ("Performa", r"performa"), ("Cell 15", r"cell\s?15"), ("Body", r"sunekos\s?body")],
    ("Sculptra", "Galderma", "biostimulator"): [("Sculptra", r"sculptra")],
    ("Radiesse", "Merz Aesthetics", "biostimulator"): [("Radiesse", r"radiesse(?!\s?\(?\+|\s?plus)"), ("Radiesse (+)", r"radiesse\s?\(?\+|radiesse\s?plus")],
    ("Nucleofill", "Promoitalia", "polynucleotide"): [
        ("Soft Plus (Eyes)", r"soft\s?plus|nucleofill\s?(soft\s?)?eyes"), ("Medium", r"medium(?!\s?plus)|nucleofill\s?20\b"),
        ("Medium Plus (Hair)", r"medium\s?plus|nucleofill\s?hair"), ("Strong", r"strong(?!\s?plus)|nucleofill\s?25\b"),
        ("Strong Plus (Age)", r"strong\s?plus|nucleofill\s?age")],
    ("Lumi", "Lumi", "skin booster"): [
        ("Lumi-Pro Skin Booster", r"lumi[\s-]?pro(?!\s?(lip|eye))"), ("Lumi-Pro Lips", r"lumi[\s-]?pro\s?lip"), ("Lumi-Pro Eyes", r"lumi[\s-]?pro\s?eye|lumi\s?eyes\s?pro"),
        ("Lumi Eyes", r"lumi[\s-]?eyes(?!\s?pro)"), ("Lumi-PN Face", r"lumi[\s-]?pn\s?face"), ("Lumi-PN Eyes", r"lumi[\s-]?pn\s?eye")],
}
for (brand, mfr, cat), lines in LINES.items():
    for line, al in lines:
        fid = fam(brand, line, mfr, cat, al, "supplier_consensus")
        if brand == "Revolax":
            var(fid, "UK/CE version", {"market": "UK/CE"}, "supplier_consensus")
            var(fid, "non-UK (Korean) version", {"market": "KR"}, "supplier_consensus")

# ======================================================== remaining brands: brand-level only
for b in csv.DictReader(open(ROOT / "data" / "brands_scope.csv", encoding="utf-8")):
    if b["category"] == "toxin" or any(b["brand"].startswith(k[0].split(" ")[0]) for k in LINES) or b["brand"] in ("Teosyal",):
        continue
    fam(b["brand"], "(line to be defined)", b["manufacturer"], b["category"], b["regex"], "not_found")


def main():
    OUT.mkdir(exist_ok=True)
    for name, rows in (("families", F), ("variants", V), ("presentations", P), ("sources", S)):
        with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    st = {}
    for r in F:
        st[r["reference_status"]] = st.get(r["reference_status"], 0) + 1
    print(f"families {len(F)} {st} | variants {len(V)} | presentations {len(P)} | sources {len(S)}")


if __name__ == "__main__":
    main()
