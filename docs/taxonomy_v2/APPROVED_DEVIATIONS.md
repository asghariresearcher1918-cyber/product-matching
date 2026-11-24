# AestheticsProcure taxonomy — owner-approved deviations & phase-1 scope

The controlled taxonomy is `data/taxonomy/AestheticsProcure_Taxonomy_v1.json` (C01–C14).
The owner approved the following deviations/decisions on 2026-11-24. Taxonomy is otherwise unchanged
(no category added, removed, merged or renamed without approval).

## Deviations (owner-approved)
1. **Weight-loss medicines = its own standalone top-level category** (NOT under C09.07 IV/Wellness).
   Implemented as a separate top-level `WLM — Weight Management` outside C01–C14. Reason: owner wants it
   fully separate ("یه دسته جداگانه باشه اصلا"). Recorded here for taxonomy governance.

## Phase-1 scope
2. **Vaccines** — data is preserved but **parked** (status `PARKED`, not shown in phase-1 catalogue).
   To be added in a later phase (owner: "تو فاز اول در نظر نگیر و ذخیره کن").
3. **Hair & scalp products** move out of the old "Skincare, haircare & peels" into **C07 Hair & Scalp Treatments**.
4. **Level 3 (product_type)**: only `C01.01.01 Cross-linked HA Filler` is defined. All other level-3 types are
   left null until approved (taxonomy rule 2 / "Level 3" section).

## Versioning
- v1 (the previous 15-category model) is frozen at git tag `catalogue-v1` (commit 9b74f9e) and the site copy
  `output/site/basis_v1_15cat.html`. v2 outputs are kept separate so the two models never borrow from each other
  and either can be restored.

## Migration approach
- Bulk map: every product's **current category + equivalence group** → a primary C-id (and subcategory where the
  evidence is clear). Supplier category is preserved. Ambiguous → `REVIEW_REQUIRED` with a reason (never guessed,
  never deleted).
- Then category-by-category deep verification (names/listings/subcategories), same method as the biostimulator pass.
