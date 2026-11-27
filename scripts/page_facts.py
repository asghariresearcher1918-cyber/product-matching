"""Read EVERYTHING on a product page before deciding (owner rules, 2026-11-18):
 1. read all tabs of the page, not only the first one (Description, Additional information, Size and Care Info,
    Box contents, Product details / SKU, product options ...) - the cached HTML holds every tab;
 2. if the answer is still missing, read the text on the product images (OCR);
 3. only when nothing is found anywhere, apply the category default (e.g. toxins: 1 vial).
Related-product blocks ("You may also like", "Bestseller" ...) are cut off so other products' facts never leak in.
Usage (module): from page_facts import page_text, labelled_fields, image_text"""
import glob, re, subprocess
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
RELATED = re.compile(
    r"you may also (?:like|need|enjoy)|you might also (?:like|need|enjoy)|related products?|related items?|"
    r"customers also (?:bought|viewed|liked)|customers who bought|frequently bought together|often bought together|"
    r"recently viewed|similar products?|similar items?|bestsellers?|best ?sellers?|people also bought|"
    r"complete the look|complete your (?:order|routine)|recommended for you|we (?:also )?recommend|"
    r"our recommendations|you may be interested|pairs well with|goes well with|shop the range|shop more|more from|"
    r"other products|trending( now)?|top sellers|add[- ]?ons?|more in this (?:category|range)|related categories|"
    # 'Recommended' / 'Recommended products' as a carousel heading, but NOT 'recommended dose/use/for ...' in prose
    r"recommended(?:\s+products?)?(?!\s+(?:dose|dosage|use|usage|for|to|that|daily|treatment|amount|storage|interval|number|frequency|time|period|age|by|when|if|that))",
    re.I)
LABELS = r"size and care info|box contents|pack contents|contents|pack size|size|product options?|quantity|qty|presentation|sku|product code|quickfind code"


def _file(pid):
    for pat in (f"cache/*/{pid}.rendered.html", f"cache/*/{pid}.html"):
        f = glob.glob(str(ROOT / pat))
        if f: return f[0]
    return None


def page_text(pid):
    """Whole page text (all tabs), header/nav/footer removed, cut before the first related-products block."""
    f = _file(pid)
    if not f: return ""
    s = BeautifulSoup(open(f, encoding="utf-8", errors="ignore").read(), "lxml")
    for x in s(["script", "style", "noscript", "svg"]): x.decompose()  # not header/nav/footer: some sites wrap the product in them
    t = " ".join(s.get_text(" ", strip=True).split())
    start = 0
    m = re.search(r"\b(description|product overview|product details)\b", t, re.I)  # the product block starts around the first Description / Overview tab
    if m: start = max(0, m.start() - 1500)
    r = RELATED.search(t, m.end() if m else 0)
    return t[start: r.start() if r else len(t)]


def labelled_fields(text):
    """'Label: value' pairs found in tab content, e.g. {'size': '1 x 50units', 'box contents': '1 x 100 Unit Vial ...'}."""
    out = {}
    for m in re.finditer(rf"\b({LABELS})\b\s*:?\s*(.{{1,60}}?)(?=\s+(?:{LABELS}|form|strength|cold chain|you may|description|additional information)\b|$)", text, re.I):
        k = m.group(1).lower()
        if k not in out: out[k] = m.group(2).strip()
    return out


def image_text(pid):
    """OCR of the cached main product image (result cached next to it as .ocr.txt)."""
    imgs = glob.glob(str(ROOT / f"cache/*/{pid}.img.*"))
    imgs = [i for i in imgs if not i.endswith(".ocr.txt")]
    if not imgs: return ""
    cache = Path(imgs[0] + ".ocr.txt")
    if cache.exists(): return cache.read_text()
    try:
        t = subprocess.run(["tesseract", imgs[0], "-", "--psm", "11"], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        t = ""
    t = " ".join(t.split())
    cache.write_text(t)
    return t
