# Run report - PILOT

Scope: 67 pilot rows (pilot_ids.txt), 10 suppliers.

## Counts

rows 67 -> classified 59 -> families 13 -> variants 24 -> packs 33

| confidence | rows |
|---|---|
| likely | 28 |
| uncertain | 26 |
| confirmed | 13 |

Errors: 8 (Refine Pharma: 4, Aesthetic Pharma: 4)

| id | supplier | error |
|---|---|---|
| N00630 | Refine Pharma | RemoteProtocolError: Server disconnected without sending a response. |
| N00756 | Refine Pharma | RemoteProtocolError: Server disconnected without sending a response. |
| N00814 | Refine Pharma | RemoteProtocolError: Server disconnected without sending a response. |
| N00942 | Refine Pharma | RemoteProtocolError: Server disconnected without sending a response. |
| R05695 | Aesthetic Pharma | extract: redirected to listing page https://www.aestheticpharma.co.uk/all-products (product removed or login-o |
| R05706 | Aesthetic Pharma | extract: redirected to listing page https://www.aestheticpharma.co.uk/all-products (product removed or login-o |
| R05841 | Aesthetic Pharma | extract: redirected to listing page https://www.aestheticpharma.co.uk/all-products (product removed or login-o |
| R05924 | Aesthetic Pharma | extract: redirected to listing page https://www.aestheticpharma.co.uk/all-products (product removed or login-o |

Reference status: found: 8, not_found: 4, partial: 3

## Families -> variants -> packs

### F-ACICLOVIR-200 - Aciclovir 200 mg oral (3 rows, 3 suppliers)
- **200 mg / dispersible tablet / oral**
  - 25 tablets: R00032 MedFX (confirmed), R10386 Ask Pharmacy (uncertain)
- **200 mg / tablet / oral**
  - 25 tablets: R03302 Fox Pharma (confirmed)

### F-AZZALURE - Azzalure (2 rows, 2 suppliers)
- **125 Speywood units**
  - 1 vial: R03112 Fox Pharma (confirmed)
- **strength?**
  - vial count not stated: R04484 John Bannon Pharmacy (uncertain)

### F-BD-MICROLANCE3 - BD Microlance 3 needle (3 rows, 3 suppliers)
- **30G x 13 mm**
  - 100 per pack: R00048 MedFX (likely), R03015 Fox Pharma (likely), R04510 John Bannon Pharmacy (likely)

### F-BOCOUTURE - BOCOUTURE (2 rows, 2 suppliers)
- **100 units**
  - 2 vials: R00653 Church Pharmacy (confirmed), R03165 Fox Pharma (confirmed)

### F-BOTOX - BOTOX (4 rows, 4 suppliers)
- **100 Allergan Units**
  - 1 vial: R00666 Church Pharmacy (confirmed), R03166 Fox Pharma (likely), R04537 John Bannon Pharmacy (confirmed), R05521 Moda Pharmacy (confirmed)

### F-JUVEDERM-ULTRA - Juvederm Ultra (9 rows, 6 suppliers)
- **Ultra 2 / lidocaine**
  - 2 x 0.55 ml syringe: R03239 Fox Pharma (likely)
- **Ultra 3 / lidocaine**
  - 1 x 1 ml syringe: R01417 Church Pharmacy (likely)
  - 2 x 1 ml syringe: R01416 Church Pharmacy (likely), R05559 Moda Pharmacy (likely), R06864 Skin On You (likely)
- **Ultra 3 / lidocaine not stated**
  - 1 x 1 ml syringe: R03245 Fox Pharma (likely), R10156 Ask Pharmacy (likely)
  - 2 x 1 ml syringe: R03238 Fox Pharma (likely), R04891 John Bannon Pharmacy (likely)

### F-PABRINEX - Pabrinex (Vitamins B & C high potency) (12 rows, 6 suppliers)
- **conflict / B+C high potency / UK**
  - 1 single ampoule 2 ml: R10470 Ask Pharmacy (uncertain)
  - 10 pairs of 5 ml and 2 ml ampoules (from image only): R06961 Skin On You (uncertain)
- **IM / B+C high potency / UK**
  - 1 single ampoule 2 ml: R10321 Ask Pharmacy (uncertain)
  - 10 pairs (5 ml + 2 ml): R01860 Church Pharmacy (uncertain), R05599 Moda Pharmacy (uncertain), R10427 Ask Pharmacy (uncertain)
  - 10 pairs of 5 ml and 2 ml ampoules (from image only): R03026 Fox Pharma (uncertain)
- **IV / B+C high potency / UK**
  - 6 pairs (5 ml + 5 ml): R01861 Church Pharmacy (confirmed), R05600 Moda Pharmacy (confirmed), R07603 MyPharmacyspace (confirmed)
  - 6 pairs of 5 ml ampoules (from image only): R03027 Fox Pharma (likely), R06981 Skin On You (uncertain)

### F-PROFHILO - Profhilo (6 rows, 3 suppliers)
- **H+L / no lidocaine**
  - 1 x 2 ml syringe: R03087 Fox Pharma (likely), R03093 Fox Pharma (likely), R05159 John Bannon Pharmacy (likely), R05729 Aesthetic Pharma (likely)
- **Structura / no lidocaine**
  - 1 x 2 ml syringe: R03344 Fox Pharma (likely), R05164 John Bannon Pharmacy (likely)

### F-TEOSYAL - Teosyal (8 rows, 6 suppliers)
- **Redensity 1 / lidocaine**
  - 2 x 1 ml syringe: R02579 Church Pharmacy (likely), R03254 Fox Pharma (likely)
- **Redensity 2 / lidocaine**
  - 2 x 1 ml syringe: R10112 Ask Pharmacy (likely)
- **RHA 3 / lidocaine**
  - 2 x 1.2 ml syringe: R02596 Church Pharmacy (uncertain), R06940 Skin On You (uncertain)
  - 2 x 1 ml syringe: R05672 Moda Pharmacy (uncertain)
- **RHA 3 / lidocaine not stated**
  - 1 x 1 ml syringe: R10281 Ask Pharmacy (uncertain)
  - 2 x 1.2 ml syringe: R05319 John Bannon Pharmacy (uncertain)

### F-TSK-STERIGLIDE - TSK STERiGLIDE cannula (5 rows, 3 suppliers)
- **25G x 38 mm**
  - 20 per pack: R00186 MedFX (likely), R02721 Church Pharmacy (likely)
  - 4 per pack: R05379 John Bannon Pharmacy (likely)
- **27G x 50 mm**
  - 20 per pack: R00183 MedFX (likely), R02718 Church Pharmacy (likely)

### F-VITBC-DEMO - Vitamins B+C IV High Potency (DEMO S.A. pack) (2 rows, 2 suppliers)
- **IV / B+C high potency / non-UK pack (DEMO S.A.)**
  - 6 pairs (5 ml + 5 ml): R03210 Fox Pharma (uncertain), R10511 Ask Pharmacy (uncertain)

### F-VITBC-UNRESOLVED - Vitamins B+C IV (licence holder unresolved) (1 rows, 1 suppliers)
- **IV / B+C high potency / UK**
  - 6 pairs (5 ml + 5 ml): R05425 John Bannon Pharmacy (uncertain)

### F-WEGOVY-TAB - Wegovy tablets (2 rows, 2 suppliers)
- **4 mg / tablet / oral**
  - 30 tablets: R03203 Fox Pharma (confirmed), R05438 John Bannon Pharmacy (confirmed)

## Top conflicts

- R01860 Church Pharmacy "pabrinex intramuscular im high potency injection": Pabrinex IM has no current emc SmPC (reference not_found; discontinuation unverified)
- R03026 Fox Pharma "Pabrinex I/M": pack size only visible in the image; Pabrinex IM has no current emc SmPC (reference not_found; discontinuation unverified)
- R03210 Fox Pharma "Vitamins B + C IV High Potency Conc Sol For Inf 5ml 6x2 (Exp.31/01/2027)": page links emc 101125 (Aspire, made by Alfasigma) but image shows a DEMO S.A. pack
- R05425 John Bannon Pharmacy "Vitamins B+C Intravenous High Potency Ampoule 5ml x 6 pairs": generic 'Vitamins B+C' name, page gives no licence holder/brand and no image - cannot tell Pabrinex (Grünenthal) from Vitenta (Aspire) or an import
- R05599 Moda Pharmacy "Pabrinex I/M": Pabrinex IM has no current emc SmPC (reference not_found; discontinuation unverified)
- R06961 Skin On You "Pabrinex High Potency Concentrate For Injection": route conflict (page text=IM/IV, image=IM); pack size only visible in the image
- R06981 Skin On You "Vitamins B+C Intravenous High Potency Concentrate For Solution For Infusion": page lists B5/B12, which are not in the UK SmPC composition (thiamine, riboflavin, pyridoxine, ascorbic acid, nicotinamide, glucose); pack size only visible in the image
- R10321 Ask Pharmacy "vitamin c im 2ml single ampoule pabrinex im clone": sold as a single ampoule (only one of the No.1/No.2 pair) - not a UK presentation; image shows a full 10-pair box; Pabrinex IM has no current emc SmPC (reference not_found; discontinuation unverified)
- R10427 Ask Pharmacy "pabrinex im 10 dual 1 box 2": Pabrinex IM has no current emc SmPC (reference not_found; discontinuation unverified)
- R10470 Ask Pharmacy "vitamin c im 2ml single ampoule pabrinex im clone 2": route conflict (page title=IV, page text=IM); sold as a single ampoule (only one of the No.1/No.2 pair) - not a UK presentation
- R10511 Ask Pharmacy "pabrinex vitamin c b inj iv 5ml pack of 6": page says Pabrinex but image shows a DEMO S.A. 'Vitamins B+C' pack (not Pabrinex, not on emc)
- R02596 Church Pharmacy "teosyal rha3": syringe volume differs across suppliers {'1.2': 2, '1': 1}
- R05319 John Bannon Pharmacy "Teosyal RHA3 2x1.2ml": lidocaine not stated on page - grouped with lidocaine version only provisionally; syringe volume differs across suppliers {'1.2': 1, '1': 1}
- R05672 Moda Pharmacy "Teosyal Rha 3 (2x1ml)": syringe volume differs across suppliers {'1.2': 2, '1': 1}
- R06940 Skin On You "Teoxane Teosyal RHA 3": syringe volume differs across suppliers {'1.2': 2, '1': 1}
- R10281 Ask Pharmacy "teosyal rha 3 1 x 1ml single syringe": lidocaine not stated on page - grouped with lidocaine version only provisionally; syringe volume differs across suppliers {'1.2': 1, '1': 1}
- R04484 John Bannon Pharmacy "Azzalure Syringe x 10": listing is syringes, not the toxin itself (accessory?); strength (units) not on page; vial count not stated on page
- R10386 Ask Pharmacy "aciclovir 200mg x 25 tablets": image shows DISPERSIBLE tablets but page/title say plain tablets

## Cross-supplier notes

- F-TEOSYAL/rha-3-lidocaine: suppliers disagree on syringe volume {'1.2': 2, '1': 1} - no official presentation read
- F-TEOSYAL/rha-3-lidocaine-not-stated: suppliers disagree on syringe volume {'1.2': 1, '1': 1} - no official presentation read

## Rules that needed changing / interpretation

- Status words are read only from titles and the stock field; page boilerplate ("New here?", "Directions: available on request", category "Vitamins & IV") produced false status/route hits.
- "Vitamins & IV" (Ask Pharmacy category label) is neutral, not a route.
- A pack count/vial count visible only in the product image lowers confidence to 'likely' (not 'uncertain'): the image is part of the page.
- Profhilo 'UK hologram' kept as a note, not a variant, until the owner decides (see open questions).
- 'Lidocaine not stated' rows are grouped with the lidocaine variant provisionally and marked 'likely' (UK Juvederm Ultra/Teosyal packs seen are lidocaine versions).
