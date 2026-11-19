"""Authoritative UK reference for skin-booster brands the matcher maps listings to.
Starts with Profhilo (verified from IBSA). More brands added as they are researched.
Schema: brand, product_name, active_class, pack, lidocaine, default, aliases, source.
Usage: python -I scripts/build_booster_reference.py"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = []


def add(brand, name, cls, pack, aliases, src, default=""):
    R.append({"brand": brand, "product_name": name, "active_class": cls, "pack": pack,
              "lidocaine": "no", "default": default, "aliases": "|".join(aliases), "source": src})


IBSA = "https://ibsaderma.com/products/profhilo/"
# Profhilo family (hologram / UK&ROI packaging is NOT a separate product)
add("Profhilo", "Profhilo Body", "HA bio-remodelling", "1 x 3ml", ["body"], IBSA)
add("Profhilo", "Profhilo Structura", "HA bio-remodelling", "1 x 2ml", ["structura"], IBSA)
add("Profhilo", "Profhilo Haenkenium Cream", "Skincare (topical)", "50ml", ["haenkenium"], IBSA)
add("Profhilo", "Profhilo Figura", "Skincare (topical)", "", ["figura"], IBSA)
add("Profhilo", "Profhilo H+L", "HA bio-remodelling", "1 x 2ml", ["h+l", "h l", "hl ", "hl("], IBSA, default="yes")

out = ROOT / "data/reference/boosters.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["brand", "product_name", "active_class", "pack", "lidocaine", "default", "aliases", "source"])
    w.writeheader(); w.writerows(R)
print("wrote", out, "-", len(R), "products across", len(set(r["brand"] for r in R)), "brands")
