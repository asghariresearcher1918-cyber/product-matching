"""Build small EMBEDDED thumbnails (base64 data URIs) keyed by LISTING id, so the site can show each supplier's own
product photo next to its row in a product's price comparison — telling apart same-named, brand-less listings that
were grouped into one product. Output: catalogue/final/listing_thumbs.json {listing_id: dataURI}. Resumable.

Usage: python -I scripts/build_listing_thumbs.py [limit] [px] [quality]   (defaults: all, 48px, 55)"""
import base64, csv, io, json, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "catalogue/final/listing_thumbs.json"
UA = "Mozilla/5.0 (compatible; catalogue-thumb/1.0)"


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    px = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    q = int(sys.argv[3]) if len(sys.argv) > 3 else 55
    thumbs = json.loads(OUT.read_text()) if OUT.exists() else {}
    url_of = {}
    for r in csv.DictReader(open(ROOT / "catalogue/final/listing_images.csv", encoding="utf-8")):
        u = [x for x in (r.get("image_urls") or "").split("|") if x.startswith("http")]
        if u and r["id"] not in thumbs:
            url_of[r["id"]] = u[0]
    todo = list(url_of.items())[:limit]
    client = httpx.Client(headers={"User-Agent": UA}, timeout=8, follow_redirects=True)
    lock = threading.Lock()
    st = {"ok": 0, "err": 0}

    def work(item):
        lid, u = item
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
            data = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
            with lock:
                thumbs[lid] = data
                st["ok"] += 1
                if st["ok"] % 400 == 0:
                    OUT.write_text(json.dumps(thumbs))
                    print(f"  {st['ok']} listing thumbs | errors {st['err']} | ~{len(json.dumps(thumbs))//1048576} MB", flush=True)
        except Exception:
            with lock:
                st["err"] += 1

    with ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(work, todo))
    client.close()
    OUT.write_text(json.dumps(thumbs))
    sz = len(json.dumps(thumbs))
    print(f"DONE: {st['ok']} new, {st['err']} errors | total {len(thumbs)} | listing_thumbs.json {sz/1048576:.1f} MB")


if __name__ == "__main__":
    main()
