# Catalogue rules — how products are categorised, named, grouped and displayed

This is the agreed logic the pipeline follows. Scripts referenced live in `scripts/`.

## 1. Which CATEGORY a listing goes in
1. **Automatic** (`categorize_all.py`): each supplier listing is voted into one of the categories by independent signals —
   supplier's own breadcrumb/category, the product-page title, a brand dictionary, legal/medicine fields (POM/P/GSL/MD),
   and the description. ≥2 signals agreeing = high confidence.
2. **Manual overrides** (`data/category_overrides.csv`, `id,category,note`) win over the automatic result.
3. **Scope** (`apply_scope.py` + `data/medicine_scope.py` + `data/scope_overrides.csv`): each row is marked Phase 1,
   Phase 2, Removed (general pharmacy / not a product), or On-hold (supplier not connected). Only **Phase 1** is in the live site.
4. **Cleanup pass** (`cleanup_categories.py`): re-files clear mistakes (e.g. Profhilo Haenkenium/Figura/Pura → Skincare;
   IUDs, respiratory, injectable medicines out of Devices).

## 2. How a PRODUCT is formed inside a category (grouping listings)
Two methods, in order of preference:

**A. Reference-matched brands (the reliable method).** Where we have an authoritative brand reference
(`data/reference/*.csv`), every listing is mapped to a real reference product:
- detect the brand in the title (space/punctuation tolerant: `LipoLab` = `Lipo Lab`);
- pick the product by the **longest matching alias** (variant / unit size), else the brand's default;
- **name, size, active agent/units come from the reference**;
- **pack count** (how many vials/syringes) is read in this order (owner rule):
  **title → whole product page → image OCR → only then assume** (marked "assumed (not stated)");
- hologram / UK&ROI packaging is **folded into the base product** (not a separate code);
- promo bundles ("buy 3 get 1 free") and marketing/accessories (banner, poster) are **flagged out, not products**.
One product code per (brand, product line, pack size, ± lidocaine).

**B. Non-reference brands (parsed).** The category script parses brand + line + spec from the title (and the page via
`page_facts`), then `auto_consolidate.py` merges codes of the **same brand + same spec whose cleaned core name is
identical** (safe, conservative; never merges different products like RHA 2 vs RHA 3).

Different PACK SIZES of the same product stay **separate products** (1 vial vs 10 vials) so price-per-unit is comparable.

## 3. EQUIVALENCE GROUP (products shown together as alternatives)
Each category groups by its natural axis, so alternative brands appear together in search/suggestions:
- Toxin → molecule ("Botulinum toxin type A") · Filler → brand · Booster → active class · Fat dissolving → active agent
- Medicine → molecule · Skincare → function · Needles → subtype · Devices → modality.
Same active agent/molecule, different brand = separate code but linked in the group.

## 4. PRODUCT NAME shown in the list (title)
Priority:
1. **Reference-matched** → our standard name + presentation, one line, e.g.
   `Juvederm Ultra 4 (2 x 1ml with lidocaine)`, `Botox 100 units (1 vial)`, `Aqualyx (10 x 8ml vials)`.
2. **Non-reference, multi-pharmacy** → the title from the **best pharmacy for that category**. Each category ranks its
   pharmacies automatically by title quality (how often titles carry size + pack, penalising noise) —
   see `catalogue/final/title_source_priority.csv`. The best pharmacy that stocks the product supplies the title.
3. **Non-reference, single-pharmacy** → that pharmacy's own title.
In all cases supplier noise is stripped (VAT, stock item, prescription item, training, EXP dates, discontinued, HTML
entities). The title is **complete on one line** — no size/pack hidden in a sub-label.

## 5. Where the REFERENCE NAME comes from
From manufacturer / official UK sources, compiled per brand into `data/reference/`:
- `toxins.csv` (emc / SmPC), `fillers.csv`, `boosters.csv`, `fat.csv`, `skincare.csv`, `profhilo.csv`, `juvederm.csv`.
Each row = real commercial name, pack/size, active agent or units, aliases (how suppliers write it), and a source link.
Reference-made brands so far: toxins (all), fillers (Juvederm, Teosyal, Restylane, Belotero, Revolax, Stylage, Aessoa),
boosters (Profhilo, Sunekos, Nucleofill, Jalupro, Seventy Hyal), fat dissolving (all main brands), Profhilo skincare.
The rest are still name-from-pharmacy (method B) until their reference is built.

## 6. PACK SIZE / presentation
Market format: `2 x 1ml with lidocaine`, `10 x 8ml vials`, `1 x 1.5ml vial` (liquid toxins show ml/vial; powder toxins
reconstitute on use so just `1 vial`), `Box of 100`, `25G 50mm`. Shown as part of the title and in the "Pack size" field.

## 7. LEGAL / POM
Prescription-only categories (toxin, medicines, weight-loss, vaccine) are **shown** publicly (name + details) but their
**price is hidden** behind "Login / verify" until the professional is verified.

## 8. COMPARISON
A product stocked by **more than one pharmacy** → price comparison (Compare). A single-pharmacy product → listed only.

## 9. Per-category review output
When a category is finished: `scripts/category_export.py "<Category>"` writes a workbook with a **Products** tab and a
**Listings-per-product** tab (each product → the pharmacies and their clickable listing links).
