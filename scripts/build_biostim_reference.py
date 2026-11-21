"""Authoritative UK biostimulator (collagen-stimulator) reference. Standardised names, verified active agent
(the equivalence group), manufacturer and standard presentation. One row per real presentation; duplicate codes
(Fillmed JuveLook vs JuveLook, OLD PACKAGING, decimal-split "1 5ml") collapse onto these.
Pack count (1 / 2 vials etc.) is read per-listing from title -> page -> image; `pack` here is only the base/default.
Schema used by reference_match (kind=biostim): brand, product_name, variant, active_agent, equivalence_group,
manufacturer, strength, pack, lidocaine, default, aliases, source.  (volume_ml is derived from `pack` "N x Vml".)
Usage: python -I scripts/build_biostim_reference.py"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = []
# active agent -> buyer-facing equivalence group label (products are comparable within a group)
GRP = {
    "PLLA": "PLLA - poly-L-lactic acid",
    "PDLLA": "PDLLA - poly-D,L-lactic acid (+ HA)",
    "CaHA": "CaHA - calcium hydroxylapatite",
    "CaHA+HA": "CaHA + HA hybrid",
    "PCL": "PCL - polycaprolactone",
    "collagen": "Injectable collagen stimulator",
    "HA booster": "HA skin booster (not a biostimulator)",
    "unknown": "Unconfirmed - ask the supplier",
}


def add(brand, name, variant, agent, manu, strength, pack, aliases, src, default="", lido="no"):
    R.append({"brand": brand, "product_name": name, "variant": variant, "active_agent": agent,
              "equivalence_group": GRP[agent], "manufacturer": manu, "strength": strength, "pack": pack,
              "lidocaine": lido, "default": default, "aliases": "|".join(aliases), "source": src})


# ---- CaHA -------------------------------------------------------------------
add("Radiesse", "Radiesse 1.5ml", "1.5ml", "CaHA", "Merz", "", "1 x 1.5ml",
    ["1.5ml", "1 5ml", "1.5 ml", "(1.5", "1.5)"], "https://www.merzaesthetics.co.uk", default="yes", lido="detect")
add("Radiesse", "Radiesse 3ml", "3ml", "CaHA", "Merz", "", "1 x 3ml",
    ["3ml", "3 ml", "3.0ml", "(3ml", "3.0 ml"], "https://www.merzaesthetics.co.uk", lido="detect")
add("Novuma", "Novuma", "", "CaHA", "Burgeon (Korea) / Vivacy UK", "", "1 x 1.5ml",
    [], "https://vivacy.co.uk", default="yes")
# ---- PLLA -------------------------------------------------------------------
add("Sculptra", "Sculptra", "", "PLLA", "Galderma", "367.5mg per vial", "1 vial",
    [], "https://www.sculptra.co.uk", default="yes")
add("Lanluma", "Lanluma V", "V (face)", "PLLA", "Sinclair", "210mg", "1 x 15ml",
    ["lanluma v", "15ml", "210", " v ", "face"], "https://sinclair.com", default="yes")
add("Lanluma", "Lanluma X", "X (body)", "PLLA", "Sinclair", "630mg", "1 x 40ml",
    ["lanluma x", "40ml", "630", " x ", "body"], "https://sinclair.com")
add("aesPLLA", "aesPLLA", "", "PLLA", "Oreon Life Science (Korea)", "365mg vial (150mg PLLA)", "1 vial",
    ["aesplla", "aes plla"], "", default="yes")
add("Ecolla", "Ecolla", "", "PLLA", "Korea", "365mg vial", "1 vial", [], "", default="yes")
add("PLLACELL", "PLLACELL", "", "PLLA", "Korea", "100mg (PLLA + PN cocktail)", "1 vial", ["pllacell"], "", default="yes")
add("Julaine", "Julaine", "", "PLLA", "Nordberg Medical (Sweden)", "150mg + CMC", "1 vial", [], "", default="yes")
add("StiCol", "StiCol", "", "PLLA", "Korea", "PLLA (+ HA)", "1 vial", ["sticol"], "", default="yes")
add("Olidia", "Olidia", "", "PLLA", "PRP Science (Korea)", "365mg vial", "1 vial", [], "", default="yes")
add("iLLUMA PLLA", "iLLUMA PLLA 200", "200mg", "PLLA", "Korea", "200mg", "1 vial",
    ["200", "illuma plla 200"], "", default="yes")
add("iLLUMA PLLA", "iLLUMA PLLA 500", "500mg", "PLLA", "Korea", "500mg", "1 vial", ["500", "illuma plla 500"], "")
add("PiNkLLA", "PiNkLLA", "", "PLLA", "Daesung (Korea)", "100mg (PLLA + PN)", "1 vial", ["pinklla"], "", default="yes")
# ---- PDLLA (+ HA) -----------------------------------------------------------
add("AestheFill", "AestheFill", "", "PDLLA", "Regen Biotech", "200mg powder", "1 vial",
    ["aesthefill", "aesthe fill"], "", default="yes")
add("Juvelook", "Juvelook", "", "PDLLA", "VAIM / Medit (Korea)", "50mg (PDLLA + HA)", "1 vial",
    [], "", default="yes")
add("Juvelook", "Juvelook Volume", "Volume", "PDLLA", "VAIM / Medit (Korea)", "200mg (PDLLA + HA)", "1 vial",
    ["volume", "200"], "")
add("Lenisna", "Lenisna", "", "PDLLA", "Medit / Fillmed", "200mg (PDLLA + HA)", "1 vial", ["lenisna"], "", default="yes")
# ---- PCL --------------------------------------------------------------------
add("Ellanse", "Ellanse S", "S", "PCL", "Sinclair", "", "1 x 1ml",
    ["ellanse s", "ellanse-s", "ellansé s"], "https://sinclair.com")
add("Ellanse", "Ellanse M", "M", "PCL", "Sinclair", "", "1 x 1ml",
    ["ellanse m", "ellanse-m", "ellansé m"], "https://sinclair.com", default="yes")
add("Ellanse", "Ellanse L", "L", "PCL", "Sinclair", "", "1 x 1ml", ["ellanse l", "ellanse-l"], "https://sinclair.com")
add("Ellanse", "Ellanse E", "E", "PCL", "Sinclair", "", "1 x 1ml", ["ellanse e", "ellanse-e"], "https://sinclair.com")
add("Gouri", "Gouri", "", "PCL", "APAD / Gran Aesthetics", "liquid PCL", "1 x 1ml", ["gouri"], "", default="yes")
# ---- collagen ---------------------------------------------------------------
add("Linerase", "Linerase", "", "collagen", "Mastelli", "100mg (equine Type I collagen)", "1 vial",
    [], "https://mastelli.com", default="yes")
# ---- CaHA + HA hybrid -------------------------------------------------------
add("HArmonyCa", "HArmonyCa", "", "CaHA+HA", "Allergan / AbbVie", "CaHA in HA gel", "2 x 1.25ml",
    ["harmonyca", "harmony ca"], "https://www.allerganaesthetics.co.uk", default="yes", lido="yes")
add("Neauvia", "Neauvia Stimulate", "Stimulate", "CaHA+HA", "Matex Lab / Neauvia", "HA 26mg/ml + 1% CaHA", "1 x 1ml",
    ["stimulate", "organic stimulate"], "https://neauvia.com", default="yes")
# ---- HA booster grouped separately (NOT a collagen stimulator) --------------
add("Linerase Hydro", "Linerase Hydro", "", "HA booster", "Mastelli", "HA booster", "5 x 5ml",
    ["hydro"], "https://mastelli.com", default="yes")
# ---- agent not stated -> flagged for supplier confirmation ------------------
add("Doublyx", "Doublyx Evo", "Evo", "unknown", "not stated", "", "1 x 2ml", ["doublyx"], "", default="yes")
add("Elysiha", "Elysiha", "", "unknown", "not stated", "", "1 vial", ["elysiha"], "", default="yes")

out = ROOT / "data/reference/biostim.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["brand", "product_name", "variant", "active_agent", "equivalence_group",
                                      "manufacturer", "strength", "pack", "lidocaine", "default", "aliases", "source"])
    w.writeheader(); w.writerows(R)
print("wrote", out, "-", len(R), "products across", len(set(r["brand"] for r in R)), "brands")
