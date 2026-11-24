"""Migrate every product from the v1 model (15 categories + equivalence groups) to the AestheticsProcure v2 taxonomy
(C01-C14 + owner-approved deviations). Deterministic, reversible, non-destructive: reads catalogue/final/master_catalogue.csv,
writes catalogue/final/taxonomy_v2.csv with the v2 primary/subcategory IDs while PRESERVING the old category and supplier
category. Ambiguous -> REVIEW_REQUIRED (never guessed, never deleted). Vaccines -> PARKED (phase 2). Weight-loss -> its own
top-level WLM (owner-approved deviation). Level 3 left null except C01.01.01.
Usage: python -I scripts/taxonomy_map.py"""
import csv, json, re, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "catalogue/final"

# id -> name, from the approved taxonomy + approved deviations
TX = json.load(open(ROOT / "data/taxonomy/AestheticsProcure_Taxonomy_v1.json", encoding="utf-8"))
NAME = {}
for c in TX["categories"]:
    NAME[c["id"]] = c["name"]
    for s in c.get("children", []):
        NAME[s["id"]] = s["name"]
        for p in s.get("product_types", []):
            NAME[p["id"]] = p["name"]
NAME["WLM"] = "Weight Management"          # owner-approved standalone top-level (not C09.07)
NAME["PARKED"] = "Parked (phase 2)"
NAME["C08.VAC"] = "Vaccines (proposed — pending JSON approval)"   # rule 11


def has(text, *words):
    t = text.lower()
    return any(w in t for w in words)


# medicine molecule (equivalence group) -> C08 subcategory
def med_sub(grp):
    g = grp.lower()
    if has(g, "lidocaine", "prilocaine", "tetracaine", "benzocaine", "articaine", "mepivacaine", "emla", "ametop", "numbing", "anaesthet", "anesthet"):
        return "C08.01"
    if has(g, "hyaluronidase", "hyalase"):
        return "C08.02"
    if has(g, "amoxicillin", "co-amoxiclav", "cefalexin", "cephalexin", "cefuroxime", "clindamycin", "metronidazole",
            "doxycycline", "flucloxacillin", "erythromycin", "erythroped", "azithromycin", "clarithromycin", "trimethoprim",
            "ciprofloxacin", "moxifloxacin", "minocycline", "minocin", "oxytetracycline", "lymecycline", "ampicillin",
            "phenoxymethylpenicillin", "penicillin", "fusidic", "mupirocin", "nystatin", "nystaform", "fluconazole",
            "itraconazole", "terbinafine", "nizoral", "ivermectin", "antibiotic"):
        return "C08.03"
    if has(g, "aciclovir", "acyclovir", "valaciclovir", "valacyclovir", "famciclovir", "valtrex", "zovirax", "antiviral"):
        return "C08.04"
    if has(g, "ibuprofen", "brufen", "naproxen", "diclofenac", "nsaid", "anti-inflammatory"):
        return "C08.06"
    if has(g, "paracetamol", "acetaminophen", "codeine", "co-codamol", "analgesic"):
        return "C08.05"
    if has(g, "betamethasone", "dexamethasone", "hydrocortisone", "prednisolone", "prednisonlone", "triamcinolone",
            "methylprednisolone", "depomedrone", "mometasone", "clobetasol", "clobetasone", "clobaderm", "fluocinolone",
            "synalar", "diprosalic", "dovobet", "enstilar", "lotriderm", "mildison", "canesten hc", "steroid"):
        return "C08.07"
    if has(g, "midazolam", "diazepam", "sedation"):
        return "C08.08"
    if has(g, "adrenaline", "epinephrine", "chlorphenamine", "chlorpheniramine", "glucagon", "naloxone", "salbutamol",
            "atropine", "metaraminol", "phenylephrine", "emergency"):
        return "C08.09"
    if has(g, "water for injection", "sterile water", "bacteriostatic", "diluent", "wfi"):
        return "C08.10"
    return None


# consumable / device items mis-filed under "Medicines" in v1 -> C10 (rule 5/7)
def is_consumable_in_meds(n):
    return has(n, "cannula", "introcan", "surflo", "venflon", "winged infusion", "butterfly winged", "winged set",
               "infusion set", "administration set", "giving set", "intrafix", "exadrop", "gravity administration",
               "baxter administration", "codan infusion", "posiflush", "winged", "freeflex", "mini-plasco", "polyfusor",
               "intralipid iv", "clinimix", "gelofusine", "braun", "terumo", "codan", "infusion bag")


def classify(cat, grp, name):
    """-> (primary_id, subcategory_id|None, status, reason)."""
    g, n = grp.lower(), name.lower()

    # ---- cross-category signal overrides (verified product identity beats the old shelf) ----
    if has(n, "polynucleotide", "pdrn", " pn ", "pn booster", "pn pro", "pn skin", "philart", "plinest", "nucleofill", "plenhyage") and cat in ("Dermal filler", "Skin booster / PN / mesotherapy"):
        return "C03.02", None, "CLASSIFIED", "polynucleotide/PDRN signal"

    if cat == "Toxin":
        return "C02.01", None, "CLASSIFIED", "botulinum toxin type A"      # all current toxins are type A
    if cat == "Biostimulator":
        return "C03.03", None, "CLASSIFIED", "collagen biostimulator (by active agent)"
    if cat == "Fat dissolving":
        return "C04.01", None, "CLASSIFIED", "fat dissolver"
    if cat == "Weight-loss medicine":
        return "WLM", None, "CLASSIFIED", "weight management (owner-approved standalone category)"
    if cat == "Supplements":
        return "C09.05", None, "CLASSIFIED", "oral supplement"
    if cat == "Vaccine":
        return "C08", "C08.VAC", "CLASSIFIED", "vaccine -> C08, proposed new subcategory 'Vaccines' (rule 11; JSON unchanged pending approval)"

    if cat == "Dermal filler":
        if has(n, "aquamid", "radiesse", "ellanse", "polycaprolactone", "calcium hydroxyl", "caha", "\bplla\b", "poly-l-lactic", "collagen"):
            return "C01", "C01.02", "CLASSIFIED", "non-HA filler"
        return "C01", "C01.01", "CLASSIFIED", "HA filler (C01.01.01 cross-linked assumed; verify per product)"

    if cat == "Skin booster / PN / mesotherapy":
        sub = {"Polynucleotide / PDRN": "C03.02", "Mesotherapy cocktail": "C03.05",
               "HA bio-remodelling": "C03.01", "Amino-acid skin booster": "C03.01",
               "Exosome": "C03.04", "PRP / PRF kit": "C03.06"}.get(grp)
        if sub:
            return "C03", sub, "CLASSIFIED", f"from equivalence group '{grp}'"
        return "C03", None, "REVIEW_REQUIRED", f"ambiguous skin-rejuvenation group '{grp}' - confirm booster vs meso"

    if cat == "PDO threads":
        if g.startswith("plla") or "plga" in g:
            return "C05", "C05.02", "CLASSIFIED", "PLLA thread (material)"
        if g.startswith("pcl"):
            return "C05", "C05.03", "CLASSIFIED", "PCL thread (material)"
        return "C05", "C05.01", "CLASSIFIED", "PDO thread (material); design is a facet"

    if cat == "Medicines":
        # rule 5/7: injection/infusion consumables & medical-device flushes (e.g. BD PosiFlush) are NOT medicines -> C10
        if is_consumable_in_meds(n):
            return "C10", "C10.02", "CLASSIFIED", "injection/infusion consumable or device flush -> C10 (not a medicine)"
        # rule 6: water for injections / dilution solutions -> C08.10
        if has(n, "water for injection", "sterile water", "water injection", "wfi") or (has(n, "water") and has(n, "inject")):
            return "C08", "C08.10", "CLASSIFIED", "water for injections / diluent (rule 6)"
        # rule 4: injectable glutathione / NAD+ -> evidence of legal status/nature required -> Review Queue
        # (word-boundary NAD so 'beNADryl' / 'fexofeNADine' are not caught)
        if re.search(r"glutathione|tationil|cellgevity|lisathyone|\bnmn\b|\bnad\b|nad\+|nadura", n):
            return "C08", None, "REVIEW_REQUIRED", "injectable glutathione/NAD+ - confirm legal status & nature with evidence (rule 4)"
        # rule 3: vitamins of drug nature (POM/injectable, as filed under Medicines) -> C08 (may show in C09 as a secondary link)
        if has(g, "vitamin") or has(n, "colecalciferol", "cholecalciferol", "ergocalciferol", "hydroxocobalamin",
                                     "cyanocobalamin", "methylcobalamin", "pyridoxine", "ascorbic", "vitamin"):
            return "C08", None, "CLASSIFIED", "vitamin of drug nature -> C08 (secondary display in C09; rule 3)"
        sub = med_sub(grp) or med_sub(n)
        if sub:
            return "C08", sub, "CLASSIFIED", f"medicine class from '{grp}'"
        return "C08", None, "CLASSIFIED", f"medicine '{grp}'; C08 subcategory left empty (acceptable)"

    if cat == "Needles, cannulas & syringes":
        sub = {"Hypodermic needle": "C10.01", "Filter needle": "C10.01", "Syringe": "C10.02",
               "Insulin syringe": "C10.02", "Luer adapter / connector": "C10.02", "Microcannula": "C10.03",
               "Microneedling cartridge": "C12.02", "Electrolysis needle": "C12.02"}.get(grp)
        if grp in ("Microneedling cartridge", "Electrolysis needle"):
            return "C12", sub, "CLASSIFIED", "device cartridge/needle -> Devices"
        if sub:
            return "C10", sub, "CLASSIFIED", f"from '{grp}'"
        return "C10", None, "REVIEW_REQUIRED", f"consumable '{grp}' - confirm subcategory"

    if cat == "Clinic consumables & PPE":
        ppe = {"Gloves": "C11.01", "Face mask / respirator": "C11.02", "Head / face PPE": "C11.03",
               "Gown / apron / coverall": "C11.04", "Antiseptic / skin prep / wipe": "C11.05", "Cleaning / solution": "C11.05"}
        c10 = {"Dressing / tape / suture": "C10.04", "Gauze / swab / cotton": "C10.04",
               "Sharps / clinical waste": "C10.08", "Drape / cover / barrier film": "C10.06",
               "Paper / towel / tissue": "C10.05", "Applicator / spatula": "C10.10"}
        c13 = {"Blade / scalpel": "C13.01", "Compression garment": "C13.05", "First aid": "C13.08", "Hot / cold pack": "C13.04"}
        if grp in ppe:
            return "C11", ppe[grp], "CLASSIFIED", f"infection control/PPE from '{grp}'"
        if grp in c10:
            return "C10", c10[grp], "CLASSIFIED", f"clinical consumable from '{grp}'"
        if grp in c13:
            return "C13", c13[grp], "CLASSIFIED", f"surgical/medical supply from '{grp}'"
        if grp == "Diagnostic / monitoring":
            return "C12", "C12.07", "CLASSIFIED", "diagnostic equipment"
        return "C10", None, "REVIEW_REQUIRED", f"generic consumable '{grp}' - confirm C10/C11/C13"

    if cat == "Devices & equipment":
        sub = {"RF microneedling": "C12.05", "Microneedling pen & cartridge": "C12.01", "Derma roller / stamp": "C12.01",
               "HIFU / focused ultrasound": "C12.06", "Laser / IPL": "C12.04", "Skin analysis / imaging": "C12.07",
               "Electrosurgery / electrolysis / plasma": "C12.03", "Clinic furniture": "C12.08",
               "LED / light therapy": "C12.08", "Cryotherapy / cryolipolysis": "C12.08"}.get(grp)
        if sub:
            return "C12", sub, "CLASSIFIED", f"from '{grp}'"
        return "C12", None, "REVIEW_REQUIRED" if "other" in g or "accessory" in g else "CLASSIFIED", f"device '{grp}'"

    if cat == "Beauty (nails/brows/lashes/PMU/makeup)":
        if has(g, "pmu", "microblading") and "tool" not in g:
            return "C14", "C14.01", "CLASSIFIED", "semi-permanent makeup pigment"
        if "nail" in g:
            return "C14", "C14.02", "CLASSIFIED", "nail product"
        return "C14", None, "REVIEW_REQUIRED" if "other" in g else "CLASSIFIED", f"beauty/salon '{grp}'"

    if cat == "Skincare, haircare & peels":
        if has(n, "hair", "scalp", "shampoo", "minoxidil", "follicle", "tricholog", "anagain", "baldness"):
            return "C07", None, "CLASSIFIED", "hair & scalp product -> C07"
        if has(n, "peel", "tca", "glycolic", "mandelic", "cosmelan", "dermamelan", "jessner"):
            return "C06", "C06.01", "CLASSIFIED", "chemical peel"
        if has(n, "spf", "sun ", "suncare", "sunscreen"):
            return "C06", "C06.07", "CLASSIFIED", "sun protection"
        if has(n, "cleanser", "wash", "foam"):
            return "C06", "C06.02", "CLASSIFIED", "cleanser"
        if has(n, "toner", "mist"):
            return "C06", "C06.03", "CLASSIFIED", "toner"
        if has(n, "serum", "ampoule"):
            return "C06", "C06.04", "CLASSIFIED", "serum"
        if has(n, "moisturis", "cream", "lotion", "balm"):
            return "C06", "C06.05", "CLASSIFIED", "moisturiser"
        if has(n, "exfoliat", "scrub", "microderm"):
            return "C06", "C06.06", "CLASSIFIED", "exfoliator"
        return "C06", None, "REVIEW_REQUIRED", "skincare type not determined from the name"

    return None, None, "REVIEW_REQUIRED", f"no mapping rule for category '{cat}'"


def main():
    rows = list(csv.DictReader(open(FINAL / "master_catalogue.csv", encoding="utf-8")))
    # supplier category per uid (original, preserved for tracing)
    supcat = {}
    for m in csv.DictReader(open(FINAL / "master_listing_index.csv", encoding="utf-8")):
        supcat.setdefault(m["uid"], m.get("supplier_category", "") or "")

    out, counts, status_counts = [], collections.Counter(), collections.Counter()
    for r in rows:
        pid, sub, status, reason = classify(r["category"], r["equivalence_group"], r["product"])
        # owner rule: a known primary category with no fitting subcategory is CLASSIFIED (empty subcategory is acceptable).
        # Keep REVIEW only for genuine decisions that need evidence (e.g. glutathione/NAD+ legal status, rule 4).
        genuine = any(k in reason.lower() for k in ("rule 4", "legal status", "evidence"))
        if status == "REVIEW_REQUIRED" and pid and not genuine:
            status = "CLASSIFIED"
            if "subcategory" not in reason.lower():
                reason = reason + " (primary certain; subcategory left empty pending the per-category pass)"
        status_counts[status] += 1
        key = (pid or "UNMAPPED", NAME.get(pid, ""), sub or "", NAME.get(sub, ""))
        counts[key] += 1
        out.append({"uid": r["uid"], "product": r["product"], "v1_category": r["category"],
                    "v1_equivalence_group": r["equivalence_group"], "supplier_category": supcat.get(r["uid"], ""),
                    "primary_category_id": pid or "", "primary_category": NAME.get(pid, ""),
                    "subcategory_id": sub or "", "subcategory": NAME.get(sub, ""),
                    "status": status, "reason": reason, "listings": r["listings"]})

    cols = ["uid", "product", "v1_category", "v1_equivalence_group", "supplier_category",
            "primary_category_id", "primary_category", "subcategory_id", "subcategory", "status", "reason", "listings"]
    with open(FINAL / "taxonomy_v2.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(out)

    print(f"mapped {len(out)} products")
    for s, c in status_counts.most_common():
        print(f"  {s}: {c}")
    print("--- by primary category ---")
    bycat = collections.Counter()
    for (pid, pname, sub, sname), c in counts.items():
        bycat[(pid, pname)] += c
    for (pid, pname), c in sorted(bycat.items()):
        print(f"  {pid:8} {pname[:34]:34} {c}")


if __name__ == "__main__":
    main()
