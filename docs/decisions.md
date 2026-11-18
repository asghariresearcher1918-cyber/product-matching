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
