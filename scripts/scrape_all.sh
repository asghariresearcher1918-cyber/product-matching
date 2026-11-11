#!/bin/bash
# Run one scraper per supplier in parallel (each still limited to 1 req/s on its own domain). Resumable.
cd "$(dirname "$0")/.."
IDS=${1:-scope_ids.txt}
mapfile -t SUPPLIERS < <(python3 - "$IDS" <<'PY'
import csv,sys
ids={l.strip() for l in open(sys.argv[1]) if l.strip()}
print("\n".join(sorted({r['supplier'] for r in csv.DictReader(open('products_input.csv',encoding='utf-8-sig')) if r['id'] in ids} - {'Refine Pharma'})))
PY
)
for s in "${SUPPLIERS[@]}"; do
  python -I scripts/scrape.py --ids "$IDS" --supplier "$s" >> "logs/scrape_$(echo $s | tr ' &.' '___').log" 2>&1 &
done
wait
echo ALL_DONE
