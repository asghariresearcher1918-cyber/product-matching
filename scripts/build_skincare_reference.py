"""Authoritative reference for branded SKINCARE/topical products the matcher consolidates (same product split across
supplier wordings and categories -> one code). Starts with the Profhilo topical range (IBSA). 'active_class' holds the
site FUNCTION. Usage: python -I scripts/build_skincare_reference.py"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = []


def add(brand, name, function, pack, aliases, src, default=""):
    R.append({"brand": brand, "product_name": name, "active_class": function, "pack": pack,
              "lidocaine": "no", "default": default, "aliases": "|".join(aliases), "source": src})


IBSA = "https://ibsaderma.com/products/profhilo/"
add("Profhilo", "Profhilo Haenkenium Cream", "Moisturiser / cream", "50ml", ["haenkenium"], IBSA)
add("Profhilo", "Profhilo Figura Body Cream", "Moisturiser / cream", "150ml", ["figura"], IBSA)
add("Profhilo", "Profhilo Pura Micellar Water", "Cleanser / wash", "400ml", ["pura", "micellar"], IBSA)

out = ROOT / "data/reference/skincare.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["brand", "product_name", "active_class", "pack", "lidocaine", "default", "aliases", "source"])
    w.writeheader(); w.writerows(R)
print("wrote", out, "-", len(R), "products")
