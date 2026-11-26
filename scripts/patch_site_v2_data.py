"""Refresh ONLY the PRODUCTS and SUPPLIERS data in an already-built v2 site page, leaving the UI/JS untouched.
Used when the pristine prototype isn't available but the catalogue data changed (e.g. pack/size added).
Reuses build_site_v2.build_data() so the data is generated exactly as in a full build.

Usage: python -I scripts/patch_site_v2_data.py output/site/basis_v2.html"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_site_v2 as b

def main():
    page = Path(sys.argv[1])
    html = page.read_text(encoding="utf-8")
    PRODUCTS, SUPPLIERS = b.build_data()
    js_sup = "var SUPPLIERS = " + json.dumps(SUPPLIERS, ensure_ascii=False) + ";"
    js_prd = "var PRODUCTS = " + json.dumps(PRODUCTS, ensure_ascii=False, separators=(",", ":")) + ";"
    # tolerant: match both the pretty prototype block and the minified single-line built form. JSON has no ';',
    # so the first '};' after the declaration is always the statement terminator.
    html, n1 = re.subn(r"var SUPPLIERS = \{.*?\};", lambda m: js_sup, html, count=1, flags=re.S)
    html, n2 = re.subn(r"var PRODUCTS = \{.*?\};", lambda m: js_prd, html, count=1, flags=re.S)
    assert n1 == 1 and n2 == 1, f"data block replace failed: SUP={n1} PRD={n2}"
    page.write_text(html, encoding="utf-8")
    print(f"patched {page} | products {len(PRODUCTS)} | suppliers {len(SUPPLIERS)}")


if __name__ == "__main__":
    main()
