"""Category cleanup pass: re-file items that landed in the wrong category/scope.
Sources of the mistakes are the flags the catalogues already produced:
 - device catalogue 're-file' rows (IUDs, respiratory spacers, x-ray, air purifiers, home test kits, general-pharmacy
   injectables), and
 - skincare rows that are actually licensed POM topicals (Emla, Fucidin, Betnovate, Hydrocortisone, Differin, Rozex,
   Skinoren, aciclovir) - NOT cosmeceutical azelaic brands like Noon Aesthetics.
Clinic-relevant medicines (EpiPen, Lignospan, and the POM topicals) are re-categorised into Medicines and KEPT in
Phase 1. Genuinely non-clinic items (contraceptives, home blood tests, respiratory spacers, dental x-ray, air
purifiers, and general-pharmacy injectables Praluent/Xolair/Genotropin) are scoped out as 'Removed - general pharmacy'.
Writes: appends to data/category_overrides.csv (id,category,note) and writes data/scope_overrides.csv (id,scope,group,note).
Usage: python -I scripts/cleanup_categories.py   (then re-run categorize_all.py + apply_scope.py)"""
import csv, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MED_INJ = "Medicine - injectable / anaesthetic / emergency"
MED_TOP = "Medicine - topical / eye / other"
REMOVED = "Removed - general pharmacy"

recats = {}   # id -> (category, note)
scopes = {}   # id -> (scope, group, note)

# ---- device catalogue re-file rows ----
dev = [m for m in csv.DictReader(open(ROOT / "catalogue/final/device_listing_map.csv")) if m["confidence"] == "re-file"]
for m in dev:
    t = m["title"].lower()
    if re.search(r"\bepipen\b|epi pen", t):
        recats[m["id"]] = (MED_INJ, "re-filed from Devices: adrenaline auto-injector (emergency medicine)")
    elif re.search(r"lignospan", t):
        recats[m["id"]] = (MED_INJ, "re-filed from Devices: dental local anaesthetic cartridge")
    elif re.search(r"praluent|xolair|genotropin", t):
        recats[m["id"]] = (MED_INJ, "re-filed from Devices: injectable medicine")
        scopes[m["id"]] = (REMOVED, "general pharmacy", "not an aesthetic/skin/dental clinic product")
    elif re.search(r"mirena|kyleena|jaydess|nexplanon|copper\s*t|nova\s*t|novaplus|\bt\s*380", t):
        scopes[m["id"]] = (REMOVED, "general pharmacy - contraceptive", "IUD/implant, not a clinic aesthetic product")
    elif re.search(r"aerochamber|volumatic|easychamber|spacer|nebuliser|nebulizer|aerosol", t):
        scopes[m["id"]] = (REMOVED, "general pharmacy - respiratory", "respiratory device, not a clinic aesthetic product")
    elif re.search(r"x-?ray|step wedge|film edge|disposa-?shield", t):
        scopes[m["id"]] = (REMOVED, "dental x-ray imaging", "imaging consumable, out of current scope")
    elif re.search(r"purifier|airbubbl|airhavn", t):
        scopes[m["id"]] = (REMOVED, "facility equipment", "air purifier, not a clinical product")
    elif re.search(r"home blood test|testing kit|ketostix|uristix|reagent strip|profile|blood pressure monitor|pillcutter|pill cutter", t):
        scopes[m["id"]] = (REMOVED, "general pharmacy - diagnostics", "home test / diagnostic, out of current scope")
    else:
        scopes[m["id"]] = (REMOVED, "general pharmacy", "flagged not an aesthetic device")

# ---- skincare rows that are really licensed POM topicals (exclude cosmeceutical azelaic brands) ----
POM = re.compile(r"\bemla\b|\bfucidin\b|\bdaktacort\b|hydrocortisone|\bbetnovate\b|\bdifferin\b|\brozex\b|\bskinoren\b|"
                 r"\befudix\b|aciclovir|\bzovirax\b|virasorb|\bdermovate\b|\beumovate\b|\belocon\b|\bfinacea\b", re.I)
COSMECEUTICAL = re.compile(r"\bnoon\b|azelaicbr|azelaics\b", re.I)  # Noon Aesthetics azelaic = cosmeceutical, keep in skincare
for m in csv.DictReader(open(ROOT / "catalogue/final/skincare_listing_map.csv")):
    if POM.search(m["title"]) and not COSMECEUTICAL.search(m["title"]):
        recats[m["id"]] = (MED_TOP, "re-filed from Skincare: licensed POM topical medicine")

# ---- append to category_overrides.csv (replace any existing row for these ids) ----
ov_path = ROOT / "data/category_overrides.csv"
existing = list(csv.DictReader(open(ov_path, encoding="utf-8")))
kept = [o for o in existing if o["id"] not in recats]
with open(ov_path, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["id", "category", "note"]); w.writeheader()
    w.writerows(kept)
    for i, (cat, note) in sorted(recats.items()):
        w.writerow({"id": i, "category": cat, "note": note})

# ---- write scope_overrides.csv ----
with open(ROOT / "data/scope_overrides.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["id", "scope", "scope_group", "note"]); w.writeheader()
    for i, (sc, grp, note) in sorted(scopes.items()):
        w.writerow({"id": i, "scope": sc, "scope_group": grp, "note": note})

print(f"recategorised (kept in scope unless also scoped out): {len(recats)}")
print(f"  -> Medicine injectable: {sum(1 for v in recats.values() if v[0]==MED_INJ)}")
print(f"  -> Medicine topical:    {sum(1 for v in recats.values() if v[0]==MED_TOP)}")
print(f"scoped out (Removed - general pharmacy): {len(scopes)}")
by = {}
for sc, grp, note in scopes.values(): by[grp] = by.get(grp, 0) + 1
for k, v in sorted(by.items()): print(f"  {v:3} {k}")
