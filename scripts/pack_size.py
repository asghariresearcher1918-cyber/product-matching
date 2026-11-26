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
    for rx, mn in ((r"pack of\s*(\d+)", 1), (r"box of\s*(\d+)", 1),
                   (r"(\d+)\s*(?:pieces?|pcs|ct\b|count|pairs?|sheets?|wipes?|swabs?|rolls?|tabs?|tablets?|caps?|sachets?)\b", 2),
                   (r"\b(\d+)\s*['’]s\b", 2), (r"(\d+)\s*pack\b", 2), (r"x\s*(\d+)\b", 2)):
        m = re.search(rx, name or "", re.I)
        if m and mn <= int(m.group(1)) <= 10000:
            return str(int(m.group(1)))
    return ""


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


def pack_label(size, qty):
    """Short human label for a product subtitle: 'size · pack of N'. A single-unit pack adds no 'pack of 1' noise."""
    bits = []
    if size:
        bits.append(size)
    if qty and str(qty) not in ("", "1"):
        bits.append(f"pack of {qty}")
    elif str(qty) == "1" and not size:
        bits.append("single unit")
    return " · ".join(bits)
