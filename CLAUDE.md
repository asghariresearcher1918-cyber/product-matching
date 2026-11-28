# Project conventions

## Excel / spreadsheet deliverables
- **Every Excel file we hand the owner must include a clickable product link on each row.**
  Use the listing `url` as an openable hyperlink (e.g. a "Link (click)" / "Open product ↗" cell).
  This applies to every workbook — category exports, review/QC sheets, ad-hoc extracts — no exceptions.
  The per-product link comes from `catalogue/final/*_listing_map.csv` (`url` column) or `crosswalk.csv`.

## Catalogue notes
- Display names are restored from cached page titles via `data/title_overrides.csv`
  (built by `scripts/build_title_overrides.py`); this is display-only and never changes uids/codes.
- On-hold suppliers **Refine Pharma** and **DermaFocus** stay excluded — never scrape/render them.
