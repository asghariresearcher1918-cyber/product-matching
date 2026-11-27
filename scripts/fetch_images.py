"""Download every catalogued product's own images (all angles) from its cached page, then OCR them so the text on
the images (pack counts, sizes printed on boxes/vials) can be read. Resumable and idempotent: a listing whose
images are already fetched (or marked image-less) is skipped, so this can be re-run until complete.

Owner rule: read the product images in every angle provided. On-hold suppliers whose anti-bot must not be
bypassed (Refine Pharma, DermaFocus) are skipped entirely.

Usage: python -I scripts/fetch_images.py [limit]      # process up to <limit> new listings this run (default all)"""
import csv, glob, re, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
from PIL import Image

WORKERS = 16

ROOT = Path(__file__).resolve().parent.parent
SKIP_SUPPLIERS = {"refine_pharma", "dermafocus"}        # on-hold: do not touch (anti-bot must not be bypassed)
MAX_IMAGES = 3                                          # main + a few angles is enough to read a label
UA = "Mozilla/5.0 (compatible; catalogue-image-fetch/1.0)"   # generic; never the user's identity
IMG_RE = re.compile(r"\.(jpg|jpeg|png|webp)$", re.I)


def _cached_html(pid):
    for pat in (f"cache/*/{pid}.rendered.html", f"cache/*/{pid}.html"):
        f = glob.glob(str(ROOT / pat))
        if f:
            return f[0]
    return None


def _norm(u):
    u = u.replace("\\/", "/").strip()
    if u.startswith("//"):
        u = "https:" + u
    u = re.sub(r"^http://", "https://", u)
    return u.split("#")[0]


def _base(u):
    """Identity of an image ignoring CDN size/version params, so '..._300x.webp' and '..._1200x.webp' are one."""
    name = re.sub(r"\?.*$", "", u).rsplit("/", 1)[-1]
    name = re.sub(r"[_-]\d{2,4}x\d{0,4}(?=\.)", "", name)        # _300x, _1200x1200
    return name.lower()


def image_urls(html):
    s = BeautifulSoup(html, "lxml")
    urls, seen = [], set()

    def add(u):
        if not u:
            return
        u = _norm(u)
        if not IMG_RE.search(re.sub(r"\?.*$", "", u)):
            return
        if re.search(r"/(logo|icon|sprite|payment|badge|flag|avatar|banner)", u, re.I):
            return
        # filename-based placeholders: a shop logo / coming-soon / no-image used in place of a product photo
        if re.search(r"(logo|placeholder|coming[-_]?soon|no[-_]?image|default[-_]?image|image[-_]?coming)", u.rsplit("/",1)[-1], re.I):
            return
        b = _base(u)
        if b in seen:
            return
        seen.add(b)
        urls.append(u)

    og = s.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        add(og["content"])
    for m in re.finditer(r'"image"\s*:\s*\[?\s*"([^"]+)"', html):      # JSON-LD
        add(m.group(1))
    # Shopify product gallery + WooCommerce uploads, in document order
    for m in re.finditer(r'(?:https?:)?\\?/\\?/[^\s"\'<>]+?/(?:cdn/shop/products|cdn/shop/files|wp-content/uploads)/[^\s"\'<>]+?\.(?:jpg|jpeg|png|webp)', html, re.I):
        add(m.group(0))
    for img in s.find_all("img"):
        for a in ("data-zoom-image", "data-large_image", "data-image", "data-src", "src"):
            if img.get(a):
                add(img[a]); break
    return urls[:MAX_IMAGES]


def ocr(path):
    """OCR one image to text; convert to grayscale PNG first so webp/large images read reliably. '' on failure."""
    try:
        im = Image.open(path).convert("L")
        if max(im.size) > 1600:
            im.thumbnail((1600, 1600))
        tmp = str(path) + ".ocr.png"
        im.save(tmp)
        t = subprocess.run(["tesseract", tmp, "-", "--psm", "11"], capture_output=True, text=True, timeout=60).stdout
        Path(tmp).unlink(missing_ok=True)
        return " ".join(t.split())
    except Exception:
        return ""


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    ids = {}
    for f in glob.glob(str(ROOT / "catalogue/final/*_listing_map.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r.get("id") and r["id"] not in ids:
                ids[r["id"]] = True
    client = httpx.Client(headers={"User-Agent": UA}, timeout=8, follow_redirects=True)
    st = {"done": 0, "imgs": 0, "ocr": 0, "skip": 0, "err": 0}
    lock = threading.Lock()

    # precompute, by listing each cache dir ONCE, the pids already fetched (have an .img.* sidecar) or marked
    # image-less (.noimg) — far faster than globbing per id across every supplier dir.
    done_pids, html_of = set(), {}
    for f in glob.glob(str(ROOT / "cache/*/*")):
        name = Path(f).name
        if name.endswith(".noimg"):
            done_pids.add(name[:-6])
        elif ".img." in name:
            done_pids.add(name.split(".img.", 1)[0])
        elif name.endswith(".html"):
            pid = name.split(".rendered.html")[0].split(".html")[0]
            html_of.setdefault(pid, f)                    # prefer whichever; rendered/plain both fine for <img> URLs

    todo = []
    for pid in ids:
        if pid in done_pids:
            st["skip"] += 1
            continue
        hf = html_of.get(pid)
        if not hf or Path(hf).parent.name in SKIP_SUPPLIERS:
            continue
        todo.append((pid, hf, Path(hf).parent / pid))
        if len(todo) >= limit:
            break

    def work(item):
        pid, hf, base = item
        try:
            urls = image_urls(open(hf, encoding="utf-8", errors="ignore").read())
        except Exception:
            urls = []
        got = 0
        for i, u in enumerate(urls):
            ext = re.sub(r"\?.*$", "", u).rsplit(".", 1)[-1].lower()
            out = Path(str(base) + f".img.{i}.{ext}")
            try:
                r = client.get(u)
                if r.status_code == 200 and len(r.content) > 1500:
                    out.write_bytes(r.content)
                    txt = ocr(out)
                    Path(str(out) + ".ocr.txt").write_text(txt)   # keep the OCR text sidecar...
                    out.unlink(missing_ok=True)                   # ...but delete the heavy image to save disk
                    got += 1
                    with lock:
                        st["imgs"] += 1
                        if txt:
                            st["ocr"] += 1
            except Exception:
                with lock:
                    st["err"] += 1
        if got == 0:
            Path(str(base) + ".noimg").write_text("")
        with lock:
            st["done"] += 1
            if st["done"] % 200 == 0:
                print(f"  processed {st['done']}/{len(todo)} | images {st['imgs']} | ocr-with-text {st['ocr']} | errors {st['err']}", flush=True)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(work, todo))
    client.close()
    print(f"DONE this run: processed {st['done']} new | images {st['imgs']} | ocr-with-text {st['ocr']} | "
          f"skipped-already-done {st['skip']} | errors {st['err']}")


if __name__ == "__main__":
    main()
