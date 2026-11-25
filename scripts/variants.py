"""Read EVERY purchasable option (variant) of a product page from the cached HTML, so a page that sells e.g. a single
vial AND a 5-vial box becomes TWO offers (each with its own pack, volume, price, SKU) instead of one. Sources:
Shopify product JSON ('variants':[...]) and WooCommerce variations JSON / <select> options. Deterministic: only real,
structured option data is used - never guessed. Usage (module): from variants import page_variants(pid) -> list of
{title, pack, volume_ml, price, sku}."""
import glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _html(pid):
    for pat in (f"cache/*/{pid}.rendered.html", f"cache/*/{pid}.html"):
        f = glob.glob(str(ROOT / pat))
        if f:
            return open(f[0], encoding="utf-8", errors="ignore").read()
    return ""


def _pack_vol(title):
    """'1x 10ml (vial)' -> (1, '10ml'); '5 x 10ml vials (box)' -> (5, '10ml'); 'Pack of 10' -> (10, '')."""
    t = title.lower()
    m = re.search(r"(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*ml", t)
    if m:
        return int(m.group(1)), m.group(2) + "ml"
    m = re.search(r"pack of\s*(\d+)|box of\s*(\d+)|\b(\d+)\s*(?:vials?|pcs|bottles?|amp)", t)
    if m:
        return int(next(g for g in m.groups() if g)), ""
    m = re.search(r"\b(\d+)\s*['’]?s\b", t)
    if m:
        return int(m.group(1)), ""
    if re.search(r"\bsingle\b|\b1\s*vial\b|\(vial\)", t):
        return 1, (re.search(r"(\d+(?:\.\d+)?)\s*ml", t).group(1) + "ml" if re.search(r"(\d+(?:\.\d+)?)\s*ml", t) else "")
    v = re.search(r"(\d+(?:\.\d+)?)\s*ml", t)
    return None, (v.group(1) + "ml" if v else "")


def _norm_price(v):
    """Shopify prices are pence ints (2500) OR pound floats (25.0). Return pounds as a string, or ''."""
    try:
        f = float(v)
    except Exception:
        return ""
    if f >= 1000 and f == int(f):        # looks like pence (2500 -> 25.00)
        f = f / 100.0
    return f"{f:.2f}"


def page_variants(pid):
    html = _html(pid)
    if not html:
        return []
    out, seen = [], set()

    # 1) Shopify: a "variants":[ {..} ] array. Pull title/public_title + price + sku per object.
    for arr in re.finditer(r'"variants"\s*:\s*\[', html):
        i = arr.end() - 1
        depth, j = 0, i
        while j < len(html) and j < i + 60000:
            if html[j] == "[":
                depth += 1
            elif html[j] == "]":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        chunk = html[i:j + 1]
        for obj in re.finditer(r"\{[^{}]*\}", chunk):
            o = obj.group(0)
            tt = re.search(r'"(?:public_title|title|name)"\s*:\s*"([^"]+)"', o)
            pp = re.search(r'"(?:price)"\s*:\s*\{?\s*"?(?:amount"\s*:\s*)?"?(\d+(?:\.\d+)?)', o)
            sk = re.search(r'"sku"\s*:\s*"([^"]*)"', o)
            if not tt or not pp:
                continue
            title = tt.group(1)
            if title.lower() in ("default title", "null", ""):
                continue
            pack, vol = _pack_vol(title)
            key = (title.strip().lower(), _norm_price(pp.group(1)))
            if key in seen:
                continue
            seen.add(key)
            out.append({"title": title.strip(), "pack": pack, "volume_ml": vol,
                        "price": _norm_price(pp.group(1)), "sku": (sk.group(1) if sk else "")})

    # 2) WooCommerce: data-product_variations='[...]' JSON
    mv = re.search(r"data-product_variations\s*=\s*'(\[.*?\])'", html, re.S)
    if mv and not out:
        try:
            for v in json.loads(mv.group(1).replace("&quot;", '"')):
                attrs = " ".join(str(x) for x in (v.get("attributes") or {}).values())
                pack, vol = _pack_vol(attrs + " " + (v.get("sku") or ""))
                out.append({"title": attrs or (v.get("sku") or ""), "pack": pack, "volume_ml": vol,
                            "price": _norm_price(v.get("display_price", "")), "sku": v.get("sku", "")})
        except Exception:
            pass
    return out


if __name__ == "__main__":
    import sys
    for v in page_variants(sys.argv[1]):
        print(v)
