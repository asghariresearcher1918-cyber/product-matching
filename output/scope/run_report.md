# Run report - toxins + fillers/skin boosters/biostimulators

## Scope

- In-scope rows (brand dictionary, recall-oriented): 3400 from 21 suppliers, 100 brands
- Pages scraped and extracted: 3240; errors: 160 (Refine Pharma: 122, Aesthetic Pharma: 14, Two Face Aesthetics: 10, Skin On You: 5, DermaFocus: 4, Kiss Aesthetics Wholesale: 3, Smile Pharma: 2)
- ACRE Pharmacy (365 rows) is a JavaScript (Salesforce) site: pages are being re-rendered with a browser; until then its text is empty.

## Step 1 - reference catalogue (catalogue/*.csv)

- Families: 173 - official 18, supplier_consensus 74, not_found 81
- Official: 8 toxins from 12 emc SmPCs (Botox 50/100/200, Bocouture 50/100, Azzalure, Alluzience, Dysport 300/500, Letybo, Nuceiva, Relfydess);
  Teosyal 10 lines from 21 Teoxane EU IFUs (fill volume from 'q.s. ad X mL', box contents, needles).
- Key finding: Teosyal RHA 3 officially exists as 2 x 1 mL (IFU 230511, 2024) AND 2 x 1.2 mL (IFU 230954, Oct 2025) - the pilot 'conflict' was two real presentations.
- Teosyal PureSense Deep Lines / Global Action / Ultimate / First Lines / Touch Up are not in Teoxane's current EU IFU list (possibly discontinued, unverified).
- Supplier consensus (lines defined, facts not official yet): Juvederm, Restylane, Belotero, Stylage, Revolax, Profhilo, Plinest/Newest, Jalupro, Seventy Hyal, Sunekos, Sculptra, Radiesse, Nucleofill, Lumi.
- Not reachable: Merz IFU portal (upstream error), Galderma IFUs found only for AU/CA/US, Allergan EU IFU not found, Vivacy IFU not found.

## Steps 2-4 on the 41-row sample

- See output/scope/results_sample.pdf and products_grouped.csv / review_queue.csv / non_products.csv.
- Step 3 for the sample was decided in-session (no API key), same rules and JSON schema as scripts/classify_llm.py; steps 2 and 4 ran as code.

## Cost estimate for the full step 3 (3,240 rows, claude-opus-5-5)

- ~2.9M text tokens + ~3,000 images; about $60 with the Batch API, about $120 with direct calls.
