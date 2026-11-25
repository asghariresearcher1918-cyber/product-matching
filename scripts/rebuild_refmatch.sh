#!/usr/bin/env bash
# Reproducible rebuild of the reference-matched catalogue WITH option-page expansion.
# Order matters: each category's listing map must be expanded into per-option offers BEFORE reference_match runs.
# expand_variants is idempotent (already-expanded rows carry opt_price and are skipped), so this is safe to re-run.
set -e
cd "$(dirname "$0")/.."

for stem in toxin filler booster biostim fat skincare; do
  python -I scripts/expand_variants.py "$stem"
done

python -I scripts/reference_match.py
python -I scripts/master_catalogue.py
python -I scripts/canonical_names.py
python -I scripts/master_catalogue.py
python -I scripts/auto_consolidate.py
python -I scripts/taxonomy_map.py
echo "rebuild complete"
