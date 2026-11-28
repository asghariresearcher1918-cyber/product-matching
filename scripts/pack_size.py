"""Single source of truth for how a product's SIZE (volume / strength) and PACK (units per pack) are read and
displayed, so the Excel exports and the website always show the same values (owner rule: pack is read from the
NAME first, then confirmed against the catalogue/page; never guessed).

Used by scripts/category_export_v2.py and scripts/build_site_v2.py."""
import re

# oral-solid dose forms: for these a catalogue pack of '1' is implausible (tablets/caps come in 28/30/84/112 packs),
# so an unconfirmed '1' is treated as "not stated" rather than shown as a guess.
_ORAL_SOLID = re.compile(r"tablet|capsule|\bcaps?\b|\bclone\b|oral", re.I)


def size_of(*texts):
    """Volume or strength, e.g. '10mg', '0.6ml', '125 Speywood'. First match across the given texts."""
    for t in texts:
        m = re.search(r"(\d+(?:\.\d+)?\s*(?:ml|mg|iu|units?|u\b|speywood))", t or "", re.I)
        if m:
            return m.group(1)
    return ""


def qty_from_name(name):
    """Explicit units-per-pack stated in the NAME. 'pack of N'/'box of N' count from 1 (explicit single); other
    forms count from 2 so a lone '1' is not mistaken for a pack size. Empty when the name states no count."""
    # a count stated inside parentheses is the authoritative pack, and beats a model number in the name
    # (e.g. 'Heliocare 360° Capsules (30 Capsules)' -> 30, not 360).
    mp = re.search(r"\(\s*(?:pack of\s*)?(\d{1,4})\s*(?:caps?|capsules?|tabs?|tablets?|pcs|pieces?|sachets?|"
                   r"amps?|ampoules?|vials?|wipes?|swabs?|sheets?|pairs?|pack)\b[^)]*\)", name or "", re.I)
    if mp and 1 <= int(mp.group(1)) <= 10000:
        return str(int(mp.group(1)))
    # explicit pack markers (pack/box of N, 'x N', 'N pack') are checked BEFORE a bare 'N caps/tabs/…', because that
    # bare number is often a strength, not a count ('Amoxicillin 500 Caps X 21' = 21 of 500mg, not 500).
    for rx, mn in ((r"pack of\s*(\d+)", 1), (r"box of\s*(\d+)", 1),
                   (r"x\s*(\d+)\b", 2), (r"(\d+)\s*pack\b", 2), (r"\b(\d+)\s*['’]s\b", 2),
                   (r"(\d+)\s*(?:pieces?|pcs|ct\b|count|pairs?|sheets?|wipes?|swabs?|rolls?|tabs?|tablets?|caps?|capsules?|sachets?|amps?|ampoules?|ampules?|vials?)\b", 2)):
        m = re.search(rx, name or "", re.I)
        if m and mn <= int(m.group(1)) <= 10000:
            return str(int(m.group(1)))
    if single_pack(name):      # an EXPLICIT single ('single mask', '(single ...)', 'pack of 1') = a pack of 1
        return "1"
    # a lone 'x1' / 'x 1' that is NOT part of an 'A x B' and NOT a size ('x 1ml') = one unit (owner: explicit single)
    if re.search(r"(?<!\d)x\s*1\b(?!\s*(?:ml|mg|g|kg|mcg|cm|mm|m|l|litre|iu|units?|oz|%|\.))", name or "", re.I) \
            and not re.search(r"\d\s*x\s*1\b", name or ""):
        return "1"
    # '1 amp' / '1 vial' / '1 piece' / '1 x 1 (pack)' = one unit (explicit single)
    if re.search(r"\b1\s*(?:amp|ampoule|ampule|vial|piece|unit|applicator|pen)s?\b", name or "", re.I) \
            or re.search(r"\b1\s*x\s*1\b(?!\s*\d|\s*\.|\s*(?:ml|mg|g|cm|mm|m|l|iu))", name or "", re.I):
        return "1"
    return ""


# "single" as an explicit pack of 1 — but only when it counts the ITEM ('single mask', 'single pack', '(single …)',
# 'pack of 1'), never when it describes usage ('single use', 'single dose', 'single patient', 'single application').
_SINGLE = re.compile(r"\bpack of 1\b|\bbox of 1\b|\(?\s*single\s+"
                     r"(?:mask|respirator|pack|unit|piece|item|vial|tube|bottle|sachet|wipe|dressing|applicator|"
                     r"pair|roll|sheet|cartridge|syringe)s?\b", re.I)
_SINGLE_USE = re.compile(r"\bsingle[\s-]*(?:use|dose|patient|application)\b", re.I)


def single_pack(*texts):
    for t in texts:
        if not t:
            continue
        s = _SINGLE_USE.sub(" ", t)          # strip usage descriptors ('single use/dose/…') first, then look for
        if _SINGLE.search(s):                # an explicit single ITEM ('single mask', '(single …)', 'pack of 1')
            return True
    return False


def resolve_pack(name, catalogue_pack):
    """Owner rule, applied the same way everywhere. Returns (qty, flag):
      - an explicit count in the NAME is primary; if it disagrees with the catalogue a flag is returned;
      - else the catalogue's evidenced pack is used;
      - an unconfirmed catalogue pack of '1' on an oral-solid product is treated as 'not stated' (blank + flag),
        never shown as a guess."""
    name = name or ""
    cp = str(catalogue_pack or "").strip()
    nq = qty_from_name(name)
    if nq:
        if cp and cp != nq:
            return nq, f"name says {nq}, catalogue had {cp} — using name"
        return nq, ""
    if cp in ("", "1") and _ORAL_SOLID.search(name) and cp != "":
        return "", "pack not stated in name — confirm pack size"
    return cp, ""


def display_name(name, qty="", unit=""):
    """The product NAME is the shop's real title, unchanged. Pack/size is NEVER appended to the name (owner rule);
    it is shown only in the small subtitle under the name. (qty/unit kept for signature compatibility.)"""
    return name or ""


_CONTAINER_WORDS = {"box", "pack", "case", "carton", "roll", "set", "bag", "pouch", "kit", "tub", "dispenser",
                    "sleeve", "tray", "canister", "bucket", "drum", "reel", "cassette"}


def pack_phrase(qty, unit=""):
    """The pack shown with the SHOP'S OWN unit word (owner rule: never invent a unit).
      container word -> 'Box of 10' / 'Case of 36'; content noun -> '100 wipes'; bare count -> '10' (no invented word);
      a lone '1' with no word -> 'single unit'."""
    q = str(qty or "")
    if not q:
        return ""
    u = (unit or "").lower()
    if u in _CONTAINER_WORDS:
        return f"{u.title()} of {q}"
    if u:
        return f"{q} {u}"
    return "single unit" if q == "1" else q


def pack_label(size, qty, unit=""):
    """Short product subtitle: 'size · <pack phrase>', using the real packaging word."""
    bits = []
    if size:
        bits.append(size)
    pp = pack_phrase(qty, unit)
    if pp and not (pp == "single unit" and size):
        bits.append(pp)
    return " · ".join(bits)
