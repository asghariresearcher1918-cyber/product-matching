"""Build small EMBEDDED thumbnails (base64 data URIs) for each product's main image, so images display inside the
claude.ai artifact preview, which blocks external (CDN) images. Output: catalogue/final/thumbs.json {uid: dataURI}.
Resumable: uids already in thumbs.json are skipped. Downloads the one primary image per product, fits it on a white
square, and saves a small JPEG as a data URI.

Usage: python -I scripts/build_thumbs.py [limit] [px] [quality]   (defaults: all, 56px, 55)"""
import csv, glob, io, json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "catalogue/final/thumbs.json"
MAPS = [("toxin", "TOX"), ("filler", "FIL"), ("booster", "BST"), ("biostim", "BIO"), ("fat", "FAT"),
        ("thread", "THR"), ("weight", "WGT"), ("medicine", "MED"), ("skincare", "SKN"), ("needle", "NDL"),
        ("consumable", "CON"), ("device", "DEV"), ("bty", "BTY"), ("sup", "SUP"), ("vac", "VAC")]
UA = "Mozilla/5.0 (compatible; catalogue-thumb/1.0)"


def primary_image_by_uid():
    imgurl = {}
    for r in csv.DictReader(open(ROOT / "catalogue/final/listing_images.csv", encoding="utf-8")):
        u = [x for x in (r.get("image_urls") or "").split("|") if x.startswith("http")]
        if u:
            imgurl[r["id"]] = u[0]
    uid_url = {}
    for stem, tag in MAPS:
        p = ROOT / f"catalogue/final/{stem}_listing_map.csv"
        if not p.exists():
            continue
        for m in csv.DictReader(open(p, encoding="utf-8")):
            code = m.get("code", "")
            if not code:
                continue
            uid = f"{tag}:{code}"
            if uid not in uid_url and imgurl.get(m.get("id", "")):
                uid_url[uid] = imgurl[m.get("id", "")]
    return uid_url


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    px = int(sys.argv[2]) if len(sys.argv) > 2 else 56
    q = int(sys.argv[3]) if len(sys.argv) > 3 else 55
    thumbs = json.loads(OUT.read_text()) if OUT.exists() else {}
    uid_url = primary_image_by_uid()
    todo = [(uid, u) for uid, u in uid_url.items() if uid not in thumbs][:limit]
    client = httpx.Client(headers={"User-Agent": UA}, timeout=8, follow_redirects=True)
    lock = threading.Lock()
    st = {"ok": 0, "err": 0}

    def work(item):
        uid, u = item
        try:
            r = client.get(u)
            if r.status_code != 200 or len(r.content) < 800:
                raise ValueError("bad")
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            im.thumbnail((px, px))
            canvas = Image.new("RGB", (px, px), (255, 255, 255))
            canvas.paste(im, ((px - im.width) // 2, (px - im.height) // 2))
            buf = io.BytesIO()
            canvas.save(buf, "JPEG", quality=q)
            import base64
            data = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
            with lock:
                thumbs[uid] = data
                st["ok"] += 1
                if st["ok"] % 300 == 0:
                    OUT.write_text(json.dumps(thumbs))
                    print(f"  {st['ok']} thumbs | errors {st['err']} | json ~{len(json.dumps(thumbs))//1024} KB", flush=True)
        except Exception:
            with lock:
                st["err"] += 1

    with ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(work, todo))
    client.close()
    OUT.write_text(json.dumps(thumbs))
    sz = len(json.dumps(thumbs))
    print(f"DONE: {st['ok']} new, {st['err']} errors | total thumbs {len(thumbs)} | thumbs.json {sz//1024} KB ({sz/1048576:.1f} MB)")


if __name__ == "__main__":
    main()
