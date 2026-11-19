"""Derive a real product display name for every catalogue code from the actual supplier listing titles we scraped
(not from our internal code). The commercial name customers search for is already in the listings
(e.g. 'Profhilo H+L (1 x 2ml)'); we were discarding it. For each uid: clean every listing title of supplier noise
(VAT / stock item / prescription item / training / etc.), then pick the most informative common title as the name.
Output: catalogue/final/canonical_names.csv (uid,name,title_variants)
Usage: python -I scripts/canonical_names.py"""
import collections, csv, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NOISE = re.compile(
    r"\b(appropriate training (recommended|required)|training (recommended|required)|"
    r"stock item|prescription item|vat payable|zero vat|no vat|pay vat|incl\.? vat|ex\.? vat|inc vat|plus vat|"
    r"available on request|out of stock|in stock|best seller|bestseller|new in|brand new|"
    r"online( exclusive)?|special offer|clearance|short dated|free delivery|next day|"
    r"buy( now| online)?|shop now|uk stock|genuine|authentic|official)\b", re.I)
TRAIL = re.compile(r"[\s\-–—,|/]+$")
LEAD = re.compile(r"^[\s\-–—,|/]+")
# tokens to keep as-is (not title-cased) when rebuilding case
KEEP = {"H+L", "HL", "RHA", "CE", "PDO", "PLLA", "PCL", "CaHA", "PDRN", "PN", "IU", "PFS", "SPF",
        "ROI", "EU", "UK", "US", "HA", "LED", "RF", "IPL", "DNA", "NCTF", "BR", "XL", "XS"}
UNIT = re.compile(r"^\d+(\.\d+)?(ml|mg|mcg|g|u|iu|%|x|cm|mm|g)?$", re.I)


NOTE = re.compile(r"\b(exp(iry)?\.?\s*\d[\d/\.]*|discontinued|previously[^)]*|medic(s)? only|"
                  r"while stocks last|limited stock|new packaging|new formula)\b", re.I)


def clean(t):
    t = re.sub(r"[®™©]", "", t)          # ® ™ ©
    t = NOISE.sub(" ", t)
    t = NOTE.sub(" ", t)
    # drop parenthetical NOTES (no size/pack digit inside); keep "(1 x 2ml)" etc.
    t = re.sub(r"\(([^)]*)\)", lambda m: m.group(0) if re.search(r"\d", m.group(1)) else " ", t)
    t = re.sub(r"^\s*single\s+", "", t, flags=re.I)     # leading "Single ..."
    t = re.sub(r"\(\s*\)", "", t)
    t = re.sub(r"\s+", " ", t)
    t = LEAD.sub("", TRAIL.sub("", t)).strip()
    t = re.sub(r"\s+[|/,-]\s*$", "", t).strip()
    return t


def recase(t):
    """Title-case words that are all-lowercase; leave already-cased and known tokens alone."""
    out = []
    for w in t.split(" "):
        if not w:
            continue
        bare = w.strip("()[]")
        if bare.upper() in KEEP:
            out.append(w.replace(bare, bare.upper()))
        elif UNIT.match(bare):                            # keep units/dims lowercase (2ml, 25g, 1x2ml)
            out.append(w.lower())
        elif w == w.lower() and re.search(r"[a-z]", w):   # all-lowercase word -> Title
            out.append(w[:1].upper() + w[1:])
        else:
            out.append(w)                                 # already has caps -> trust supplier
    return " ".join(out)


def canonical(titles):
    cleaned = [clean(t) for t in titles]
    cleaned = [c for c in cleaned if len(c) >= 2]
    if not cleaned:
        return "", ""
    # group by case-insensitive key; score = frequency + informativeness (word count)
    groups = collections.defaultdict(list)
    for c in cleaned:
        groups[c.lower()].append(c)
    def score(k):
        return (len(groups[k]) + 0.4 * len(k.split()), len(k))
    best = max(groups, key=score)
    # among raw variants for the winning key, prefer the one that already has good casing
    variants = groups[best]
    cased = max(variants, key=lambda v: (sum(1 for ch in v if ch.isupper()), len(v)))
    name = recase(cased) if cased == cased.lower() else cased
    others = sorted({g for g in groups if g != best}, key=lambda k: -len(groups[k]))[:3]
    return name, " | ".join(others)


def main():
    idx = collections.defaultdict(list)
    for r in csv.DictReader(open(ROOT / "catalogue/final/master_listing_index.csv", encoding="utf-8")):
        if r.get("listing_title"):
            idx[r["uid"]].append(r["listing_title"])
    out = []
    for uid, titles in idx.items():
        name, variants = canonical(titles)
        out.append({"uid": uid, "name": name, "title_variants": variants})
    with open(ROOT / "catalogue/final/canonical_names.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["uid", "name", "title_variants"]); w.writeheader(); w.writerows(out)
    print("wrote canonical_names.csv:", len(out), "codes")
    # sample
    names = {r["uid"]: r["name"] for r in out}
    for pat in ["BST:PROFHILO", "FIL:", "BST:SUNEKOS", "BST:NUCLEOFILL"]:
        print(f"\n{pat} examples:")
        for uid, nm in list(names.items()):
            if uid.startswith(pat): print(f"  {uid:34} -> {nm}")
            if sum(1 for u in names if u.startswith(pat) and list(names).index(u) <= list(names).index(uid)) >= 6: break


if __name__ == "__main__":
    main()
