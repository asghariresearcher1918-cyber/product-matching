"""Authoritative UK reference for skin-booster brands the matcher maps listings to.
Verified from manufacturer / UK distributor sources (IBSA, Professional Derma, Promoitalia, Fox Pharma).
Schema: brand, product_name, active_class, pack, lidocaine, default, aliases, source. Longest matching alias wins.
Usage: python -I scripts/build_booster_reference.py"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = []
HA, AMINO, PN, SK = "HA bio-remodelling", "Amino-acid skin booster", "Polynucleotide / PDRN", "Skincare (topical)"


def add(brand, name, cls, pack, aliases, src, default=""):
    R.append({"brand": brand, "product_name": name, "active_class": cls, "pack": pack,
              "lidocaine": "no", "default": default, "aliases": "|".join(aliases), "source": src})


# ---- Profhilo (IBSA) - hologram/UK&ROI packaging is NOT a separate product ----
IBSA = "https://ibsaderma.com/products/profhilo/"
add("Profhilo", "Profhilo Body Kit", HA, "2 x 3ml", ["body kit"], IBSA)   # supplier titles say "Body Kit" = 2 x 3ml
add("Profhilo", "Profhilo Body", HA, "1 x 3ml", ["body"], IBSA)
add("Profhilo", "Profhilo Structura", HA, "1 x 2ml", ["structura"], IBSA)
add("Profhilo", "Profhilo H+L", HA, "1 x 2ml", ["h+l", "h l", "hl ", "hl("], IBSA, default="yes")
# Haenkenium / Figura / Pura are TOPICAL (skincare) - handled in data/reference/skincare.csv, not here

# ---- Sunekos (Professional Derma) ----
SUN = "https://sunekos.com"
add("Sunekos", "Sunekos 1200", AMINO, "2 x 1.5ml", ["1200"], SUN)
add("Sunekos", "Sunekos 200", AMINO, "2 x 3ml", ["200"], SUN)
add("Sunekos", "Sunekos Performa", AMINO, "2 x 3.5ml", ["performa"], SUN)
add("Sunekos", "Sunekos Body", AMINO, "10ml", ["body"], SUN)
add("Sunekos", "Sunekos Cell", AMINO, "4.5ml + 10.5ml", ["cell"], SUN)
add("Sunekos", "Sunekos (unspecified)", AMINO, "2 x 1.5ml", [], SUN, default="yes")

# ---- Nucleofill (Promoitalia) - 20=Medium, 25=Strong, Eyes=Soft Plus ----
NUC = "https://officialnucleofill.co.uk/"
add("Nucleofill", "Nucleofill Strong Plus", PN, "1 x 2ml", ["strong plus"], NUC)
add("Nucleofill", "Nucleofill Strong", PN, "1 x 1.5ml", ["strong", "nucleofill 25", " 25 "], NUC)
add("Nucleofill", "Nucleofill Medium Plus (Hair)", PN, "1 x 2ml", ["medium plus", "hair"], NUC)
add("Nucleofill", "Nucleofill Medium", PN, "1 x 1.5ml", ["medium", "nucleofill 20", " 20 "], NUC)
add("Nucleofill", "Nucleofill Soft Plus (Eyes)", PN, "1 x 2ml", ["soft plus", "soft", "eyes", "eye"], NUC)
add("Nucleofill", "Nucleofill (unspecified)", PN, "1 x 2ml", [], NUC, default="yes")

# ---- Jalupro (Professional Derma) ----
JAL = "https://jalupro.com"
add("Jalupro", "Jalupro Super Hydro", AMINO, "1 x 2.5ml", ["super hydro", "superhydro"], JAL)
add("Jalupro", "Jalupro HMW", AMINO, "1.5ml + 1ml", ["hmw", "h.m.w"], JAL)
add("Jalupro", "Jalupro Young Eye", AMINO, "1 x 1ml", ["young eye", "young eyes"], JAL)
add("Jalupro", "Jalupro Classic", AMINO, "2 x 3ml", ["classic"], JAL, default="yes")

# ---- Seventy Hyal 2000 (Fox Pharma) ----
SH = "https://foxpharma.co.uk/product/seventy-hyal-2000"
add("Seventy Hyal", "Seventy Hyal 2000", HA, "1 x 2ml", ["seventy hyal", "70 hyal"], SH, default="yes")

out = ROOT / "data/reference/boosters.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["brand", "product_name", "active_class", "pack", "lidocaine", "default", "aliases", "source"])
    w.writeheader(); w.writerows(R)
print("wrote", out, "-", len(R), "products across", len(set(r["brand"] for r in R)), "brands")
