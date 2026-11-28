"""THE single, shared implementation of the owner's product-reading rules, applied identically to EVERY category.
No per-category guessing: a product's PACK and SIZE are read from its own page, in this fixed order of trust:

  PACK (units per pack):
    1. the NAME                      (e.g. 'pack of 10', '2 x 5ml' -> 2, 'x 5', 'single mask' -> 1)
    2. the labelled Size/Pack/Quantity field on the page
    3. an explicit statement in the description  ('pack contains N', 'quantity: N', 'N x <unit>')
    4. the same, read off the product images (OCR sidecar)
  SIZE (volume / strength): the NAME first, then the labelled Size/Strength/Volume field, then the page text.

Related / recommended products are never read (page_facts already cuts them). Nothing is guessed; when the page does
not state a pack, PACK is blank (not invented). Used by build_site_v2 and category_export_v2 so the website and the
Excel always agree, and adding a new pharmacy needs no new code — it is read by these same rules.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_facts import page_text, labelled_fields, image_text
from pack_size import qty_from_name, single_pack, size_of

_UNIT_NOUN = (r"ice ?packs?|packs?|vials?|units?|pieces?|pcs|swabs?|wipes?|gloves?|pairs?|sheets?|dressings?|"
              r"plasters?|sachets?|rolls?|syringes?|needles?|cannulas?|applicators?|spatulas?|bibs?|aprons?|"
              r"gowns?|masks?|caps?|capsules?|drapes?|tips?|tablets?|bottles?|tubes?|ampoules?|amps?|strips?|blades?")

_DESC_PATS = [
    r"(?:this |each |per )?(?:pack|box|case|kit|bag|carton|pouch|tub|dispenser)\s+(?:contains?|of)[:\-\s]*(\d{1,4})\s*x?\b",
    r"\bcontains?[:\-\s]*(\d{1,4})\s*x\b",
    r"\b(?:pack size|pack quantity|quantity|qty|units? per (?:pack|box)|no\.? per (?:pack|box))[:\-\s]*(\d{1,4})\b",
    r"\b(\d{1,4})\s*x\s*(?:" + _UNIT_NOUN + r")\b",
    r"\b(\d{1,4})\s*(?:" + _UNIT_NOUN + r")\s+per\s+(?:pack|box|case)\b",
    r"(?:pack of|box of|case of|roll of|set of)\s*(\d{1,4})\b",
]


def _pack_from_desc(text):
    t = text or ""
    for rx in _DESC_PATS:
        m = re.search(rx, t, re.I)
        if m and 1 <= int(m.group(1)) <= 100000:
            return str(int(m.group(1)))
    return ""


def _pack_from_field(key, val):
    """A labelled field value. A Pack/Quantity field's value is itself the count ('Pack size: 100' -> 100); a Size
    field may carry a count the same way the name does ('100 wipes', '1 x 5L')."""
    if not val:
        return ""
    pk = qty_from_name(val) or _pack_from_desc(val)
    if pk:
        return pk
    if key in ("pack", "pack size", "pack quantity", "quantity", "qty"):
        m = re.search(r"\b(\d{1,4})\b", val)              # a bare number in a pack/quantity field is the pack
        if m and 1 <= int(m.group(1)) <= 100000:
            return str(int(m.group(1)))
    return ""


def read_pack(title, pid):
    """Units per pack by the owner rule (name -> labelled field -> description -> image OCR). '' when not stated."""
    pk = qty_from_name(title)                              # 1. NAME (shared rule, same everywhere)
    if pk:
        return pk
    if pid:
        txt = page_text(pid)
        lf = labelled_fields(txt)
        for key in ("size", "pack size", "pack", "quantity", "qty", "pack quantity"):  # 2. labelled field
            if lf.get(key):
                pk = _pack_from_field(key, lf[key])
                if pk:
                    return pk
        pk = _pack_from_desc(txt)                          # 3. description / specifications
        if pk:
            return pk
        pk = _pack_from_desc(image_text(pid))              # 4. product image (OCR sidecar)
        if pk:
            return pk
        if single_pack(title) or single_pack(txt[:800]):   # an explicit 'single' = a pack of 1
            return "1"
        return ""
    return "1" if single_pack(title) else ""


_CODE_RX = re.compile(r"(?:quickfind\s*code|product\s*code|sku|item\s*code|\bcode)\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9\-]{2,})", re.I)


def _page_codes(pid):
    """The shop's own product/SKU/QuickFind code(s) shown on the page, lower-cased for comparison."""
    if not pid:
        return set()
    txt = page_text(pid)
    codes = {m.group(1).lower() for m in _CODE_RX.finditer(txt)}
    lf = labelled_fields(txt)
    for k in ("sku", "product code", "quickfind code"):
        if lf.get(k):
            codes.add(re.sub(r"[^a-z0-9\-]", "", lf[k].lower()))
    return {c for c in codes if c}


def strip_shop_code(title, pid):
    """Remove a trailing number/code from the NAME only when it is the shop's own product code read from the page
    (owner rule). A trailing number that is a size / length / volume, or a blade number like 'No. 15C', is kept —
    it is not in the code field, so it stays. E.g. '… No. 15C (0221)' -> '… No. 15C' because the page says 'code: 0221'.
    """
    if not title:
        return title
    m = re.search(r"\s*[\(\[]?\s*([A-Za-z]{0,4}\d[A-Za-z0-9]*)\s*[\)\]]?\s*$", title)   # a trailing code-like token
    if not m:
        return title
    tail = re.sub(r"[^a-z0-9\-]", "", m.group(1).lower())
    if tail and tail in _page_codes(pid):
        return title[:m.start()].rstrip(" -–—([")
    return title


def read_size(title, pid):
    """Volume / strength by the owner rule (name -> labelled Size/Strength/Volume field -> page text). '' when none."""
    s = size_of(title)                                     # 1. NAME
    if s:
        return s
    if pid:
        txt = page_text(pid)
        lf = labelled_fields(txt)
        for key in ("size", "strength", "volume"):         # 2. labelled field
            if lf.get(key):
                s = size_of(lf[key])
                if s:
                    return s
        s = size_of(txt[:400])                             # 3. page text
        if s:
            return s
    return ""
