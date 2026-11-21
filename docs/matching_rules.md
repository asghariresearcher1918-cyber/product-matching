# Catalogue rules — full specification (every detail)

The exact logic the pipeline runs, step by step, with the real constants. Pipeline order:
`cleanup_categories.py → categorize_all.py → apply_scope.py → <category>_catalogue.py (×all) →
build_*_reference.py → reference_match.py → master_catalogue.py → canonical_names.py → master_catalogue.py →
auto_consolidate.py → full_export.py / category_export.py → build_site.py`.
(master runs twice: first to produce the listing index that canonical_names needs, then again to apply the names.)

---

## A. CATEGORY — which bucket a listing lands in

### A1. Signals (`categorize_all.py`, `classify()`)
Each listing is read from its scraped page (`pages.jsonl`) and votes are collected:
- **S1 supplier category** (breadcrumb / WooCommerce `product_cat` / Shopify type / URL path / a "Category" field) — strongest.
- **S1b vendor / brand name** from the supplier category vendor field or page title.
- **S2 page title** — matched against ordered keyword rules (most specific first).
- **S3 brand dictionary** (`data/brands_scope.csv`) — known brand → category.
- **S4 legal / medicine fields** on the page (Legal Category: POM / P / GSL / MD, Medicine Type…).
- **S5 description** (weaker). **S6 listing title** (weakest, last resort).
- Confidence: **high** = ≥2 independent strong signals agree with no strong conflict; **medium** = one strong signal;
  **low** = weak/conflicting (goes to the manual review list).

### A2. The 20 categories
Toxin · Dermal filler · Skin booster / polynucleotide / mesotherapy · Biostimulator · Fat dissolving ·
Vitamin & IV therapy · Weight-loss medicine · Medicine – injectable/anaesthetic/emergency · Medicine – oral ·
Medicine – topical/eye/other · Vaccine · Needles, cannulas & syringes · Clinic consumables & PPE · Devices & equipment ·
Skincare, haircare & peels · Supplements · Beauty (nails, brows, lashes, PMU, makeup) · Training/services · Not a product.

### A3. Manual category overrides
`data/category_overrides.csv` (`id,category,note`) — applied first inside `classify()`, beats every signal.
`cleanup_categories.py` generates these by pattern (idempotent) for known mistakes, e.g.
Profhilo Haenkenium/Figura/Pura → Skincare; licensed POM topicals (Emla, Fucidin, Betnovate, Hydrocortisone, Differin,
Rozex, Skinoren, aciclovir — but NOT cosmeceutical azelaic brands like Noon) → Medicine; EpiPen/Lignospan → Medicine.

### A4. Scope (`apply_scope.py` + `data/medicine_scope.py` + `data/scope_overrides.csv`)
Per category, regex rules map a row to an action → scope label:
`keep→Phase 1`, `phase2→Phase 2 - later`, `remove→Removed - general pharmacy`, `salon→Later phase - nail & facial salons`,
`move:<cat>` moves the category. Per-id overrides in `data/scope_overrides.csv` win last (used to scope out
contraceptives, home test kits, respiratory, x-ray, air purifiers, general-pharmacy injectables Praluent/Xolair/Genotropin).
Suppliers Refine Pharma & DermaFocus → "On hold - supplier not connected". **Only `Phase 1` rows appear on the site.**

---

## B. PRODUCT — grouping listings into one product

### B1. Method A — reference-matched (reliable). `reference_match.py` + `data/reference/*.csv`
Runs for categories: **filler, booster, skincare, toxin, fat** (each with its own reference file). For each listing:

1. **Brand detection** (in this order):
   a. `\b<brand>\b` in the lower-cased title;
   b. if none, **squashed** match: `<brand>` with spaces/punctuation removed is a substring of the squashed title
      (so `LipoLab` matches `Lipo Lab`, `Deso body` matches `DesoBody`);
   c. if none, the listing's existing parsed brand if it is a reference brand.
   No reference brand found → **passthrough** (keeps the Method-B code, untouched).
2. **Exclusions** (checked before matching):
   - **Accessory** regex → `review-accessory`, not a product:
     `roller banner | banner | poster | sticker | lanyard | t-shirt | brochure | leaflet | display stand | shelf`.
   - **Bundle** regex → `review-bundle`:
     `free | get 1 | get one | + 1 x | buy 1 get | bundle | worth £ | multibuy`.
3. **Pick the product**: among that brand's reference rows, the one whose **longest alias** is a substring of the title;
   if no alias matches, the brand's row flagged `default`; if neither → `review-nomatch`.
4. **Lidocaine**: reference `lidocaine` = `yes`→yes, `no`→no, `detect`→ true iff the title has
   `lidocaine | +lido | lido | with lido`.
5. **Pack count** (how many vials/syringes) — owner reading rule, in order, first hit wins:
   **title → whole product page (`page_text`) → image OCR (`image_text`) → else assume reference base (marked "assumed")**.
   The `decision` column records the source: `(title)`, `(page)`, `(image(OCR))`, `(assumed (not stated))`, `(reference (kit))`.
   - Pack patterns, STRICT (used on page/image to avoid false hits):
     `box of N`, `pack of N`, `N x <num>ml` (e.g. 10 x 8ml / 10x8ml), `<num>ml x N` (8ml x 10 / 10mlx8), `N vials/pcs/pieces/syringes`.
     LOOSE (title only): also `xN`, `Nx`. Accepted only when `1 ≤ N ≤ 60`.
   - A product whose name contains **"Kit"** takes its pack from the reference (a kit is a fixed bundle), ignoring the title.
6. **Size / units / active agent** always come from the **reference** (fixes decimal errors): filler volume, toxin
   units + unit_type (+ ml/vial for liquid toxins Relfydess 1.5ml, Alluzience 0.625ml), fat active agent + vial ml.
7. **Market variant**: `hologram | ROI | Irish/Ireland` is **folded into the base product** (no separate code).
8. **Code** = `TAG-BRAND-LINE[-LIDO][-NX]` (TAG per category). One product per (brand, line, pack count, ±lidocaine).

### B2. Method B — parsed (non-reference brands). `<category>_catalogue.py`
Brand + line + spec parsed from the title and the page (`page_facts`: full page text across all tabs, then image OCR).
Noise stripped; decimal fixes applied (see D). These produce the codes until a reference is built for the brand.

### B3. Cross-product safe merge. `auto_consolidate.py`
Only in branded categories (Toxin, Filler, Booster, Biostimulator, Fat, PDO threads, Skincare, Beauty, Supplements,
Weight-loss). Groups products by `(category, brand, normalised spec)` and merges two products **only when their cleaned
core-name token sets are IDENTICAL** (equal, not subset). Keeps distinct products apart:
- single-digit identifiers are **kept** (RHA 2 ≠ RHA 3, Vol 1 ≠ Vol 2);
- gauge/mm/mg kept (30G ≠ 29G); only ml and `xN` pack tokens are stripped from the core.
Supplier and listing counts are recomputed from the listing index (a merge never double-counts).

### B4. Pack size = separate product
Different pack counts of the same product are **separate codes** (1 vial vs 10 vials; 1×1ml vs 2×1ml), so
price-per-unit is comparable. Hologram/ROI and single-vs-twin are NOT separate for name, but twin IS a separate pack SKU.

---

## C. NAME shown in the list (title)

Priority in `master_catalogue.py` (later overrides earlier):
1. parsed name (Method B) — `brand + line/variant`;
2. **canonical name** (best-pharmacy title, see C2) overrides it;
3. **reference name** overrides both for reference-matched rows, and sets `verified = reference-matched`.

**Complete one-line title:**
- reference-matched → name **+ presentation in brackets**, e.g. `Juvederm Ultra 4 (2 x 1ml with lidocaine)`,
  `Botox 100 units (1 vial)`, `Relfydess 150 units (1 x 1.5ml vial)`, `Aqualyx (10 x 8ml vials)`.
- non-reference → the pharmacy's own title is kept **as-is** (it already contains size/pack), nothing appended,
  so we never duplicate the size.

### C1. Noise stripped from any title (`canonical_names.clean()`)
HTML entities decoded (`&amp;`→`&`); ® ™ © removed; parenthetical **notes** dropped when they contain no digit
(keep `(1 x 2ml)`, drop `(Discontinued)`, `(Medic Only)`); leading `Single ` removed. Phrases removed:
`appropriate training recommended/required · stock item · prescription item · vat payable · zero/no/pay/incl/ex/inc/plus vat ·
available on request · out of/in stock · best seller · new in · brand new · online(/exclusive) · special offer · clearance ·
short dated · free delivery · next day · buy(/now/online) · shop now · uk stock · genuine · authentic · official`, and
note patterns `exp/expiry <date> · discontinued · previously… · medic(s) only · while stocks last · limited stock ·
new packaging · new formula`. Lower-case words are Title-cased; tokens like `H+L, RHA, CE, PDO, PLLA, PCL, CaHA, PDRN, PN,
IU, PFS, SPF, ROI, EU, UK, HA, LED, RF, IPL, DNA, NCTF` kept as-is; units (2ml, 25g, 1x2ml) kept lower.

### C2. Title source for non-reference products (`canonical_names.py`)
- **Per-category pharmacy ranking**, computed automatically from the data: for each `(category, pharmacy)` a score =
  mean over its titles of `(1 if title has a size) + (1 if title has a pack) − 1.5 if title has noise`. Size regex =
  `\d+(ml|mg|mcg|g|%|iu)`; pack regex = `N x N | pack/box of | xN | single | double | kit | vials | syringes`;
  noise regex = `stock item | vat | prescription item | out of stock | appropriate training | available on request`.
- For a product, the chosen title = from the **highest-scoring pharmacy that stocks it**, tie-broken by the longest
  cleaned title (most complete). Single-supplier product → that supplier's title.
- The full ranking is written to `catalogue/final/title_source_priority.csv` for review.

---

## D. SIZE / PACK formatting & decimal fixes
- Market format (`master_catalogue.py`): `_packspec` → `N x Vml[ with lidocaine]`; `_vials` → `N x Vml vial(s)` for toxin/fat
  (powder toxins just `1 vial`); `_mkt` drops the meaningless `UK/std` market tag (keeps HG / ROI only).
- Decimal duplicates merged in booster & filler: `1 == 1.0`; decimal-loss twin `35→3.5, 15→1.5, 10→1.0` merged **only
  when the decimal twin already exists** for the same brand+line+pack(+lido+market).
- Display field label on the product page = **"Pack size"** (not "Spec").

## E. EQUIVALENCE GROUP (alternatives shown together)
Toxin → molecule / "Botulinum toxin type A"; Filler → brand; Booster → active class
(Polynucleotide/PDRN · HA bio-remodelling · Amino-acid · Mesotherapy cocktail · Exosome · PRP); Fat → active agent
(Deoxycholic acid · Phosphatidylcholine · Lecithin/proprietary · Mesotherapy lipolytic); Medicine → molecule;
Skincare → function (Peel/SPF/Retinoid/Vitamin C/Cleanser/Serum/Moisturiser/Eye/Mask/…); Needles → subtype; Devices → modality.
Same molecule/agent, different brand = separate code, same group → shown together as alternatives.

## F. COMMODITY categories (spec-based, brand = attribute)
Needles/cannulas/syringes and consumables/PPE: the code is the **spec** (subtype + gauge + length, or volume + luer, or
material + size for gloves), and the **brand is a filterable attribute** — the same spec from any manufacturer compares
together (e.g. 30G 13mm needle from 12 suppliers = one code). Medicines group by **active molecule** (generics
interchangeable, manufacturer an attribute); branded drugs mapped to their molecule (Kenalog→triamcinolone, etc.).

## G. LEGAL / POM
POM categories = **Toxin, Medicines (all), Weight-loss medicine, Vaccine**. On the site these products are **shown**
(name + details) but the **price is masked** (`🔒 Login`) until the user is verified; after verify the price shows.

## H. COMPARISON mode
Product stocked by **>1 pharmacy** → price comparison (per-unit). Single pharmacy → listed only.

## I. CONFIDENCE / verified flags
`reference-matched` = mapped to an authoritative brand reference (highest trust). Method-B rows carry the catalogue's own
tier (high / high* brand-unverified / rule / partial / review). The reference `source` column links to the authority
(emc SmPC, manufacturer / UK distributor page).

## J. Reference coverage so far (`data/reference/`)
- **Toxin**: all 9 brands (emc/SmPC) — Botox, Azzalure, Dysport, Bocouture, Xeomin, Alluzience, Letybo, Nuceiva, Relfydess.
- **Filler**: Juvederm, Teosyal, Restylane, Belotero, Revolax, Stylage, Aessoa.
- **Booster**: Profhilo, Sunekos, Nucleofill, Jalupro, Seventy Hyal.
- **Fat dissolving**: Aqualyx, Lemon Bottle, Lipo Lab, Deso(Face/Body), Kabelline, Dr. Lipo, Alidya, BCN Adipo, Cincelar,
  Mesoestetic, MesoSculpt, Inno-TDS, Pine/Skinny Bottle.
- **Skincare**: Profhilo topical range (Haenkenium, Figura, Pura).
Everything else is still Method B (pharmacy title) until its reference is built — this is the remaining work, done
category by category.

## K. Per-category review output
`scripts/category_export.py "<Category>"` → workbook with a **Products** tab and a **Listings-per-product** tab
(each product → its pharmacies + clickable listing links). Produced whenever a category is finished.
