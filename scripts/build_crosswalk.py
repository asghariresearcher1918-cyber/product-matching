"""One authoritative join table so a pharmacy's future official feed connects to our catalogue with zero re-matching:
each supplier LISTING -> its stable keys (url, sku) -> our reference PRODUCT uid + name.
Output: catalogue/final/crosswalk.csv"""
import csv, glob
from pathlib import Path
ROOT=Path('.')
MAPS=[("toxin","TOX"),("filler","FIL"),("booster","BST"),("biostim","BIO"),("fat","FAT"),
      ("thread","THR"),("weight","WGT"),("medicine","MED"),("skincare","SKN"),("needle","NDL"),
      ("consumable","CON"),("device","DEV"),("bty","BTY"),("sup","SUP"),("vac","VAC")]
# sku from structured json-ld
sku={}
try:
    for r in csv.DictReader(open(ROOT/'catalogue/final/structured.csv',encoding='utf-8')):
        if r.get('sku'): sku[r['id']]=r['sku']
except FileNotFoundError: pass
rows=[]; seen=set()
for stem,tag in MAPS:
    p=ROOT/f'catalogue/final/{stem}_listing_map.csv'
    if not p.exists(): continue
    for m in csv.DictReader(open(p,encoding='utf-8')):
        lid=m.get('id','')
        if not lid or lid in seen: continue
        seen.add(lid)
        code=m.get('code','')
        uid=f"{tag}:{code}" if code else ""
        rows.append({"listing_id":lid,"supplier":m.get('supplier',''),"url":m.get('url',''),
                     "sku":sku.get(lid,''),"product_uid":uid,"catalogue_code":code,
                     "listing_title":m.get('title','')})
cols=["listing_id","supplier","url","sku","product_uid","catalogue_code","listing_title"]
out=ROOT/'catalogue/final/crosswalk.csv'
with open(out,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)
join_url=sum(1 for r in rows if r['url'].startswith('http'))
join_sku=sum(1 for r in rows if r['sku'])
linked=sum(1 for r in rows if r['product_uid'])
print(f"crosswalk.csv: {len(rows)} listings")
print(f"  joinable by URL: {join_url} ({100*join_url//len(rows)}%)")
print(f"  joinable by SKU: {join_sku} ({100*join_sku//len(rows)}%)")
print(f"  linked to a reference product uid: {linked} ({100*linked//len(rows)}%)")
