"""Extract platform-independent structured product data (Schema.org JSON-LD) for every catalogued listing, and flag
listings whose structured NAME disagrees with our listing title — a reliable, cross-platform way to catch pages the
shop silently repointed to a different product (e.g. 'hot cold pack' whose page is really 'Sani-cloth wipes').

Outputs:
  catalogue/final/structured.csv   id,supplier,listing_title,struct_name,image,price,currency,availability,sku,name_match
  output/structured_mismatch.csv   the subset where name_match == 'MISMATCH' (for review / drop)
Usage: python -I scripts/build_structured.py"""
import csv, glob, re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from structured import product_struct

ROOT = Path(__file__).resolve().parent.parent
STOP = set("the a an of and or for with to in on at by from pack box set kit x ml mg g cm mm size new sterile non "
           "disposable medical uk pharmacy product products buy online ltd single use with without 1 2 3 4 5 10 "
           "pom p vial vials pre filled".split())


def words(s):
    return {w for w in re.findall(r"[a-z0-9]{3,}", (s or "").lower()) if w not in STOP}


def _alnum(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def related(a, b, ta="", tb=""):
    # punctuation-insensitive whole-string check first ('Bio-Oil' == 'biooil', 'Co-Amoxiclav' == 'coamoxiclav')
    ca, cb = _alnum(ta), _alnum(tb)
    if ca and cb and len(min(ca, cb, key=len)) >= 6 and (ca in cb or cb in ca):
        return True
    for x in a:
        for y in b:
            if x == y or (len(x) >= 4 and y.startswith(x)) or (len(y) >= 4 and x.startswith(y)):
                return True
    return False


def main():
    seen, rows, mism = set(), [], []
    for mp in sorted(glob.glob(str(ROOT / "catalogue/final/*_listing_map.csv"))):
        for r in csv.DictReader(open(mp, encoding="utf-8")):
            pid, title = r.get("id", ""), r.get("title", "")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            s = product_struct(pid)
            if not s:
                continue
            lw, nw = words(title), words(s.get("name", ""))
            match = "" if not (lw and nw) else ("OK" if related(lw, nw, title, s.get("name", "")) else "MISMATCH")
            row = {"id": pid, "supplier": r.get("supplier", ""), "listing_title": title,
                   "struct_name": s.get("name", ""), "image": (s.get("images") or [""])[0],
                   "price": s.get("price", ""), "currency": s.get("currency", ""),
                   "availability": s.get("availability", ""), "sku": s.get("sku", ""), "name_match": match}
            rows.append(row)
            if match == "MISMATCH":
                mism.append(row)
    cols = ["id", "supplier", "listing_title", "struct_name", "image", "price", "currency", "availability", "sku", "name_match"]
    with open(ROOT / "catalogue/final/structured.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    with open(ROOT / "output/structured_mismatch.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(mism)
    print(f"structured.csv: {len(rows)} listings with JSON-LD | with image {sum(1 for x in rows if x['image'])} | "
          f"with price {sum(1 for x in rows if x['price'])}")
    print(f"name mismatches (page is a different product): {len(mism)}  -> output/structured_mismatch.csv")


if __name__ == "__main__":
    main()
