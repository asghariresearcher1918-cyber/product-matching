# Connecting a pharmacy's official feed to our catalogue

**Purpose.** When a pharmacy grants us official access (an API, a product/price feed, a
CSV/XML export, or a reseller data feed), this is the procedure to connect their live
products to the listings and reference products we already built — with **no re-matching
of products**. Read this together with `docs/product_identity.md` (how reference products
are defined) and `docs/site_handoff.md` (how the site consumes the data).

---

## 1. The model: two layers

The catalogue is deliberately built in two layers so that an official feed only ever
touches the cheap, refreshable layer:

| Layer | What it is | Changes when? |
|-------|-----------|----------------|
| **A — Reference product** | Our canonical product: taxonomy, name, brand, size, pack, `product_uid`. The hard, human-reviewed layer. | Built once. Stays stable. |
| **B — Listing (offer)** | One supplier's offer of that product: price, stock, image, delivery, URL, SKU. | Refreshed from the feed. |

An official feed **refreshes Layer B in place**. Layer A is not rebuilt. This is the whole
reason the integration is a *refresh*, not a *rebuild*.

---

## 2. The join table: `catalogue/final/crosswalk.csv`

This is the single authoritative table that links everything. One row per supplier listing.

```
listing_id      our internal id for this supplier's listing (e.g. R05860)
supplier        supplier name (e.g. "Dr. Adams Pharmacy")
url             the listing's canonical page URL   <- primary join key (100% coverage)
sku             the listing's SKU from structured data   <- secondary join key (~48%)
product_uid     the reference product this listing belongs to (e.g. FIL:revolax-deep-1x1.1ml)
catalogue_code  the per-category product code behind the uid
listing_title   the supplier's own product title (fallback / audit only)
```

Rebuild it any time with:

```bash
python -I scripts/build_crosswalk.py      # writes catalogue/final/crosswalk.csv
```

Coverage today: **URL 100% · SKU 48% · linked to a reference product 99%** of 11,311 listings.

---

## 3. The join procedure (per pharmacy)

Match each record in the pharmacy's feed to exactly one of **our** listings, in this order.
Stop at the first key that resolves.

1. **By URL (preferred, deterministic).**
   Normalise both sides (lowercase host, strip trailing slash, strip tracking query params,
   keep the product-id path/param) and match `feed.url == crosswalk.url`.
   Works for 100% of listings as long as the pharmacy's URLs are unchanged.

2. **By SKU (backup).**
   Match `feed.sku == crosswalk.sku` **within the same supplier** (SKUs are only unique per
   shop, never globally). Covers ~48% and rescues anything whose URL changed.

3. **By name (fallback, only when 1 and 2 both fail for that supplier).**
   Run the existing matcher `scripts/reference_match.py` on just that pharmacy's unmatched
   rows. This is the same engine that built the catalogue, so a feed with neither URL nor
   SKU is still handled — worst case we re-match **one** pharmacy, never the whole catalogue.

Once a feed record is matched to a `listing_id`, you already know its `product_uid` from the
crosswalk — so the feed's price / stock / image flows straight onto the product page we built.

### Pseudocode

```python
cross = load("catalogue/final/crosswalk.csv")          # listing_id, supplier, url, sku, product_uid
by_url = {norm(r.url): r for r in cross}
by_sku = {(r.supplier, r.sku): r for r in cross if r.sku}

for rec in pharmacy_feed:                               # one supplier's official feed
    hit = by_url.get(norm(rec.url)) \
       or by_sku.get((supplier, rec.sku))
    if hit:
        update_listing(hit.listing_id,                 # Layer B refresh, in place
                       price=rec.price, stock=rec.stock, image=rec.image)
    else:
        queue_for_name_match(rec)                       # -> reference_match.py, or "new product"
```

---

## 4. What the feed updates (Layer B fields)

Write these onto the listing; never silently alter Layer A from a feed.

- `price` (ex-VAT unit price; keep the feed's currency + VAT flag)
- `stock` / availability
- `image` (store the URL; thumbnails are rebuilt by `scripts/build_listing_thumbs.py`)
- `delivery` thresholds / cost, lead time — if the feed provides them

Prices for prescription-only (POM) items stay hidden to the public (MHRA/ASA). The `pom`
flag already lives on each reference product, so showing POM pricing to *verified*
clinicians is a **display toggle**, not a data rebuild.

---

## 5. Edge cases and how we handle them

| Situation | Handling |
|-----------|----------|
| Pharmacy re-platformed; URLs changed | Fall back to SKU; if SKU also changed, re-scrape once to rebuild the url↔sku bridge, then re-run crosswalk. |
| Feed keyed by internal ERP codes (no public URL/SKU) | Name-match that one feed with `reference_match.py`; add its code as a new join key column. |
| Feed has products not on the public site | New listings → normal pipeline → matcher assigns a `product_uid` (or creates a new reference product if genuinely new). |
| Same product, two feed rows (variants) | Each variant is its own listing; pack/size rules in `scripts/pack_size.py` keep them distinct. |
| Image endpoint-style URLs (e.g. `/api/media/fetch?id=N`, `/products/product-image/N`) | Supported — store the full URL; thumbnail builder fetches it. |
| Pharmacy serves one placeholder image for all products (e.g. Aesthetic Pharma today) | Do **not** import it (misleading); leave the category icon until real per-product photos exist. |

---

## 6. On-hold suppliers — do not connect

**Refine Pharma** and **DermaFocus** are on hold and must stay excluded. Do not scrape,
render, or connect them until they are formally activated. No anti-bot bypass, ever.

---

## 7. Checklist when a new feed arrives

1. Get the feed's format and which identifier(s) it carries (URL? SKU? ERP code?).
2. Ensure `crosswalk.csv` is current: `python -I scripts/build_crosswalk.py`.
3. Match feed → listings by URL, then SKU, then name (§3).
4. Refresh Layer B fields (§4). Rebuild thumbnails if images changed.
5. Rebuild the site data: `python -I scripts/patch_site_v2_data.py output/site/basis_live.html`.
6. Report match rate: `matched by URL / by SKU / by name / unmatched`. Investigate any
   supplier below ~95% matched before publishing.
