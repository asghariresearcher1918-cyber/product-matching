# Basis — Handoff for Claude Code

Basis is a price-comparison and procurement site for UK aesthetic clinics (fillers, skin boosters, cannulas, needles/syringes, gloves, aftercare).
`basis-aesthetics-supplies.html` is a working **front-end prototype with hard-coded sample data**. Everything (suppliers, prices, reviews) in it is fake.

## Goal of this first session
1. Keep the prototype's UI and logic as the front end.
2. Load the real product list (the product file already in this repo) into a proper data store.
3. Serve it through a small API and make the front end read from it instead of the hard-coded `PRODUCTS` / `SUPPLIERS` objects.
4. Test that the loaded data is correct and that the existing flows still work.

Do NOT build supplier APIs, payments, auth or the quote engine yet. Only products, suppliers, offers, and the read API.

## Data model used by the prototype (match this, or migrate it deliberately)

All money is **integer pence**.

**Supplier**
- key, name
- delivery: flat fee in pence
- freeOver: basket value (pence) at that supplier above which delivery is free; `0` means always free
- pro: boolean. Professional-only suppliers are hidden until the user is verified
- speedDays, speed (label, e.g. "Next working day"), remoteExtraDays (extra days for remote postcodes)
- rating, reviewCount, reviews[] (author, text)

**Product**
- key, name, pack (e.g. "1 × 1ml"), category
- offers: map of supplierKey to a list of quantity tiers `{ min, price }`
  - price per unit applies when quantity >= min
  - example: `meridian: [{min:1, price:2000}, {min:10, price:1850}]`

Categories live in the prototype: Dermal Fillers, Skin Boosters, Cannulas, Needles & Syringes, Gloves, PPE & Aftercare.

## Business rules already implemented in the front end (keep behaviour)
- Line total = unit price for the matching tier x quantity.
- Delivery per supplier is charged once per supplier on that supplier's subtotal, unless subtotal >= freeOver.
- Basket optimiser: tries every assignment of basket items to eligible suppliers, scores product cost + delivery, and offers three priorities: cheapest, fewest suppliers, fastest. The user can override the supplier per item manually.
- "Smart savings" suggests quantity-tier jumps and supplier consolidation, with a "Why this option?" breakdown.
- Postcode check: remote-area prefixes (HS, ZE, KW, IV, PA, PH, BT, GY, JE, IM) add days to each supplier's estimate.
- Professional pricing is gated behind a verification flow (profession, regulator, registration number).
- Checkout splits the basket into one order per supplier.
- Compliance: **prescription-only medicines (e.g. botulinum toxin) must never show a public price.** Any product flagged POM is excluded from public listings.
- Views: home, results, product, basket, checkout, dashboard, suppliers.

## Planned later (context only, do not build now)
- Price refresh about every 2 hours, stock about every 1 hour, delivery rules at least daily. Event-driven sync for suppliers that offer API or webhooks.
- Bulk Quote Engine: for large or recurring orders (one-off, weekly, monthly), suppliers submit quotes through a supplier portal, quotes are valid for a limited time (e.g. 48h), and they feed back into the same optimiser.
- Per-clinic contract pricing based on purchase volume.
- Verified stock and supplier vetting, because competitors like PriceRunner are criticised for wrong stock and unreliable sellers.

## Suggested first prompt for Claude Code

> Read HANDOFF.md and the product file in this repo. First inspect the product file and tell me its format and any problems (missing prices, duplicate products, odd units, POM items). Then: (1) design a schema that matches the Product/Supplier/Offer model in HANDOFF.md, using SQLite for now; (2) write an import script that validates every row, converts prices to integer pence, and prints a report of what was imported and what was rejected and why; (3) add a read-only API (`GET /api/products`, `GET /api/products/:key`, `GET /api/suppliers`); (4) change `basis-aesthetics-supplies.html` to fetch from that API instead of the hard-coded objects, without changing the UI; (5) add tests for the import and for the delivery and tier calculations. Exclude POM products from public output. Run the app and tell me what to click to verify.

## How to verify after the run
- Imported product count equals the source file count minus the reported rejects.
- Open 5 random products and compare each tier price with the source file.
- Home, search, product page, basket, optimiser buttons and checkout all still work with API data.
- No prescription-only product appears in any public list or search result.
