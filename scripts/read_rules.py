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
    r"[\(\[]\s*(?:box|pack|case|tub)\s*(\d{1,4})\s*[\)\]]",                       # '( Box 10 )' / '[Pack 25]'
    r"\b(?:box|pack|case|tub)\s+(\d{1,4})\b(?!\s*(?:cm|mm|ml|l|g|kg|mcg|m|oz|in|x))",  # 'Box 100', 'Pack 25'
    r"\b(\d{1,4})\s*per\s*(?:box|pack|case)\b",                                   # '100 per box'
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


# the actual selling-unit words a page may use — shown verbatim, never normalised to a generic 'pack' (owner rule).
_CONTAINERS = ("box", "pack", "case", "carton", "roll", "set", "bag", "pouch", "kit", "tub", "dispenser",
               "sleeve", "tray", "canister", "bucket", "drum", "reel", "cassette")
_CONT_RX = "|".join(c + "(?:es|s)?" for c in _CONTAINERS)
_NOUN_RX = (r"pcs|pieces?|units?|wipes?|swabs?|sheets?|sachets?|tablets?|caps?|capsules?|gloves?|pairs?|strips?|"
            r"ampoules?|amps?|vials?|dressings?|plasters?|applicators?|spatulas?|syringes?|needles?|cannulas?|blades?")
_NESTED_RX = re.compile(r"\b(box|case|carton|drum)(?:es|s)?\b[^.\n]{0,18}?\b(\d{1,4})\s*(packs?|boxes?|strips?|cards?|sachets?|trays?)\b", re.I)


def _sing(w):
    w = w.lower()
    return w[:-2] if w.endswith("es") and w[:-2] in _CONTAINERS else (w[:-1] if w.endswith("s") else w)


def _unit_qty(text):
    """First packaging statement in text -> (qty, unit word as written). Keeps the real word (box/pack/case/roll…)."""
    if not text:
        return "", ""
    m = re.search(r"[\(\[]?\s*(" + _CONT_RX + r")\s*(?:of\s+)?(\d{1,4})\b", text, re.I)          # 'Box of 10' / '( Box 10 )'
    if m and 1 <= int(m.group(2)) <= 100000:
        return m.group(2), _sing(m.group(1))
    m = re.search(r"\b(\d{1,4})\s*(?:per|/)\s*(" + _CONT_RX + r")\b", text, re.I)                  # '100 per box'
    if m and 1 <= int(m.group(1)) <= 100000:
        return m.group(1), _sing(m.group(2))
    m = re.search(r"\b(\d{1,4})\s*(" + _NOUN_RX + r")\b", text, re.I)                              # '100 wipes', '30 tablets'
    if m and 2 <= int(m.group(1)) <= 100000:
        return m.group(1), m.group(2).lower()
    return "", ""


def read_packaging(title, pid):
    """Owner rule: read the pack AND its real unit word from the product's own page. Returns (qty, unit, nested_note).
    The unit is the word the shop used (box/pack/case/roll/… or a content noun); '' when only a bare count is given.
    nested_note is set when the page states two levels (e.g. 'box of 20 packs') so it is never flattened silently."""
    for src in ([title] if title else []) + ([page_text(pid)] if pid else []):
        q, u = _unit_qty(src)
        if q:
            nested = ""
            if pid:
                mn = _NESTED_RX.search(page_text(pid))
                if mn:
                    nested = f"{mn.group(1).lower()} of {mn.group(2)} {mn.group(3).lower()}"
            return q, u, nested
    q = read_pack(title, pid)                    # falls through to labelled field / description / OCR (number only)
    if q:
        return q, "", ""
    # 'Each' as the packaging slot = sold singly = a pack of 1 (owner rule), unless a number was stated (handled above)
    for src in ([title] if title else []) + ([page_text(pid)] if pid else []):
        if re.search(r"[\(\[]\s*each\s*[\)\]]|\bsold\s+(?:each|singly|individually)\b|\bpriced\s+each\b|"
                     r"£\s*\d[\d.]*\s*each\b", src, re.I):
            return "1", "", ""
    return "", "", ""


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


_NONSTERILE = re.compile(r"\bnon[\s-]*sterile\b", re.I)
_STERILE = re.compile(r"(?<!non[\s-])\bsterile\b", re.I)


def sterility(title, pid):
    """'Sterile' or 'Non-sterile' when the NAME or the product's own page states it (critical for surgical items);
    '' when neither does. Never guessed. Non-sterile is checked first so 'non-sterile' is not read as 'sterile'."""
    for src in (title or "", page_text(pid) if pid else ""):
        if not src:
            continue
        if _NONSTERILE.search(src):
            return "Non-sterile"
        if _STERILE.search(src):
            return "Sterile"
    return ""


def ensure_sterility(title, pid):
    """Keep sterile/non-sterile in the name, and ADD it from the page when the name omits it (owner rule: it must
    stay in the title we show). Returns the name unchanged if its sterility is already stated or the page is silent."""
    if not title or _NONSTERILE.search(title) or _STERILE.search(title):
        return title
    s = sterility("", pid)
    return f"{title} — {s}" if s else title


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
