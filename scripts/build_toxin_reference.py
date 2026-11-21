"""Authoritative UK botulinum toxin reference (emc / SmPC). Standardised names, molecule, manufacturer, unit sizes.
Pack (1 vial / twin) and ROI/hologram are attributes, not separate products.
Schema used by reference_match (kind=toxin): brand, product_name, molecule, manufacturer, unit_type, units,
active_class, pack, lidocaine, default, aliases, source.  Usage: python -I scripts/build_toxin_reference.py"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = []
GROUP = "Botulinum toxin type A"


def add(brand, units, mol, manu, ut, aliases, src, default="", volume=""):
    # volume = solution ml per vial for READY-TO-USE liquid toxins; powders reconstitute on use -> no volume
    name = f"{brand} {units} {ut}"
    R.append({"brand": brand, "product_name": name, "molecule": mol, "manufacturer": manu, "unit_type": ut,
              "units": str(units), "volume": volume, "active_class": GROUP, "pack": "1 vial", "lidocaine": "no",
              "default": default, "aliases": "|".join(aliases), "source": src})


E = "https://www.medicines.org.uk/emc/search?q="
# Botox - onabotulinumtoxinA (Allergan/AbbVie)
add("Botox", 50, "onabotulinumtoxinA", "Allergan / AbbVie", "units", ["50"], E + "botox")
add("Botox", 100, "onabotulinumtoxinA", "Allergan / AbbVie", "units", ["100"], E + "botox", default="yes")
add("Botox", 200, "onabotulinumtoxinA", "Allergan / AbbVie", "units", ["200"], E + "botox")
# Azzalure - abobotulinumtoxinA (Galderma) - Speywood units
add("Azzalure", 125, "abobotulinumtoxinA", "Galderma", "Speywood units", ["125"], E + "azzalure", default="yes")
# Dysport - abobotulinumtoxinA (Ipsen / Galderma)
add("Dysport", 300, "abobotulinumtoxinA", "Ipsen / Galderma", "units", ["300"], E + "dysport")
add("Dysport", 500, "abobotulinumtoxinA", "Ipsen / Galderma", "units", ["500"], E + "dysport", default="yes")
# Bocouture - incobotulinumtoxinA (Merz)
add("Bocouture", 50, "incobotulinumtoxinA", "Merz", "units", ["50"], E + "bocouture")
add("Bocouture", 100, "incobotulinumtoxinA", "Merz", "units", ["100"], E + "bocouture", default="yes")
# Xeomin - incobotulinumtoxinA (Merz)
add("Xeomin", 50, "incobotulinumtoxinA", "Merz", "units", ["50"], E + "xeomin")
add("Xeomin", 100, "incobotulinumtoxinA", "Merz", "units", ["100"], E + "xeomin", default="yes")
# Alluzience - abobotulinumtoxinA ready-to-use liquid (Galderma) 125 Speywood units / 0.625ml
add("Alluzience", 125, "abobotulinumtoxinA", "Galderma", "Speywood units", ["125", "alluzience"], E + "alluzience", default="yes", volume="0.625ml")
# Letybo - letibotulinumtoxinA (Hugel)
add("Letybo", 50, "letibotulinumtoxinA", "Hugel", "units", ["50"], E + "letybo")
add("Letybo", 100, "letibotulinumtoxinA", "Hugel", "units", ["100"], E + "letybo", default="yes")
# Nuceiva - prabotulinumtoxinA (Evolus)  (= Jeuveau)
add("Nuceiva", 100, "prabotulinumtoxinA", "Evolus", "units", ["100", "nuceiva", "jeuveau"], E + "nuceiva", default="yes")
# Relfydess - relabotulinumtoxinA ready-to-use liquid (Galderma) 150 units / 1.5ml
add("Relfydess", 150, "relabotulinumtoxinA", "Galderma", "units", ["150", "relfydess", "100 units/ml", "100units/ml"], E + "relfydess", default="yes", volume="1.5ml")

out = ROOT / "data/reference/toxins.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["brand", "product_name", "molecule", "manufacturer", "unit_type", "units",
                                      "volume", "active_class", "pack", "lidocaine", "default", "aliases", "source"])
    w.writeheader(); w.writerows(R)
print("wrote", out, "-", len(R), "toxin products across", len(set(r["brand"] for r in R)), "brands")
