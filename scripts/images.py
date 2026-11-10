"""Download each page's main product image (polite, cached, never overwritten) and build
labelled contact sheets for visual checking (rule 10).
Usage: python -I scripts/images.py [--sheet-ids FILE]"""
import json, re, sys, time, urllib.parse
from pathlib import Path
import httpx
ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; product-catalogue-research/1.0)"
def slug(s): return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
def main():
    c = httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=30)
    last = {}
    pages = [json.loads(l) for l in open(ROOT / "pages.jsonl", encoding="utf-8")]
    for p in pages:
        u = p.get("image_url") or ""
        if not u: continue
        u = urllib.parse.urljoin(p["final_url"], u)
        d = ROOT / "cache" / slug(p["supplier"])
        if list(d.glob(p["id"] + ".img.*")): continue
        host = urllib.parse.urlparse(u).netloc
        dt = time.time() - last.get(host, 0)
        if dt < 1: time.sleep(1 - dt)
        last[host] = time.time()
        try:
            r = c.get(u)
            r.raise_for_status()
        except Exception as e:
            print("FAIL", p["id"], u, e); continue
        ext = {"image/png": "png", "image/webp": "webp", "image/gif": "gif"}.get(r.headers.get("content-type", "").split(";")[0], "jpg")
        (d / f"{p['id']}.img.{ext}").write_bytes(r.content)
        print("ok", p["id"], len(r.content))
    from PIL import Image, ImageDraw
    files = sorted((ROOT / "cache").glob("*/*.img.*"))
    tiles = []
    for f in files:
        try:
            im = Image.open(f).convert("RGB"); im.thumbnail((300, 300))
        except Exception as e:
            print("bad image", f, e); continue
        t = Image.new("RGB", (310, 330), "white"); t.paste(im, (5, 25))
        ImageDraw.Draw(t).text((5, 5), f.name.split(".")[0] + " " + f.parent.name[:18], fill="black")
        tiles.append(t)
    out = ROOT / "logs" / "contact_sheets"; out.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(tiles), 12):
        sheet = Image.new("RGB", (310 * 4, 330 * 3), "white")
        for j, t in enumerate(tiles[i:i + 12]): sheet.paste(t, (310 * (j % 4), 330 * (j // 4)))
        sheet.save(out / f"sheet_{i // 12 + 1:02d}.jpg", quality=80)
    print("sheets:", (len(tiles) + 11) // 12, "images:", len(tiles))
if __name__ == "__main__": main()
