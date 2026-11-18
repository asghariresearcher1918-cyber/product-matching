# Catalogue decisions (agreed with the site owner)

1. **Same active ingredient, different licence/brand** (e.g. Pabrinex vs Vitenta): separate product codes.
   They are linked in an *equivalence group*; searching one shows the others as suggestions.
2. **Generics from different manufacturers**: one product code. The manufacturer is shown clearly on
   every offer (name and/or logo) and can be filtered on.
3. **Profhilo hologram box vs standard**: same product, separate market variant. A visible
   "hologram / no hologram" label and a filter.
4. **Filler with / without lidocaine**: open - waiting for confirmation after explanation
   (they are different licensed products, e.g. Belotero Balance vs Belotero Balance + Lidocaine).
5. **Split packs** (one syringe sold out of a 2-pack): separate pack under the same product code;
   price compared per unit.
6. **Scope**: everything a clinic needs, not only injectables. Consumables are in scope.
   Two display modes:
   - *Compare*: the same product code from several suppliers, price per unit.
   - *Browse & choose*: many brands of a generic item (e.g. sterile gloves); the buyer picks,
     no price comparison needed. Compare only where brand + size are identical.
   Final per-category list: output/scope_review.xlsx (owner reviewing).

## Backlog - phase 2 (agreed 2026-11-18, not started)
Services and fit-out items from output/clinic_needs_master.xlsx ("Service / fit-out"), to add after the
current product list is finalised. Mode: request a quote; revenue: referral commission (often recurring);
feature: renewal reminders (insurance, BLS training, servicing).
Start with: insurance, clinical waste collection contract, training. Then clinic software, prescriber service.
Also later: hand-wash basin (fit-out), Hep B vaccination, LPA / laser safety, fire & H&S assessments / PAT.
Also phase 2+: the missing / weak product items in the needs master list (medical-wholesaler recruitment),
dental clinics.

## Medicines scope (agreed 2026-11-18)
General-pharmacy medicines with no use in aesthetic / skin clinics are out of phase 1 (scope = "Removed - general pharmacy";
rows kept in the data). Men's & women's health, joint (MSK) injections and iron infusions = phase 2.
Misfiled items moved to their right category. Rules: data/medicine_scope.py, applied by scripts/apply_scope.py.
- Kept in phase 1 (owner, 2026-11-18): bimatoprost / Lumigan (lash growth, off-label) and Disolvidase
  (show with a note: per JCCP, MHRA does not regard it as an authorised hyaluronidase alternative).
- Vaccines (2026-11-18): only adult Engerix B kept (staff hepatitis B); the other 24 (flu, travel, childhood) removed from phase 1.
- Supplements (2026-11-18): keep beauty / skin / hair supplements (44); misfiled items moved to their category;
  general vitamins & minerals and clinical nutrition removed from phase 1; Testogel to phase 2.
- Beauty (2026-11-18): keep PMU / microblading (DHSC green list), clinic mineral make-up, lash & brow growth;
  nails, waxing and other salon items set aside as "Later phase - nail & facial salons" (for a future salon phase).
Phase-1 scope is now set for every category (scripts/apply_scope.py). 2 rows still to check by hand
(Life Enhance Pro - page removed; Extra H 10 ml - page gives no product type).
- The 2 unidentifiable rows removed (2026-11-18).

## Category 1 - Toxins (built 2026-11-18, awaiting owner check)
Catalogue from the official UK SmPCs (emc): 9 brands, 23 codes; code = BRAND-UNITS PER VIAL-VIALS PER PACK (+ -ROI for Ireland packs).
Corrections vs the draft: Alluzience vial = 125 Speywood units in 0.625 mL (200 units/mL is the concentration);
Relfydess vial = 150 units in 1.5 mL. Xeomin added (therapeutic licence; 1 listing).
Pack not stated on the page -> 1 vial assumed (smallest official pack), confidence medium.
Equivalence groups by molecule: abobotulinumtoxinA (Azzalure, Alluzience, Dysport), incobotulinumtoxinA (Bocouture, Xeomin).

## How a product page is read (owner rules, 2026-11-18 - all categories)
1. Read every tab of the page, not only the description: Additional information, Size and Care Info (John Bannon),
   Box contents / Contents (Dr Adams, Smile), Size (Church), Product options (ACRE), Product details / SKU (Ask).
2. If still not found, read the text on the product images (OCR; e.g. Moda box photos say "1 vial").
3. Only when nothing is found anywhere, use the category default (toxins: 1 vial).
Related-product blocks ("You may also like", "Bestseller") are cut off so other products' text never counts.
Implemented in scripts/page_facts.py. Known gaps: Aesthetic Pharma product links redirect to the shop listing,
MyPharmacyspace needs a login to show the product, Refine Pharma refuses automated access.
Supplier text errors are flagged, e.g. Smile Pharma's Botox 100 and 200 pages say "Box contains 1 x BOTOX 50IU vial".

## Suppliers on hold (2026-11-18)
Refine Pharma (369 phase-1 listings) and DermaFocus (14) refuse connections from this cloud environment
(their sites load in a normal browser but drop our server). Both tested repeatedly. Kept in the data with
scope "On hold - supplier not connected"; excluded from phase 1 and from price comparison until we connect to
them via a product feed or an authorised login. No circumvention of their anti-bot protection was attempted.

## Category 2 - Biostimulators (built 2026-11-18, awaiting owner check)
35 product codes. Biostimulators are CE-marked devices - no central UK register like emc, so the reference
(scripts/biostim_catalogue.py) gives each brand's active agent, manufacturer and standard pack, with a
'verified' flag: major brands (Radiesse, Sculptra, Lanluma, Ellanse, HArmonyCa, Gouri, Juvelook, Lenisna,
AestheFill) verified; niche brands (aesPLLA, Ecolla, PLLACELL, Julaine, StiCol, Olidia, iLLUMA, PiNkLLA,
Linerase, Novuma, Neauvia Stimulate) marked 'agent to confirm'. Doublyx Evo and Elysiha (Dr Adams only):
agent not stated anywhere reachable -> 'Unconfirmed - ask the supplier'.
All niche-brand agents verified against multiple sources (2026-11-19): aesPLLA/Ecolla/Julaine/Olidia/iLLUMA/StiCol = PLLA; PLLACELL/PiNkLLA = PLLA+PN; Linerase = equine Type I collagen (corrected from porcine); Novuma = CaHA; Neauvia Stimulate = CaHA+HA. Only Doublyx Evo and Elysiha remain unconfirmed (Dr Adams only, no public source).
Code = BRAND-[VARIANT]-STRENGTH-[LIDO]-PACK. Fixed strength per brand used where the brand has one standard
presentation (Sculptra 367.5mg, Ecolla/aesPLLA/StiCol 365mg, PLLACELL/PiNkLLA/Linerase 100mg, Julaine 150mg,
AestheFill/Lenisna 200mg). HArmonyCa normalised to its only UK pack (2 x 1.25ml + lidocaine).
Linerase Hydro separated out (HA booster, not a collagen stimulator). 9 multi-buy bundles left uncoded.

## Principle: list everything, compare where possible (agreed 2026-11-19)
Goal is a one-stop shop - the buyer should find every clinic need on our site and not go elsewhere.
- Product from several suppliers  -> Compare mode (one code, each supplier's price side by side, per unit).
- Product from a single supplier   -> List / Browse mode (no price comparison; findable and buyable).
- Product with incomplete data (e.g. Doublyx Evo, Elysiha - Dr Adams only) -> still listed; ask the supplier
  for the missing details later, but missing data never blocks listing.
Future suppliers / after login: when we find a product in a category that is not yet on our list, add it;
if details are missing, ask that supplier, but list the product straight away.

## Category 3 - Fat dissolving / lipolytics (built 2026-11-19)
33 codes. No central UK register. Active agent verified against sources and used as the equivalence group:
- Deoxycholic acid: Aqualyx (Marllor), DesoFace 0.5% / DesoBody 1.25% (Love Cosmedical), Kabelline, Cincelar
- PPC (phosphatidylcholine + deoxycholate): Lipo Lab (V-Line = face), Dr. Lipo, Inno-TDS Draining PPC, BCN Adipo Forte, Myfiller
- Lecithin/riboflavin 'bottle' type: Lemon Bottle (riboflavin+lecithin+bromelain, no MHRA/CE), The Skinny Bottle, Pine Bottle
- Mesotherapy lipolytic: Mesoestetic C.Prof 221, MesoSculpt C71
- Anti-cellulite / lipodystrophy (NOT a fat dissolver, own group): Alidya (Marllor)
Recategorised out of fat dissolving: Macom CRYSTALSMOOTH (compression garments -> consumables),
CelluErase (subcision blades -> devices), Lemon Bottle Skin Booster (-> skin booster), Master Cream (-> skincare).
Per-vial volume fixed per brand (Aqualyx 8ml, Deso/Lemon Bottle/Lipo Lab 10ml, Inno-TDS 5ml, MesoSculpt 1ml).

## Category 4 - PDO / lifting threads (built 2026-11-19)
171 codes, 209 listings. Threads match on brand + material (PDO / PLLA / PCL / PLGA) + thread type
(mono = skin quality, screw/twist = volume, cog/barbed = lifting, cone = suspension) + gauge + length +
needle/cannula + pack. Equivalence group = material + type. Code = BRAND-TYPE-GAUGE-LENGTH-[NEE/CAN]-PCS.
Material is stated in the listing name, so it is certain even where the manufacturer is not independently verified.
Only 7 codes have 2+ suppliers (price-comparable); the rest are single-supplier -> list only (per the list-everything principle).
Definisse/Silhouette are specified by length (cm) / cones, not gauge; slug-dropped decimals restored (316cm -> 31.6cm).
Recategorised out of threads: Definisse Core/Touch/Restore Filler -> Dermal filler, HydroBooster -> Skin booster,
Redensifying Cream / Eye Contour / Neutralizing Buffer / Rinnova Peel -> Skincare.

## Category 5 - Weight-loss medicines (built 2026-11-19)
45 codes, 226 listings. Licensed POMs (emc). Equivalence group = molecule:
- semaglutide (GLP-1): Wegovy (pen SC + oral tablets), Ozempic (pen, diabetes licence), Rybelsus (oral)
- tirzepatide (GLP-1/GIP): Mounjaro (KwikPen 2.5-15mg)
- dulaglutide: Trulicity | liraglutide: Saxenda, Victoza | orforglipron (oral GLP-1): Foundayo (confirm UK licence)
- orlistat (lipase inhibitor): Xenical, Orlistat, Alli | naltrexone+bupropion: Mysimba
Code = BRAND-STRENGTH-ROUTE (one presentation per strength). Strength snapped to each brand's licensed strengths,
fixing slug-dropped decimals ("125mg"->12.5, "2 4mg"->2.4). Wegovy snapped per route (pen vs oral strengths differ).
POM - price shown only to verified prescribers; diabetes-licensed brands (Ozempic, Victoza, Trulicity) flagged as off-label for weight.
Generic Church listings carry the dose in a Strength/Size field on the page, not the title - now read from the page (24 doses) so every listing maps to its exact code; no partials left. 1 MedFX blog article -> review.
Note: one Church "Wegovy 7.2mg pen" is not a standard strength - flagged for the supplier.
