# Are our 24 supplier lists complete? (checked 2026-11-18, public pages only, no login)

Method: each supplier's public sitemap (robots.txt respected, honest user agent, 1 request/second), or the public
shop listing when there is no sitemap, compared with our input list. New products -> data/products_added.csv (ids A.....; the owner file uses R and N).

| Supplier | Our list | Public catalogue | Added | Status |
|---|---|---|---|---|
| Church Pharmacy | 2,565 | 3,378 (sitemap) | 1,107 | completed from sitemap |
| John Bannon | 1,048 | 1,093 products (+262 blog posts in sitemap, ignored) | 45 | completed from sitemap |
| MedFX | 374 | 732 (sitemap) | 360 | completed from sitemap |
| MyPharmacyspace | 340 | 386 (sitemap) | 46 | list complete; product details need login |
| LPG Clinics | 643 | 676 | 42 | completed |
| Wimpole Fillers | 311 | 327 | 17 | completed |
| Dr. Adams | 476 | 481 (shop pages) | 16 | completed from shop pages |
| Smile Pharma | 366 | 378 | 15 | completed |
| Herts & Essex | 272 | 261 | 11 | completed (22 of ours no longer listed) |
| Harpar Grace | 145 | 146 (shop JSON) | 8 | completed (sitemap hides products) |
| Ask Pharmacy | 631 | 637 | 7 | completed |
| AesthetiCare, AestheticSource, Two Face | | | 6 each | completed |
| Moda, Kiss | | | 4, 3 | completed |
| Skin On You | 268 | 60 in sitemap page 1 | 1 | sitemap is paginated - our list looks complete |
| Healthxchange, IGO | | | 0 | already complete |
| Fox Pharma | 407 | 342 | 0 | complete; 65 of ours no longer listed (removed?) |
| ACRE | 1,089 | 646 shop items | 0 | ACRE lists each product twice (stock item / prescription item) under separate links; exact reconciliation by name still to do |
| Aesthetic Pharma | 233 | 235 total, 156 shown publicly | 0 | **login needed**: 77-79 products are shown only to registered customers ("Register to see a full list") |
| DermaFocus | 14 | - | 0 | site drops automated connections - retry later |
| Refine Pharma | 373 | - | 0 | **owner permission needed** (session permission rule) - robots.txt allows product pages |

Total added: 1,700 products (262 John Bannon blog posts removed).
