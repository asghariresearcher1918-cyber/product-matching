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
    PRODUCTS, SUPPLIERS, THUMBS = b.build_data()
    js_sup = "var SUPPLIERS = " + json.dumps(SUPPLIERS, ensure_ascii=False) + ";"
    js_prd = "var PRODUCTS = " + json.dumps(PRODUCTS, ensure_ascii=False, separators=(",", ":")) + ";"
    js_thm = "var THUMBS = " + json.dumps(THUMBS, ensure_ascii=False, separators=(",", ":")) + ";"
    # tolerant: match both the pretty prototype block and the minified single-line built form. JSON has no ';',
    # so the first '};' after the declaration is always the statement terminator.
    html, n1 = re.subn(r"var SUPPLIERS = \{.*?\};", lambda m: js_sup, html, count=1, flags=re.S)
    html, n2 = re.subn(r"var PRODUCTS = \{.*?\};", lambda m: js_prd, html, count=1, flags=re.S)
    # THUMBS pool: replace if present, else insert just before PRODUCTS.
    html, nt = re.subn(r"var THUMBS = \[.*?\];", lambda m: js_thm, html, count=1, flags=re.S)
    if nt == 0:
        html, nt = re.subn(r"(var PRODUCTS = )", lambda m: js_thm + "\n  " + m.group(1), html, count=1)
    assert n1 == 1 and n2 == 1 and nt == 1, f"data block replace failed: SUP={n1} PRD={n2} THM={nt}"
    page.write_text(html, encoding="utf-8")
    print(f"patched {page} | products {len(PRODUCTS)} | suppliers {len(SUPPLIERS)} | thumbs {len(THUMBS)}")


if __name__ == "__main__":
    main()
