"""Authoritative UK biostimulator (collagen-stimulator) reference. Clean CANONICAL commercial names (no synthesised
spec in the name), verified active agent = the scientific equivalence group, manufacturer, standard presentation and a
SOURCE link per brand. One row per real presentation; the matcher reads each listing's pack/lido and builds the final
display name as "<canonical> [with Lidocaine] (<market pack>)" so it reads like the real market name.
Schema (kind=biostim): brand, product_name, variant, active_agent, equivalence_group, manufacturer, strength, pack,
lidocaine, default, aliases, source.  Gels carry volume via pack "N x V ml"; powders carry strength (mg) and pack "1 vial".
Usage: python -I scripts/build_biostim_reference.py"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = []
GRP = {
    "PLLA": "PLLA - poly-L-lactic acid",
    "PDLLA": "PDLLA - poly-D,L-lactic acid (+ HA)",
    "CaHA": "CaHA - calcium hydroxylapatite",
    "CaHA+HA": "CaHA + HA hybrid",
    "PCL": "PCL - polycaprolactone",
    "collagen": "Injectable collagen stimulator",
    "HA booster": "HA skin booster (not a biostimulator)",
    "topical": "Topical serum PDRN/HA/collagen (not a biostimulator - move to Skincare)",
    "unknown": "Unconfirmed - ask the supplier",
}


def add(brand, name, variant, agent, manu, strength, pack, aliases, src, default="", lido="no"):
    R.append({"brand": brand, "product_name": name, "variant": variant, "active_agent": agent,
              "equivalence_group": GRP[agent], "manufacturer": manu, "strength": strength, "pack": pack,
              "lidocaine": lido, "default": default, "aliases": "|".join(aliases), "source": src})


# ---- CaHA (gels; volume via pack) -------------------------------------------
add("Radiesse", "Radiesse", "1.5ml", "CaHA", "Merz", "", "1 x 1.5ml",
    ["1.5ml", "1 5ml", "1.5 ml", "(1.5", "1.5)"], "https://www.merzaesthetics.co.uk", default="yes", lido="detect")
add("Radiesse", "Radiesse", "3ml", "CaHA", "Merz", "", "1 x 3ml",
    ["3ml", "3 ml", "3.0ml", "(3ml", "3.0 ml"], "https://www.merzaesthetics.co.uk", lido="detect")
add("Novuma", "Novuma", "", "CaHA", "Burgeon (Korea) / Vivacy UK", "", "1 x 1.5ml",
    [], "https://vivacy.co.uk", default="yes")
# ---- PLLA (powders; strength in mg) -----------------------------------------
add("Sculptra", "Sculptra", "", "PLLA", "Galderma", "367.5mg", "1 vial",
    [], "https://www.galderma.com/uk", default="yes")
# -- niche brands: manufacturer / UK distributor confirmed by research (2026-11-22) --
add("Lanluma", "Lanluma V", "V (face)", "PLLA", "Sinclair", "210mg", "1 vial",
    ["lanluma v", "15ml", "210", "face"], "https://sinclair.com", default="yes")
add("Lanluma", "Lanluma X", "X (body)", "PLLA", "Sinclair", "630mg", "1 vial",
    ["lanluma x", "40ml", "630", "body"], "https://sinclair.com")
add("aesPLLA", "aesPLLA", "", "PLLA", "Oreon Life Science (Korea); Fox Pharma exclusive UK/EU", "365mg", "1 vial",
    ["aesplla", "aes plla"], "https://support.foxpharma.co.uk/en-gb/what-is-aesplla", default="yes")
add("Ecolla", "Ecolla", "", "PLLA", "JETEMA (Korea)", "365mg", "1 vial", [], "https://www.jetema.com", default="yes")
add("PLLACELL", "PLLACELL", "", "PLLA", "Korea", "100mg", "1 vial", ["pllacell"], "", default="yes")
add("Julaine", "Julaine", "", "PLLA", "Nordberg Medical (Sweden); own UK & Ireland arm", "150mg", "1 vial", [], "https://www.nordbergmedical.com", default="yes")
add("StiCol", "StiCol Volume", "Volume", "PLLA", "Contac Korea", "365mg", "1 vial", ["sticol", "volume"], "https://sticolfiller.com", default="yes")
add("Olidia", "Olidia", "", "PLLA", "PRP Science (Korea)", "365mg", "1 vial", [], "https://olidia.kr", default="yes")
add("iLLUMA PLLA", "iLLUMA PLLA 200", "200mg", "PLLA", "LINKUS GLOBAL (Korea)", "200mg", "1 vial",
    ["200", "illuma plla 200"], "https://linkusglobal.kr/portfolio/illuma-plla/", default="yes")
add("iLLUMA PLLA", "iLLUMA PLLA 500", "500mg", "PLLA", "LINKUS GLOBAL (Korea)", "500mg", "1 vial",
    ["500", "illuma plla 500"], "https://linkusglobal.kr/portfolio/illuma-plla/")
add("PiNkLLA", "PiNkLLA", "", "PLLA", "Oreon Life Science (Korea)", "100mg", "1 vial", ["pinklla"], "", default="yes")
# ---- PDLLA (+ HA) powders ---------------------------------------------------
add("AestheFill", "AestheFill", "", "PDLLA", "Regen Biotech (Korea)", "200mg", "1 vial",
    ["aesthefill", "aesthe fill"], "https://www.tga.gov.au/resources/artg/402703", default="yes")
add("Juvelook", "Juvelook", "", "PDLLA", "VAIM (Korea); Fillmed UK & Ireland", "50mg", "1 vial", [], "https://uk.fillmed.com", default="yes")
add("Juvelook", "Juvelook Volume", "Volume", "PDLLA", "VAIM (Korea); Fillmed UK & Ireland (= Lenisna globally)", "200mg", "1 vial", ["volume", "200"], "https://uk.fillmed.com")
add("Lenisna", "Lenisna", "", "PDLLA", "VAIM (Korea); Fillmed UK & Ireland", "200mg", "1 vial", ["lenisna"], "https://uk.fillmed.com", default="yes")
# ---- PCL (gels/liquid) ------------------------------------------------------
add("Ellanse", "Ellanse S", "S", "PCL", "Sinclair", "", "1 x 1ml",
    ["ellanse s", "ellanse-s", "ellansé s"], "https://sinclair.com")
add("Ellanse", "Ellanse M", "M", "PCL", "Sinclair", "", "1 x 1ml",
    ["ellanse m", "ellanse-m", "ellansé m"], "https://sinclair.com", default="yes")
add("Ellanse", "Ellanse L", "L", "PCL", "Sinclair", "", "1 x 1ml", ["ellanse l", "ellanse-l"], "https://sinclair.com")
add("Ellanse", "Ellanse E", "E", "PCL", "Sinclair", "", "1 x 1ml", ["ellanse e", "ellanse-e"], "https://sinclair.com")
add("Gouri", "Gouri", "", "PCL", "DEXLEVO (Korea)", "", "1 x 1ml", ["gouri"], "https://www.dexlevo.com", default="yes")
# ---- collagen ---------------------------------------------------------------
add("Linerase", "Linerase", "", "collagen", "Mastelli (equine Type I collagen)", "100mg", "1 vial",
    [], "https://mastelli.com", default="yes")
# ---- CaHA + HA hybrid (gels) ------------------------------------------------
add("HArmonyCa", "HArmonyCa", "", "CaHA+HA", "Allergan / AbbVie", "", "2 x 1.25ml",
    ["harmonyca", "harmony ca"], "https://www.allerganaesthetics.co.uk", default="yes", lido="yes")
add("Neauvia", "Neauvia Stimulate", "Stimulate", "CaHA+HA", "Matex Lab / Neauvia", "", "1 x 1ml",
    ["stimulate", "organic stimulate"], "https://neauvia.com", default="yes")
# NOTE: Linerase Hydro + Doublyx Evo (HA boosters) and Elysiha (topical serum) were moved out of this category
# to Skin booster / Skincare via data/category_overrides.csv (owner decision 2026-11-23).

out = ROOT / "data/reference/biostim.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["brand", "product_name", "variant", "active_agent", "equivalence_group",
                                      "manufacturer", "strength", "pack", "lidocaine", "default", "aliases", "source"])
    w.writeheader(); w.writerows(R)
print("wrote", out, "-", len(R), "products across", len(set(r["brand"] for r in R)), "brands")
