# AestheticsProcure Master Product Taxonomy v1.0

Use this specification as the controlled classification contract. Process every source record; retain unresolved records. Return structured classification results using the JSON schema example in the companion file. Do not modify the taxonomy without approval.

## Approved hierarchy

### C01 — Dermal Fillers

- C01.01 — Hyaluronic Acid Fillers

  - C01.01.01 — Cross-linked HA Filler

- C01.02 — Non-HA Fillers

### C02 — Botulinum Toxins

- C02.01 — Botulinum Toxin Type A

- C02.02 — Botulinum Toxin Type B

### C03 — Skin Rejuvenation & Regeneration

- C03.01 — Skin Boosters

- C03.02 — Polynucleotides

- C03.03 — Collagen Biostimulators

- C03.04 — Exosomes

- C03.05 — Mesotherapy

- C03.06 — PRP & PRF

- C03.07 — Stem Cell-related Products

### C04 — Fat Dissolving & Body Contouring

- C04.01 — Fat Dissolvers

- C04.02 — Body Contouring Products

### C05 — Threads

- C05.01 — PDO Threads

- C05.02 — PLLA Threads

- C05.03 — PCL Threads

### C06 — Skincare & Chemical Peels

- C06.01 — Chemical Peels

- C06.02 — Cleansers

- C06.03 — Toners

- C06.04 — Serums

- C06.05 — Moisturisers

- C06.06 — Exfoliators

- C06.07 — Sun Protection

- C06.08 — Pre-Treatment Skincare

- C06.09 — Post-Treatment Skincare

### C07 — Hair & Scalp Treatments

- C07.01 — Hair Mesotherapy

- C07.02 — Hair Regeneration

- C07.03 — Scalp Treatments

- C07.04 — Hair Loss Products

### C08 — Medicines & Pharmaceuticals

- C08.01 — Anaesthetics

- C08.02 — Hyaluronidase

- C08.03 — Antibiotics

- C08.04 — Antivirals

- C08.05 — Analgesics

- C08.06 — Anti-inflammatory Medicines

- C08.07 — Steroids

- C08.08 — Sedation

- C08.09 — Emergency Medicines

- C08.10 — Diluents

### C09 — IV, IM & Wellness

- C09.01 — IV Therapy

- C09.02 — IM Therapy

- C09.03 — Vitamin Injections

- C09.04 — NAD+

- C09.05 — Supplements

- C09.06 — Wellness Products

- C09.07 — Weight Management

### C10 — Clinical Consumables

- C10.01 — Needles

- C10.02 — Syringes

- C10.03 — Cannulae

- C10.04 — Dressings & Swabs

- C10.05 — Couch Rolls

- C10.06 — Drapes

- C10.07 — Irrigation

- C10.08 — Sharps Disposal

- C10.09 — Safety Devices

- C10.10 — Facial Aesthetics Accessories

### C11 — Infection Control & PPE

- C11.01 — Gloves

- C11.02 — Face Masks

- C11.03 — Face Shields

- C11.04 — Gowns

- C11.05 — Disinfectants

- C11.06 — Sterilisation Products

### C12 — Devices & Equipment

- C12.01 — Microneedling Devices

- C12.02 — Needle Cartridges

- C12.03 — Plasma Pens

- C12.04 — Laser & IPL Devices

- C12.05 — Radiofrequency Devices

- C12.06 — Ultrasound Devices

- C12.07 — Diagnostic Equipment

- C12.08 — Clinic Equipment

### C13 — Surgical & Medical Supplies

- C13.01 — Scalpels

- C13.02 — Sutures & Skin Closures

- C13.03 — Haemostasis

- C13.04 — Post-operative Care

- C13.05 — Compression Garments

- C13.06 — Rhinoplasty Supplies

- C13.07 — Orthopaedic Supplies

- C13.08 — First Aid

### C14 — Beauty & Salon Supplies

- C14.01 — Semi-Permanent Makeup

- C14.02 — Nail Products

- C14.03 — Gel Polish

- C14.04 — Builder Gel

- C14.05 — Acrylics & Powders

- C14.06 — Nail Art

- C14.07 — Nail Tips

- C14.08 — Files & Buffers

- C14.09 — Beauty Tools

- C14.10 — Suncare & Tanning

## Classification rules

1. Use one primary category path per canonical product; additional navigation tags do not create duplicate products.

2. Use only approved IDs. Assign the deepest supported level; leave unknown levels null. Empty product_types arrays are reserved for future approval, not permission to invent types.

3. Classify using verified product identity, composition, intended use and official documentation; supplier category is evidence, not authoritative truth. Preserve original supplier labels and source URLs.

4. For overlaps prefer the specific verified product type: hair-specific mesotherapy goes to Hair Mesotherapy; botulinum toxins go to C02 even when prescription-only; hyaluronidase goes to C08. For unresolved overlaps use REVIEW_REQUIRED.

5. Treatment area (Lip, Face, Body) is a facet, not a primary category. Mono, Cog and Screw are thread design facets; PDO, PLLA and PCL are material categories.

6. Brand, manufacturer, dose, strength, volume, pack size, route, regulatory status, prescription requirements and professional eligibility are independent attributes. Never infer legal status from category.

7. Do not automatically overwrite canonical Product Truth with supplier data. Manufacturer or official documentation takes precedence. Keep field-level source, confidence and audit history.

8. Distinguish MANUFACTURER_STANDARD, SUPPLIER_SPLIT, SUPPLIER_BUNDLE and UNKNOWN. Require evidence or supplier confirmation for custom/split packs. Do not merge different variants or packs as identical offers.

9. Exclude unresolved or conflicting offers from automated cheapest and basket recommendations. Route conflicts to verification queue.

10. Do not force a classification or invent evidence. Preserve unmatched records and propose new categories separately for human approval.

11. Taxonomy includes future scope; inclusion does not imply supplier availability, UK authorisation or permission to sell.

12. Best Sellers, New Arrivals and Special Offers are collections; Training and Marketing are services, not product categories.

## Store navigation

- Dermal Fillers: C01

- Botulinum Toxins: C02

- Skin Boosters: C03.01

- Polynucleotides: C03.02

- Biostimulators: C03.03

- Exosomes: C03.04

- Mesotherapy: C03.05, C07.01

- Fat Dissolvers: C04.01

- Threads: C05

- Chemical Peels: C06.01

- Skincare: C06.02, C06.03, C06.04, C06.05, C06.06, C06.07, C06.08, C06.09

- Pharmacy: C08

- IV & Wellness: C09

- Consumables: C10

- Infection Control: C11

- Devices & Equipment: C12

- Surgical Supplies: C13

- Beauty & Salon: C14

## Output contract

Return one result per source record, including original supplier category, category IDs, evidence, confidence, status (CLASSIFIED or REVIEW_REQUIRED), reason and proposed category if needed. Classification alone does not establish recommendation eligibility. Report total input, classified and review-required counts; reconcile totals.

## Level 3

Only Cross-linked HA Filler is currently defined. All other Level 3 types require approval.