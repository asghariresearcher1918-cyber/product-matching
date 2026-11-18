# Product identity and syncing with suppliers

Our catalogue code (e.g. TEOSYAL-PURESENSE-KISS-L-2X1ML) is an internal, human-readable master key.
It never changes, so supplier links and price history stay attached to it.

Each code also stores every official identifier we can find (cross-references):
- GTIN / EAN barcode (GS1) - the pack barcode; best single key across suppliers.
- dm+d (NHS Dictionary of medicines and devices) AMPP / VMPP IDs - medicines (free via NHS TRUD).
- PIP code - 7-digit UK pharmacy wholesale code (medicines, many consumables).
- UDI-DI / manufacturer reference - medical devices such as fillers.
- Supplier SKU - per supplier, kept in a mapping table.

Matching a supplier product to a code (in order):
1. Exact identifier: GTIN, PIP or dm+d.
2. Known mapping: the supplier SKU was mapped before (by us or by the supplier in the portal).
3. Attribute match: brand + line + strength + lidocaine + market + units x volume (deterministic rules + AI).
4. Human review / supplier chooses the code in the portal; new code requested if none fits.

Finding (2026-11-18): only 74 of ~11,000 public product pages show a barcode (Kiss Aesthetics 64,
AestheticSource 10). Supplier feeds / APIs (e.g. Shopify and WooCommerce have barcode fields) are the
place to ask for GTIN / PIP; ask for them in the supplier data request.
