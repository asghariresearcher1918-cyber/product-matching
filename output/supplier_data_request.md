# Connecting to suppliers - what to ask each one

## How our system reads a supplier's products (best to worst)

| Option | What the supplier does | What we get | Effort for them |
|---|---|---|---|
| **A. Read-only API key** | WooCommerce: creates a *Read* REST API key (WooCommerce > Settings > Advanced > REST API). Shopify: creates a custom app with `read_products` (+ `read_inventory`). | All products, variants, SKUs, barcodes, trade prices and stock, refreshed automatically | ~10 minutes |
| **B. Product feed file** | Shares a CSV/XML link (many already have one for Google Shopping) or emails a spreadsheet each week | Same data, refreshed on their schedule | Low |
| **C. Trade login for us** | Gives us a trade account | We read prices behind login with our scraper | Low, but fragile for us |
| **D. Public pages only** | Nothing | What we have today: names, descriptions, images - no trade prices | None |

Columns we need in A or B: **supplier SKU, product name, barcode (GTIN/EAN), manufacturer code, pack size, trade price (ex/inc VAT), stock status, product URL**.
Barcode + manufacturer code let us match ~automatically; everything else is matched by our system, and whatever is left the supplier maps once in our portal.

## Supplier platforms (from our scrape)

| Supplier | Platform | Best option to ask for |
|---|---|---|
| Ask Pharmacy, Fox Pharma, Herts & Essex Supplies, Kiss Aesthetics Wholesale, LPG Clinics Wholesale, Skin On You, Smile Pharma, Wimpole Fillers | WooCommerce | A (Read REST API key) |
| MyPharmacyspace, Two Face Aesthetics, Healthxchange, IGO Aesthetics, AestheticSource | Shopify | A (custom app, read_products) |
| ACRE Pharmacy | Salesforce B2B Commerce | B (feed/export) |
| Church Pharmacy, John Bannon Pharmacy, Moda Pharmacy, Dr. Adams Pharmacy, Aesthetic Pharma, MedFX | Custom-built site | B (feed/export) or C |
| Refine Pharma, DermaFocus | (blocks automated access) | B or C |

## Email template (English)

> Subject: Listing your products on [SITE NAME] - product data access
>
> Hello [NAME],
>
> We are building [SITE NAME], a price-comparison service for UK aesthetic clinics and prescribers, and we would like to list your products with your trade prices.
>
> To keep your listings accurate and up to date, could you share your product data in one of these ways?
> 1. a **read-only** API key for your store (WooCommerce: Read REST API key / Shopify: custom app with read_products), or
> 2. a product feed or spreadsheet (CSV/XML) that you update regularly.
>
> The fields we need are: your SKU, product name, barcode (GTIN/EAN) if available, manufacturer code, pack size, trade price, stock status and product link. We never place orders or change anything in your store.
>
> Once connected, you will see each of your products matched to our master catalogue in a simple portal, where you can confirm the match or choose the right product in a few clicks.
>
> Kind regards,
> [NAME]
