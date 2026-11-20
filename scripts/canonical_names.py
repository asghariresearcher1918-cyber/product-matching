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
    import html as _html
    t = _html.unescape(t)                               # &amp; -> & , &deg; -> ° etc.
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


SIZE_RX = re.compile(r"\d+\s*(ml|mg|mcg|g|%|iu)\b|\d+g\b", re.I)
PACK_RX = re.compile(r"\d+\s*x\s*\d|pack of|box of|\bx\s*\d+|single|double|\bkit\b|vials?|syringes?", re.I)
NOISE_RX = re.compile(r"stock item|vat|prescription item|out of stock|appropriate training|available on request", re.I)


def main():
    rows = [r for r in csv.DictReader(open(ROOT / "catalogue/final/master_listing_index.csv", encoding="utf-8")) if r.get("listing_title")]

    # 1) per (category, pharmacy) title-quality score: how often titles carry size + pack, penalising noise
    q = collections.defaultdict(lambda: [0, 0.0])
    for r in rows:
        t = r["listing_title"]
        s = (1 if SIZE_RX.search(t) else 0) + (1 if PACK_RX.search(t) else 0) - (1.5 if NOISE_RX.search(t) else 0)
        k = (r["category"], r["supplier"]); q[k][0] += 1; q[k][1] += s
    score = {k: v[1] / v[0] for k, v in q.items()}   # mean title-quality per pharmacy within a category

    # 2) group listings by product; pick the title from the best-ranked pharmacy for that category
    byuid = collections.defaultdict(list)
    for r in rows:
        byuid[r["uid"]].append(r)
    out, ranked_cats = [], {}
    for uid, lst in byuid.items():
        cat = lst[0]["category"]
        # best pharmacy first (category score), then the most complete (longest cleaned) of its titles
        best = max(lst, key=lambda r: (score.get((cat, r["supplier"]), -9), len(clean(r["listing_title"]))))
        nm = clean(best["listing_title"])
        nm = recase(nm) if nm == nm.lower() else nm
        out.append({"uid": uid, "name": nm, "title_source": best["supplier"]})
        ranked_cats.setdefault(cat, sorted({r["supplier"] for r in rows if r["category"] == cat},
                                           key=lambda s: -score.get((cat, s), -9)))
    with open(ROOT / "catalogue/final/canonical_names.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["uid", "name", "title_source"]); w.writeheader(); w.writerows(out)
    # write the per-category pharmacy priority used (for transparency / owner review)
    with open(ROOT / "catalogue/final/title_source_priority.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["category", "pharmacy_priority (best title source first)"])
        for cat, order in sorted(ranked_cats.items()):
            w.writerow([cat, " > ".join(order[:8])])
    print("wrote canonical_names.csv:", len(out), "codes; title_source_priority.csv:", len(ranked_cats), "categories")


if __name__ == "__main__":
    main()
