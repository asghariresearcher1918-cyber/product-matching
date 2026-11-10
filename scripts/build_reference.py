"""Step 2 - reference_catalog.csv (one row per family/variant), built from the cached official
sources in refcache/. Every value below was read from the cited source; nothing is invented.
Where no official source could be read, reference_status = not_found (or partial).

Usage: python -I scripts/build_reference.py
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMC = "https://www.medicines.org.uk/emc/product/"

COLS = ["family_id", "variant_key", "family", "brand", "manufacturer", "uk_form", "route",
        "strength_or_composition", "unit_volume", "pack_contents", "pack_sizes", "lidocaine_versions",
        "uk_vs_non_uk", "reference_status", "source_urls", "notes"]

R = [
    # ---------------- Pabrinex / Vitamin B&C ----------------
    dict(family_id="F-PABRINEX", variant_key="IV", family="Pabrinex IV High Potency (Vitamin B&C IVHP)",
         brand="Pabrinex / Vitamin B&C IVHP", manufacturer="Grünenthal Ltd (MAH, PL 21727/0116); older packs Kyowa Kirin / Archimedes",
         uk_form="Concentrate for solution for infusion", route="IV",
         strength_or_composition="No.1 5 ml: thiamine HCl 250 mg, riboflavin 4 mg, pyridoxine HCl 50 mg; No.2 5 ml: ascorbic acid 500 mg, nicotinamide 160 mg, glucose 1000 mg",
         unit_volume="5 ml + 5 ml (one pair)", pack_contents="pairs of 5 ml amber ampoules (No.1 + No.2)",
         pack_sizes="6 pairs; 10 pairs (not all marketed)", lidocaine_versions="n/a", uk_vs_non_uk="UK licence",
         reference_status="found", source_urls=EMC + "1427/smpc ; " + EMC + "1427/pil",
         notes="emc now titles it 'Pabrinex/Vitamin B&C Intravenous High Potency'. PIL ingredient list also gives strengths per 10 ml vial (500 mg thiamine etc.) but SmPC 6.5 lists only 5 ml pairs - no 10 ml pack recorded. emc search 'pabrinex' returns only this product."),
    dict(family_id="F-PABRINEX", variant_key="IM", family="Pabrinex IM High Potency",
         brand="Pabrinex", manufacturer="(historic: Kyowa Kirin / Archimedes)", uk_form="Solution for injection", route="IM",
         strength_or_composition="(supplier pages) No.1 5 ml: thiamine 250 mg, riboflavin 4 mg, pyridoxine 50 mg; No.2 2 ml: ascorbic acid 500 mg, nicotinamide 160 mg",
         unit_volume="5 ml + 2 ml (one pair) - per supplier pages/pack images only", pack_contents="pairs of 5 ml + 2 ml ampoules - per pack images only",
         pack_sizes="10 pairs - per pack images only", lidocaine_versions="n/a", uk_vs_non_uk="UK (historic)",
         reference_status="not_found", source_urls="https://www.medicines.org.uk/emc/search?q=pabrinex%20intramuscular (0 results) ; https://products.mhra.gov.uk/search/?search=pabrinex (site error during run)",
         notes="No current emc SmPC/PIL for the IM product. Hospital note that IM is discontinued: NOT verified (MHRA products database returned 'technical issues'). Every IM listing in the pilot is out of stock/unavailable, which is consistent with but does not prove discontinuation."),
    dict(family_id="F-VITBC-ASPIRE", variant_key="IV", family="Vitamin B and C IV High Potency (Vitenta)",
         brand="Vitenta / Vitamin B and C IVHP", manufacturer="Aspire Pharma Ltd (MAH, PL 35533/0195); made by Alfasigma S.p.A., Italy",
         uk_form="Concentrate for solution for infusion", route="IV",
         strength_or_composition="Same as Pabrinex IV: No.1 5 ml thiamine 250/riboflavin 4/pyridoxine 50 mg; No.2 5 ml ascorbic acid 500/nicotinamide 160/glucose 1000 mg",
         unit_volume="5 ml + 5 ml", pack_contents="pairs of 5 ml ampoules", pack_sizes="6 pairs; 10 pairs (not all marketed)",
         lidocaine_versions="n/a", uk_vs_non_uk="UK licence", reference_status="found",
         source_urls=EMC + "101125/smpc ; " + EMC + "101125/pil",
         notes="Different licence/brand from Pabrinex, identical composition and presentation -> separate family, equivalent_to F-PABRINEX/IV. Not made by DEMO S.A."),
    dict(family_id="F-VITBC-DEMO", variant_key="IV", family="Vitamins B+C IV High Potency (DEMO S.A. pack)",
         brand="(none)", manufacturer="DEMO S.A. (Greece) - per pack image only", uk_form="Concentrate for solution for infusion (pack text)", route="IV (pack text 'Single IV use')",
         strength_or_composition="unknown", unit_volume="5 ml (pack text)", pack_contents="6 pairs of 5 ml ampoules (pack text)", pack_sizes="6 pairs (pack text)",
         lidocaine_versions="n/a", uk_vs_non_uk="NOT on emc - likely imported/unlicensed", reference_status="not_found",
         source_urls="https://www.medicines.org.uk/emc/search?q=vitamin%20b%26c (2 results, neither DEMO)",
         notes="Seen only in supplier images (Fox R03210, Ask R10511)."),
    # ---------------- Toxins ----------------
    dict(family_id="F-BOTOX", variant_key="50U|100U|200U", family="BOTOX (cosmetic/therapeutic)", brand="BOTOX", manufacturer="AbbVie Ltd",
         uk_form="Powder for solution for injection", route="IM / intradermal",
         strength_or_composition="50, 100 or 200 Allergan Units per vial (separate SmPCs)", unit_volume="1 vial",
         pack_contents="carton of 1 vial", pack_sizes="packs of 1, 2, 3 or 6 cartons (not all marketed)", lidocaine_versions="n/a",
         uk_vs_non_uk="UK licence", reference_status="found", source_urls=EMC + "6185/smpc ; " + EMC + "859/smpc ; " + EMC + "436/smpc", notes=""),
    dict(family_id="F-BOCOUTURE", variant_key="50U|100U", family="BOCOUTURE", brand="BOCOUTURE", manufacturer="Merz Pharmaceuticals GmbH",
         uk_form="Powder for solution for injection", route="IM",
         strength_or_composition="50 or 100 units botulinum toxin type A (150 kD) per vial", unit_volume="1 vial",
         pack_contents="vials", pack_sizes="1, 2, 3 or 6 vials (not all marketed)", lidocaine_versions="n/a",
         uk_vs_non_uk="UK licence (PL 29978/0002, /0005)", reference_status="found", source_urls=EMC + "7418/smpc", notes=""),
    dict(family_id="F-AZZALURE", variant_key="125SU", family="Azzalure", brand="Azzalure", manufacturer="Ipsen Ltd",
         uk_form="Powder for solution for injection", route="IM",
         strength_or_composition="125 Speywood units per vial", unit_volume="1 vial", pack_contents="vials", pack_sizes="1 or 2 vials",
         lidocaine_versions="n/a", uk_vs_non_uk="UK licence (PL 06958/0031)", reference_status="found", source_urls=EMC + "6584/smpc",
         notes="'Azzalure Syringe x 10' is not a presentation of Azzalure."),
    # ---------------- Oral ----------------
    dict(family_id="F-WEGOVY-TAB", variant_key="1.5mg|4mg|9mg|25mg", family="Wegovy tablets (oral semaglutide)", brand="Wegovy", manufacturer="Novo Nordisk A/S",
         uk_form="Tablet", route="oral", strength_or_composition="4 mg semaglutide per tablet (SmPC 102345; other strengths have own SmPCs - not read in pilot)",
         unit_volume="tablet", pack_contents="Alu/Alu blisters", pack_sizes="10, 30, 90 tablets", lidocaine_versions="n/a",
         uk_vs_non_uk="UK licence (PL 04668/0467)", reference_status="found", source_urls=EMC + "102345/smpc", notes="Different product from Wegovy injection pens."),
    dict(family_id="F-ACICLOVIR-200", variant_key="tablet", family="Aciclovir 200 mg tablets (generic)", brand="generic (Milpharm, Wockhardt, Accord...)",
         manufacturer="various", uk_form="Tablet", route="oral", strength_or_composition="200 mg aciclovir", unit_volume="tablet",
         pack_contents="blister", pack_sizes="25; 100", lidocaine_versions="n/a", uk_vs_non_uk="UK licences", reference_status="found",
         source_urls=EMC + "11673/smpc ; " + EMC + "2353/smpc", notes=""),
    dict(family_id="F-ACICLOVIR-200", variant_key="dispersible", family="Aciclovir 200 mg dispersible tablets", brand="generic / Zovirax",
         manufacturer="various (Zovirax: GSK)", uk_form="Dispersible (film-coated) tablet", route="oral", strength_or_composition="200 mg aciclovir",
         unit_volume="tablet", pack_contents="blister", pack_sizes="25", lidocaine_versions="n/a", uk_vs_non_uk="UK licences", reference_status="found",
         source_urls=EMC + "1634/smpc", notes="Dispersible vs plain tablet = different pharmaceutical form -> different variant."),
    # ---------------- Fillers / skin boosters (devices) ----------------
    dict(family_id="F-JUVEDERM-ULTRA", variant_key="Ultra 2|Ultra 3", family="Juvederm Ultra", brand="Juvederm", manufacturer="Allergan Aesthetics (AbbVie)",
         uk_form="Hyaluronic acid gel in pre-filled syringe (CE/UKCA device)", route="intradermal / submucosal",
         strength_or_composition="Ultra 2 / Ultra 3 are different models (never merged)", unit_volume="not confirmed from official source",
         pack_contents="not confirmed", pack_sizes="not confirmed", lidocaine_versions="supplier pages: UK packs contain 0.3% lidocaine; not confirmed officially",
         uk_vs_non_uk="not confirmed", reference_status="partial",
         source_urls="https://www.juvederm.co.uk/ ; https://www.allerganaesthetics.co.uk/ (no presentation data on public pages)",
         notes="UK consumer/HCP sites have no presentation table; IFU not reachable in pilot."),
    dict(family_id="F-TEOSYAL", variant_key="RHA 3|Redensity 1|Redensity 2", family="Teosyal (RHA / PureSense Redensity)", brand="Teosyal", manufacturer="Teoxane SA",
         uk_form="Hyaluronic acid gel in pre-filled syringe (device)", route="intradermal",
         strength_or_composition="RHA 3 23 mg/ml (Church page); models never merged", unit_volume="RHA 3: suppliers disagree (1 ml vs 1.2 ml) - not confirmed",
         pack_contents="not confirmed", pack_sizes="not confirmed", lidocaine_versions="RHA 3 box image: 'hyaluronic acid + lidocaine'",
         uk_vs_non_uk="not confirmed", reference_status="partial",
         source_urls="https://www.teoxane.com/en/productinfo-europe (EU patient IFP PDF on teoxanestorage.blob.core.windows.net - host not allowed in pilot)", notes=""),
    dict(family_id="F-PROFHILO", variant_key="H+L|Structura", family="Profhilo", brand="Profhilo", manufacturer="IBSA Farmaceutici Italia",
         uk_form="Hyaluronic acid gel in pre-filled syringe (device)", route="subcutaneous / intradermal",
         strength_or_composition="H+L: 32 mg H-HA + 32 mg L-HA / 2 ml (pack image); Structura: 45 mg + 45 mg / 2 ml (pack image)",
         unit_volume="2 ml (pack images)", pack_contents="1 pre-filled syringe + needles (pack images)", pack_sizes="1",
         lidocaine_versions="none", uk_vs_non_uk="'UK hologram' box variants exist - see open question", reference_status="partial",
         source_urls="https://ibsaderma.com/products/profhilo/ (product line page only, no presentation)", notes=""),
    # ---------------- Needles / cannulas (devices) ----------------
    dict(family_id="F-TSK-STERIGLIDE", variant_key="gauge x length", family="TSK STERiGLIDE cannula", brand="TSK", manufacturer="TSK Laboratory (Japan)",
         uk_form="Blunt cannula (device)", route="n/a", strength_or_composition="gauge x length defines the variant (e.g. 25G x 38mm, 27G x 50mm)",
         unit_volume="n/a", pack_contents="cannulas (+ pre-hole needles)", pack_sizes="20 (supplier codes SGC-xxxxx-020)", lidocaine_versions="n/a",
         uk_vs_non_uk="n/a", reference_status="not_found", source_urls="https://tsklab.com/ (connection refused in pilot)", notes=""),
    dict(family_id="F-BD-MICROLANCE3", variant_key="gauge x length", family="BD Microlance 3 hypodermic needle", brand="BD Microlance 3", manufacturer="Becton Dickinson",
         uk_form="Hypodermic needle (device)", route="n/a", strength_or_composition="gauge x length (30G x 1/2\" = 0.3 x 13 mm, yellow hub)",
         unit_volume="n/a", pack_contents="needles", pack_sizes="100 (pack images)", lidocaine_versions="n/a", uk_vs_non_uk="n/a",
         reference_status="not_found", source_urls="https://www.bd.com/en-uk/... (Access Denied to automated requests - not bypassed)", notes=""),
]


def main():
    out = ROOT / "output" / "reference_catalog.csv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in R:
            w.writerow({c: r.get(c, "") for c in COLS})
    print(f"{out}: {len(R)} rows")


if __name__ == "__main__":
    main()
