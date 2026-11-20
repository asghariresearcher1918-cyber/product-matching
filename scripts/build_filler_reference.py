"""Write the authoritative UK filler reference (top brands) that the matcher maps supplier listings to.
Sources: manufacturer / UK distributor listings (Teoxane, Juvederm/Allergan, Vivacy, Galderma, Merz, Across).
Each product: brand, product_name (real commercial name), pack, lidocaine (yes/no/both/detect), default (match when brand
seen but no specific line), aliases (| separated substrings, lower-case), source. Longest matched alias wins.
Usage: python -I scripts/build_filler_reference.py"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = []  # brand, product_name, pack, lidocaine, default, aliases, source


def add(brand, name, pack, lido, aliases, src, default=""):
    R.append({"brand": brand, "product_name": name, "pack": pack, "lidocaine": lido,
              "default": default, "aliases": "|".join(aliases), "source": src})


# ---- Teoxane / Teosyal (RHA = lidocaine-FREE; PureSense = WITH lidocaine) ----
TX = "https://www.teoxane.com"
add("Teosyal", "Teosyal RHA 1", "2 x 1ml", "no", ["rha 1", "rha1", "rha one"], TX)
add("Teosyal", "Teosyal RHA 2", "2 x 1ml", "no", ["rha 2", "rha2", "rha two"], TX)
add("Teosyal", "Teosyal RHA 3", "2 x 1ml", "no", ["rha 3", "rha3", "rha three"], TX)
add("Teosyal", "Teosyal RHA 4", "2 x 1ml", "no", ["rha 4", "rha4", "rha four"], TX)
add("Teosyal", "Teosyal RHA Kiss", "2 x 0.7ml", "no", ["rha kiss"], TX)
add("Teosyal", "Teosyal PureSense Redensity I", "2 x 1ml", "yes", ["redensity 1", "redensity i ", "redensity i(", "redensity1", "redensity one", "redensity mesotherapy"], TX)
add("Teosyal", "Teosyal PureSense Redensity II", "2 x 1ml", "yes", ["redensity 2", "redensity ii", "redensity2", "redensity two"], TX)
add("Teosyal", "Teosyal PureSense Ultra Deep", "2 x 1.2ml", "yes", ["ultra deep", "ultradeep", "ultra-deep"], TX)
add("Teosyal", "Teosyal PureSense Deep Lines", "2 x 1ml", "yes", ["deep lines", "deeplines"], TX)
add("Teosyal", "Teosyal PureSense Global Action", "2 x 1ml", "yes", ["global action"], TX)
add("Teosyal", "Teosyal PureSense Kiss", "2 x 1ml", "yes", ["puresense kiss", "pure sense kiss", " kiss"], TX)
add("Teosyal", "Teosyal First Lines / Touch Up", "2 x 1ml", "yes", ["first lines", "touch up", "touchup"], TX)
add("Teosyal", "Teosyal (unspecified)", "2 x 1ml", "detect", [], TX, default="yes")

# ---- Juvederm / Allergan (all with lidocaine) ----
JV = "https://www.juvederm.co.uk"
add("Juvederm", "Juvederm Ultra 2", "2 x 0.55ml", "yes", ["ultra 2", "ultra2", "ultra smile"], JV)  # ultra smile ~0.55ml too
add("Juvederm", "Juvederm Ultra 3", "2 x 1ml", "yes", ["ultra 3", "ultra3"], JV)
add("Juvederm", "Juvederm Ultra 4", "2 x 1ml", "yes", ["ultra 4", "ultra4"], JV)
add("Juvederm", "Juvederm Volbella", "2 x 1ml", "yes", ["volbella"], JV)
add("Juvederm", "Juvederm Volift Retouch", "2 x 0.55ml", "yes", ["volift retouch", "retouch"], JV)
add("Juvederm", "Juvederm Volift", "2 x 1ml", "yes", ["volift"], JV)
add("Juvederm", "Juvederm Voluma", "2 x 1ml", "yes", ["voluma"], JV)
add("Juvederm", "Juvederm Volux", "2 x 1ml", "yes", ["volux"], JV)
add("Juvederm", "Juvederm Volite", "2 x 1ml", "yes", ["volite"], JV)
add("Juvederm", "Juvederm Skinvive", "2 x 1ml", "yes", ["skinvive"], JV)
add("Juvederm", "Juvederm (unspecified)", "2 x 1ml", "yes", [], JV, default="yes")

# ---- Stylage / Vivacy ----
ST = "https://www.vivacy.com"
add("Stylage", "Stylage HydroMax", "1 x 1ml", "detect", ["hydromax", "hydro max"], ST)
add("Stylage", "Stylage Hydro", "1 x 1ml", "detect", ["stylage hydro", "hydro "], ST)
add("Stylage", "Stylage Special Lips", "1 x 1ml", "yes", ["special lips", "lips plus", "bi-soft lips", "bi soft lips"], ST)
add("Stylage", "Stylage XXL", "2 x 1ml", "yes", ["xxl"], ST)
add("Stylage", "Stylage XL", "2 x 1ml", "yes", ["xl"], ST)
add("Stylage", "Stylage L", "2 x 1ml", "yes", ["stylage l", "bi-soft l", "bi soft l", "bi-flex l", " l (", " l("], ST)
add("Stylage", "Stylage M", "2 x 1ml", "yes", ["stylage m", "bi-soft m", "bi soft m", "bi-flex m", " m (", " m("], ST)
add("Stylage", "Stylage S", "2 x 0.8ml", "yes", ["stylage s", "bi-soft s", "bi soft s", "bi-flex s", " s (", " s("], ST)
add("Stylage", "Stylage (unspecified)", "2 x 1ml", "detect", [], ST, default="detect")

# ---- Restylane / Galderma (mostly 1 x 1ml single syringe) ----
RS = "https://www.restylane.co.uk"
add("Restylane", "Restylane Kysse", "1 x 1ml", "yes", ["kysse"], RS)
add("Restylane", "Restylane Lyft", "1 x 1ml", "detect", ["lyft", "perlane"], RS)
add("Restylane", "Restylane Defyne", "1 x 1ml", "yes", ["defyne"], RS)
add("Restylane", "Restylane Refyne", "1 x 1ml", "yes", ["refyne"], RS)
add("Restylane", "Restylane Volyme", "1 x 1ml", "yes", ["volyme"], RS)
add("Restylane", "Restylane Eyelight", "1 x 0.5ml", "yes", ["eyelight"], RS)
add("Restylane", "Restylane Skinboosters Vital Light", "1 x 1ml", "detect", ["vital light"], RS)
add("Restylane", "Restylane Skinboosters Vital", "1 x 1ml", "detect", ["vital"], RS)
add("Restylane", "Restylane Lip Volume", "1 x 1ml", "yes", ["lip volume"], RS)
add("Restylane", "Restylane (original)", "1 x 1ml", "detect", [], RS, default="detect")

# ---- Belotero / Merz ----
BL = "https://merz-aesthetics.co.uk/belotero/"
add("Belotero", "Belotero Volume", "2 x 1ml", "detect", ["volume"], BL)
add("Belotero", "Belotero Intense", "1 x 1ml", "detect", ["intense"], BL)
add("Belotero", "Belotero Balance", "1 x 1ml", "detect", ["balance"], BL)
add("Belotero", "Belotero Soft", "1 x 1ml", "detect", ["soft"], BL)
add("Belotero", "Belotero Lips Shape", "1 x 0.6ml", "yes", ["lips shape", "lip shape"], BL)
add("Belotero", "Belotero Lips Contour", "1 x 0.6ml", "yes", ["lips contour", "lip contour"], BL)
add("Belotero", "Belotero Revive", "1 x 1ml", "detect", ["revive"], BL)
add("Belotero", "Belotero Hydro", "1 x 1ml", "no", ["hydro"], BL)
add("Belotero", "Belotero (unspecified)", "1 x 1ml", "detect", [], BL, default="detect")

# ---- Aessoa / Oreon Life Science (4 products, each 1 x 1ml, all with lidocaine) ----
AE = "https://www.teleta.co.uk/product-category/dermal-fillers/aessoa-dermal-fillers/"
add("Aessoa", "Aessoa Shine", "1 x 1ml", "yes", ["shine"], AE)
add("Aessoa", "Aessoa Global", "1 x 1ml", "yes", ["global"], AE)
add("Aessoa", "Aessoa Deep", "1 x 1ml", "yes", ["deep"], AE)
add("Aessoa", "Aessoa Ultra", "1 x 1ml", "yes", ["ultra"], AE)

# ---- Revolax / Across (all 1 x 1.1ml, lidocaine common) ----
RV = "https://www.revolax.co.uk"
add("Revolax", "Revolax Sub-Q", "1 x 1.1ml", "detect", ["sub-q", "sub q", "subq"], RV)
add("Revolax", "Revolax Deep", "1 x 1.1ml", "detect", ["deep"], RV)
add("Revolax", "Revolax Fine", "1 x 1.1ml", "detect", ["fine"], RV)
add("Revolax", "Revolax (unspecified)", "1 x 1.1ml", "detect", [], RV, default="detect")

out = ROOT / "data/reference/fillers.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["brand", "product_name", "pack", "lidocaine", "default", "aliases", "source"])
    w.writeheader(); w.writerows(R)
print("wrote", out, "-", len(R), "reference products across", len(set(r["brand"] for r in R)), "brands")
