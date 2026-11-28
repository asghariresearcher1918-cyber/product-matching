# How a product is read — exact current behaviour

The single source of the reading rules is `scripts/read_rules.py` (pack + size) on top of `scripts/page_facts.py`
(what part of the page is read) and `scripts/pack_size.py` (name parsing). This file documents exactly what the code
does today, with no omissions, so the owner can confirm or correct each step.

## 1. Where on the page is read
Source: the product's own cached HTML — `cache/<pharmacy>/<id>.rendered.html` if present, else `cache/<pharmacy>/<id>.html`.
- **`page_text(id)`** — strips `script/style/noscript/svg`, takes ALL text of ALL tabs (Description, Additional
  information, Size & Care, Box contents, Product details / SKU, Product options). It starts near the first
  "Description / Overview" and is **cut at the first related-products block** ("You may also like", "Related products",
  "Bestsellers", "Recommended products", etc.) so another product's facts never leak in.
- **`labelled_fields(text)`** — "Label: value" pairs for these labels only: `size and care info, box contents,
  pack contents, contents, pack size, size, product options, quantity, qty, presentation, sku, product code,
  quickfind code` (value truncated to 60 chars).
- **`image_text(id)`** — OCR of every product image (all angles), read from `<id>.img.N.*.ocr.txt` sidecars.
  **Gap: OCR sidecars exist only for ~39% of images (the OCR job was stopped), so this layer is partial.**

## 2–3. What is recorded / stored
- Per listing (`catalogue/final/*_listing_map.csv`): id, supplier, original title, url, brand, internal code,
  size/spec, pack, prescription, price, image url.
- Per reference product (`catalogue/final/master_catalogue.csv`): uid, category, equivalence group, brand,
  display name (`product`), `key_spec` (volume/strength), `pack`, manufacturer, price, source.
- Helpers: `canonical_names.csv` (display name), `structured.csv` (from JSON-LD: name, image, SKU, MPN, GTIN, price,
  availability), `listing_images.csv`, `listing_thumbs.json`, `crosswalk.csv` (join table).

## 4. What is ignored in the name
Two different names exist:
- **Display name** (shown on site/Excel): from `canonical_names` = the pharmacy's real title, kept as-is; only
  "Buy", the shop-name suffix and "(Size - 1)" noise are removed. **Nothing else is dropped.**
- **`namecore`** (only to build the grouping CODE): deliberately simplified for matching — removes `®™©`,
  parenthesis contents, size units (`ml, l, g, cm, mm, N x, ply, pack, box`), all punctuation, NOISE words
  (`the, with, for, buy, uk, new, disposable, sterile, non, box, pack, of, ml, x, each, per, ce, pcs, clinic,
  medical, professional, stock, item, vat, prescription, training, required, free, single, use, ply, colour, size,
  ltd, quality, value`), brand words, and keeps only the first 4 significant words. A distinguishing number dropped
  here is what merged the scalpel blades (fixed with `blade_spec`).

## 5. How the text under the name is read (owner rule order)
- **PACK** (`read_rules.read_pack`): 1) NAME → 2) labelled Size/Pack/Quantity field → 3) an explicit statement in the
  description ("pack contains N", "quantity: N", "N x <unit>", "box of N") → 4) image OCR. If none: blank (never guessed).
- **SIZE** (`read_rules.read_size`): NAME → labelled Size/Strength/Volume field → page text.
- NAME parsing details (`pack_size.qty_from_name`): a count in parentheses beats a model number; explicit pack
  markers ("pack of N", "x N") beat a bare "N caps" (a strength); explicit single ("single mask", "x1", "1 vial",
  "pack of 1") = 1; "single use/dose/patient/application" is NOT a count.

## 6. How product info is extracted from the page
Cached HTML → strip script/style → full text → cut the related block → regex for labelled fields + pack/size phrases
+ `structured.py` reads Schema.org JSON-LD (name, image, SKU, MPN, GTIN, price, availability) + image-url extraction
(payment/logo icons filtered out) + OCR.

## 7. What goes into the Excel
- **Products tab**: Product | Taxonomy (primary › sub) | Brand | Volume | Qty / pack | Prescription | Suppliers |
  Listings | Public price | Name reference (name source) | Product link.
- **Listings per product tab**: Product | Pharmacy | Listing title | Qty / pack | SKU / product code |
  Commercial code | Prescription | Public price | Product link | Match confidence | Name reference | Image.
- **For your review tab**: Product | Equivalence / subcategory | Why flagged | Brand | Suppliers | Listings.

## Known gaps (honest)
- OCR layer only ~39% populated.
- `page_text` cut relies on recognising the "related products" heading; an unusual shop layout could cut early or
  leak. - Historically each category catalogue had its own pack logic; `read_rules.py` unifies it, now wired into
  `build_site_v2`, to be applied to every category and the Excel export.
