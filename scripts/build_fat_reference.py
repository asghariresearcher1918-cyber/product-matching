"""Authoritative UK fat-dissolving (lipolysis) reference. Standardised names, active agent, vial size.
Pack (1/5/10 vials) is an attribute. Schema used by reference_match (kind=fat): brand, product_name, variant,
active_agent, manufacturer, volume, active_class, pack, lidocaine, default, aliases, source.
Usage: python -I scripts/build_fat_reference.py"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = []
DCA, PPC, PROP, LIPO = "Deoxycholic acid", "Phosphatidylcholine (PPC)", "Lecithin / proprietary", "Mesotherapy lipolytic"


def add(brand, name, agent, manu, vol, aliases, src, default="", variant=""):
    R.append({"brand": brand, "product_name": name, "variant": variant, "active_agent": agent, "manufacturer": manu,
              "volume": vol, "active_class": agent, "pack": "1 vial", "lidocaine": "no",
              "default": default, "aliases": "|".join(aliases), "source": src})


add("Aqualyx", "Aqualyx", DCA, "Marllor / Ghimja", "8ml", [], "https://www.aqualyx.com", default="yes")
add("Lemon Bottle", "Lemon Bottle", PROP, "Lemon Bottle (Korea)", "10ml", [], "https://lemonbottle.co.kr", default="yes")
add("Lipo Lab", "Lipo Lab V-Line", PPC, "Lipo Lab (Korea)", "10ml", ["v-line", "v line", "vline"], "https://www.lipolab.co.kr", variant="V-Line")
add("Lipo Lab", "Lipo Lab PPC", PPC, "Lipo Lab (Korea)", "10ml", ["ppc"], "https://www.lipolab.co.kr", default="yes", variant="PPC (body)")
add("DesoFace", "DesoFace", "Deoxycholic acid 0.5%", "Deso (Korea)", "10ml", ["desoface", "deso face"], "https://deso.co.kr", default="yes")
add("DesoBody", "DesoBody", "Deoxycholic acid 1.25%", "Deso (Korea)", "10ml", ["desobody", "deso body"], "https://deso.co.kr", default="yes")
add("Dr. Lipo", "Dr. Lipo V-Line", LIPO, "Dr. Lipo", "10ml", ["v-line", "v line", "vline", "facial"], "", variant="V-Line")
add("Dr. Lipo", "Dr. Lipo Plus (Body)", LIPO, "Dr. Lipo", "10ml", ["body", "plus"], "", default="yes", variant="Body")
add("Kabelline", "Kabelline", DCA, "Kabelline (Korea)", "8ml", [], "", default="yes")
add("The Skinny Bottle", "The Skinny Bottle", PROP, "The Skinny Bottle", "10ml", [], "", default="yes")
add("Pine Bottle", "Pine Bottle", PROP, "Pine Bottle", "10ml", [], "", default="yes")
add("Kabonne", "Kabonne", DCA, "Kabonne (Korea)", "8ml", [], "", default="yes")
add("BCN Adipo", "BCN Adipo Forte", LIPO, "Institute BCN", "10ml", ["adipo"], "", default="yes")
add("Mesoestetic", "Mesoestetic C.Prof 221 Lipolytic", LIPO, "Mesoestetic", "10ml", ["221", "c.prof 221", "lipolytic"], "", default="yes")
add("MesoSculpt", "MesoSculpt C71", LIPO, "MesoSculpt", "1ml", ["c71", "mesosculpt"], "", default="yes")
add("Cincelar", "Cincelar Plus", LIPO, "Cincelar", "8ml", [], "", default="yes")
add("Inno-TDS", "Inno-TDS Draining PPC", PPC, "Innoaesthetics", "5ml", ["draining ppc", "draining"], "", default="yes")
add("Alidya", "Alidya (anti-lipodystrophy)", "Anti-lipodystrophic (cellulite)", "Mastelli", "10ml", [], "", default="yes")

out = ROOT / "data/reference/fat.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["brand", "product_name", "variant", "active_agent", "manufacturer", "volume",
                                      "active_class", "pack", "lidocaine", "default", "aliases", "source"])
    w.writeheader(); w.writerows(R)
print("wrote", out, "-", len(R), "products across", len(set(r["brand"] for r in R)), "brands")
