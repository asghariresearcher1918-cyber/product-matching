"""Step-3 decisions for the 41-row sample (sample_ids.txt), made by Claude inside the working session
(no API key available yet) with the SAME rules and output schema as scripts/classify_llm.py.
Each decision is based on the page text and image shown to the reviewer; quotes are verbatim.
Writes llm_results/<id>.json marked decided_by=claude-session. Usage: python -I data/session_decisions.py"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = dict(kind="product", variant_id="", presentation_id="", proposed_line="", lidocaine="not_stated", lidocaine_source="none",
            market="not_stated", strength="", unit_type="not_stated", unit_count="", unit_volume_ml="", pack_source="none",
            status_words=[], options_seen=[], image_reads="", image_matches_text="no_image", evidence=[], conflicts=[],
            confidence="likely", needs_human_review=False, review_reason="")


def E(src, q):
    return {"source": src, "quote": q}


BTX = dict(family_id="F-botox", variant_id="F-botox/100-allergan-units", presentation_id="F-botox/100-allergan-units/1xvial",
           strength="100 Allergan Units", unit_type="vial", unit_count="1", lidocaine="no", market="UK/CE")
TEO3 = dict(family_id="F-teosyal-rha-3", variant_id="F-teosyal-rha-3/lidocaine-0-3", lidocaine="yes", unit_type="syringe", market="UK/CE")
REV = dict(family_id="F-revolax-deep", lidocaine="yes", unit_type="syringe", unit_count="1", unit_volume_ml="1.1")
VOL = dict(family_id="F-juvederm-volift", lidocaine="yes", unit_type="syringe", unit_volume_ml="1")
STR = dict(family_id="F-profhilo-structura", lidocaine="no", unit_type="syringe", unit_count="1", unit_volume_ml="2")

D = {
    # ---------------- BOTOX 100 ----------------
    "R10093": BTX | dict(pack_source="image", image_matches_text="yes", image_reads="BOTOX 100 Allergan Units, one vial, AbbVie carton",
                         evidence=[E("page_title", "Botox 100u"), E("image", "BOTOX 100 Allergan Units One vial contains 100 Allergan Units")],
                         status_words=["Prescription required"], confidence="confirmed",
                         review_reason="page has no description; strength from page title, carton (1 vial) from image"),
    "R06964": BTX | dict(pack_source="page_text", image_matches_text="yes", image_reads="BOTOX 100 Allergan Units carton, Allergan",
                         evidence=[E("page_text", "Each vial contains 100 Allergan Units of botulinum toxin type A"), E("page_title", "BOTOX 100 Allergan Units (Single Vial)")],
                         confidence="confirmed"),
    "R05521": BTX | dict(pack_source="page_title", image_matches_text="yes", image_reads="BOTOX 100 Allergan Units, AbbVie",
                         evidence=[E("page_title", "BOTOX 100iu (1 x vial)"), E("page_text", "This BOTOX 100IU vial contains clostridium botulinum")],
                         options_seen=["dose-instruction selector (not a product option)"], confidence="confirmed"),
    "R03166": BTX | dict(pack_source="image", image_matches_text="yes", image_reads="BOTOX 100 Allergan Units, one vial, AbbVie",
                         evidence=[E("page_text", "EMC: https://www.medicines.org.uk/emc/product/859/smpc"), E("image", "One vial contains 100 Allergan Units")],
                         confidence="confirmed", review_reason="page links the official emc SmPC 859 (BOTOX 100)"),
    "R00666": BTX | dict(pack_source="page_text", image_matches_text="yes", image_reads="BOTOX 100 Allergan Units, Allergan, Church sticker",
                         evidence=[E("page_text", "Size: 1 x 100u Form: Vial"), E("page_text", "Administered via intramuscular injection")],
                         status_words=["Cold Chain", "POM"], confidence="confirmed"),
    "R06342": BTX | dict(pack_source="page_text", market="not_stated",
                         evidence=[E("page_text", "Each box of Botox 100 Units contains: - 1 vial of Botox (100 Units) for injection.")],
                         conflicts=["page calls it 'FDA-approved' (US wording); UK BOTOX is an MHRA-licensed POM - market of stock not confirmed"],
                         confidence="likely", needs_human_review=True, review_reason="no image; US 'FDA-approved' wording - confirm UK-licensed stock"),
    # ---------------- AZZALURE ----------------
    "R06321": dict(family_id="F-azzalure", variant_id="F-azzalure/125-speywood-units", presentation_id="F-azzalure/125-speywood-units/1xvial",
                   strength="125 Speywood units", unit_type="vial", unit_count="2", pack_source="page_title", lidocaine="no", market="UK/CE",
                   evidence=[E("page_title", "Azzalure 2 x 125 units"), E("page_text", "Azzalure, 125 Speywood units, powder for solution for injection")],
                   confidence="likely", review_reason="vial count only in page title (description is the SmPC text, no pack count); no image"),
    "R00528": dict(family_id="F-azzalure", variant_id="F-azzalure/125-speywood-units", presentation_id="F-azzalure/125-speywood-units/1xvial",
                   strength="125 Speywood units", unit_type="vial", unit_count="2", pack_source="page_text", lidocaine="no", market="UK/CE",
                   image_matches_text="yes", image_reads="Azzalure 125 Speywood units, 2 vials, Intramuscular use, Galderma",
                   evidence=[E("page_text", "Size: 2 x 125 Speywood units Form: Vial"), E("image", "125 Speywood units ... 2 VIALS ... Intramuscular use")],
                   status_words=["Limited Stock", "Cold Chain", "POM"], confidence="confirmed"),
    "R10245": dict(family_id="F-azzalure", kind="marketing_or_accessory", proposed_line="Azzalure bottle opener (accessory)",
                   evidence=[E("page_text", "This opener easily opens azzalure bottles, and most other aesthetic bottles")],
                   confidence="confirmed", review_reason="accessory sold under the brand name, not the medicine"),
    "R04482": dict(family_id="F-azzalure", variant_id="F-azzalure/125-speywood-units", presentation_id="F-azzalure/125-speywood-units/1xvial",
                   strength="125 Speywood units", unit_type="vial", unit_count="1", pack_source="page_text", lidocaine="no", market="UK/CE",
                   image_matches_text="yes", image_reads="single Azzalure 125 Speywood units vial",
                   evidence=[E("page_text", "Azzalure 1 x 125 Speywood units vials Botulinum Toxin Type A"), E("page_text", "Size and Care Info 1 x 125U")],
                   confidence="confirmed"),
    # ---------------- ALLUZIENCE ----------------
    "R06050": dict(family_id="F-alluzience", variant_id="F-alluzience/125-speywood-units-200-su-ml-0-625-ml",
                   presentation_id="F-alluzience/125-speywood-units-200-su-ml-0-625-ml/1xvial", strength="125 Speywood units (200 SU/ml)",
                   unit_type="vial", unit_count="2", pack_source="image", lidocaine="no", market="UK/CE", image_matches_text="yes",
                   image_reads="Alluzience 200 Speywood units/ml, each vial 125 Speywood units, 2 vials, Galderma",
                   evidence=[E("page_title", "Alluzience 125iu (TWIN PACK 2 Vials )"), E("image", "200 Speywood units/ml ... Each vial contains 125 Speywood units ... 2 vials")],
                   status_words=["Prescription Item (VAT FREE)"], options_seen=["Prescription Item (VAT FREE)"], confidence="confirmed"),
    "R05488": dict(family_id="F-alluzience", variant_id="F-alluzience/125-speywood-units-200-su-ml-0-625-ml",
                   presentation_id="F-alluzience/125-speywood-units-200-su-ml-0-625-ml/1xvial", strength="125 Speywood units (200 SU/ml)",
                   unit_type="vial", unit_count="2", pack_source="image", lidocaine="no", market="UK/CE", image_matches_text="yes",
                   image_reads="Alluzience 200 Speywood units/ml, 2 vials, Intramuscular use",
                   evidence=[E("page_title", "Alluzience 2 x 125 Units"), E("page_text", "the first ready-to-use liquid neurotoxin in the UK")],
                   confidence="confirmed"),
    "N00006": dict(family_id="F-alluzience", variant_id="F-alluzience/125-speywood-units-200-su-ml-0-625-ml",
                   presentation_id="F-alluzience/125-speywood-units-200-su-ml-0-625-ml/1xvial", strength="125 Speywood units (200 SU/ml)",
                   unit_type="vial", unit_count="1", pack_source="page_title", lidocaine="no", market="UK/CE", image_matches_text="yes",
                   image_reads="2-vial Alluzience carton with a 'SINGLE VIAL' badge",
                   evidence=[E("page_title", "Alluzience SINGLE VIAL 200 Speywood units/ml (Split Pack May Not Include Original Box)")],
                   status_words=["POM"], confidence="likely",
                   review_reason="split pack: one vial taken from a 2-vial carton, may come without original box - not a manufacturer pack"),
    # ---------------- BOCOUTURE ----------------
    "R05520": dict(family_id="F-bocouture", variant_id="F-bocouture/50-units", presentation_id="F-bocouture/50-units/1xvial", strength="50 units",
                   unit_type="vial", unit_count="2", pack_source="image", lidocaine="no", market="UK/CE", image_matches_text="yes",
                   image_reads="two Bocouture 50 units cartons", evidence=[E("page_title", "Bocouture 50unit Vials x2"), E("page_text", "Box contains one Bocouture vial")],
                   confidence="likely", review_reason="sold as 2 single-vial cartons (page: 'Box contains one Bocouture vial'; image shows 2 cartons), not an official 2-vial pack"),
    "R10091": dict(family_id="F-bocouture", variant_id="F-bocouture/100-units", presentation_id="F-bocouture/100-units/1xvial", strength="100 units",
                   unit_type="vial", unit_count="2", pack_source="page_title", lidocaine="no", market="not_stated",
                   evidence=[E("page_title", "Bocouture 100u Dual Vial")], status_words=["Prescription required"],
                   confidence="likely", review_reason="no description and no image; strength and count only from page title"),
    "R04534": dict(family_id="F-bocouture", variant_id="F-bocouture/100-units", presentation_id="F-bocouture/100-units/1xvial", strength="100 units",
                   unit_type="vial", unit_count="1", pack_source="page_text", lidocaine="no", market="UK/CE", image_matches_text="yes",
                   image_reads="Bocouture 100 units carton and vial", evidence=[E("page_text", "Size and Care Info 1 x 100u"), E("page_text", "manufactured by Merz")],
                   confidence="confirmed"),
    # ---------------- TEOSYAL RHA 3 ----------------
    "R06126": TEO3 | dict(presentation_id="F-teosyal-rha-3/lidocaine-0-3/2x1pre-filled-syringe", unit_count="2", unit_volume_ml="1", pack_source="page_text",
                          lidocaine_source="page_text", image_matches_text="yes", image_reads="Teoxane Teosyal RHA 3 carton, 'hyaluronic acid lidocaine'",
                          evidence=[E("page_text", "The pack consists of: 2 x 1ml syringes"), E("page_text", "The product contains lidocaine")],
                          options_seen=["Non Prescription Item (PAY VAT)", "Prescription Item (VAT FREE)"], confidence="confirmed"),
    "R07761": TEO3 | dict(presentation_id="F-teosyal-rha-3/lidocaine-0-3/2x1pre-filled-syringe", unit_count="2", unit_volume_ml="1", pack_source="page_text",
                          lidocaine_source="page_text", image_matches_text="yes", image_reads="Teosyal RHA 3 carton",
                          evidence=[E("page_text", "The pack consists of: 2 x 1ml syringes"), E("page_text", "Teosyal® RHA 3 Lidocaine")],
                          status_words=["76 in stock"], confidence="confirmed"),
    "R10281": TEO3 | dict(presentation_id="", unit_count="1", unit_volume_ml="1", pack_source="page_title", lidocaine_source="image",
                          image_matches_text="yes", image_reads="full Teosyal RHA 3 carton (official box holds 2 syringes)",
                          evidence=[E("page_title", "Teosyal RHA 3 (1 x 1ml) SINGLE SYRINGE")], options_seen=["Non-Prescription", "Prescription"],
                          confidence="likely", review_reason="split pack: single syringe from a 2-syringe box (official IFU: 'Each box contains two pre-filled syringes')"),
    "R07563": TEO3 | dict(presentation_id="F-teosyal-rha-3/lidocaine-0-3/2x1pre-filled-syringe", unit_count="2", unit_volume_ml="1", pack_source="page_text",
                          lidocaine_source="page_text", image_matches_text="yes", image_reads="Teosyal RHA 3 carton, hyaluronic acid lidocaine",
                          evidence=[E("page_text", "2 x 1ml syringes"), E("page_text", "contains lidocaine")], confidence="confirmed"),
    "R08566": TEO3 | dict(presentation_id="F-teosyal-rha-3/lidocaine-0-3/2x1pre-filled-syringe", unit_count="2", unit_volume_ml="1", pack_source="page_text",
                          lidocaine_source="image", image_matches_text="yes", image_reads="Teosyal RHA 3 carton, hyaluronic acid lidocaine",
                          evidence=[E("page_text", "Teosyal RHA 3 - 2 x 1ml Advanced Resilient Hyaluronic Acid Dermal Filler")],
                          status_words=["backordered"], confidence="confirmed"),
    "R06940": TEO3 | dict(presentation_id="F-teosyal-rha-3/lidocaine-0-3/2x1-2pre-filled-syringe", unit_count="2", unit_volume_ml="1.2", pack_source="page_title",
                          lidocaine_source="page_text", image_matches_text="yes", image_reads="Teosyal RHA 3 carton",
                          evidence=[E("page_title", "Teoxane Teosyal RHA 3 (2 × 1.2ml)"), E("page_text", "The inclusion of lidocaine ensures a gentle injection process")],
                          confidence="confirmed", review_reason="2 x 1.2 ml matches the newer official presentation (Teoxane IFU 230954, Oct 2025)"),
    "R09293": TEO3 | dict(presentation_id="F-teosyal-rha-3/lidocaine-0-3/2x1pre-filled-syringe", unit_count="2", unit_volume_ml="1", pack_source="page_text",
                          lidocaine_source="page_text", image_matches_text="yes", image_reads="Teosyal RHA 3 carton (Wimpole logo)",
                          evidence=[E("page_text", "The pack consists of: 2 x 1ml syringes"), E("page_text", "The product contains lidocaine")], confidence="confirmed"),
    "R05672": TEO3 | dict(presentation_id="F-teosyal-rha-3/lidocaine-0-3/2x1pre-filled-syringe", unit_count="2", unit_volume_ml="1", pack_source="page_title",
                          lidocaine_source="none", lidocaine="not_stated", image_matches_text="yes", image_reads="Teosyal RHA 3 carton (side panel reads RHA 3)",
                          evidence=[E("page_title", "Teosyal Rha 3 (2x1ml)"), E("page_text", "TEOSYAL RHA® 3 is a filler designed to treat severe dynamic wrinkles")],
                          confidence="likely", review_reason="syringe volume only in page title; lidocaine not stated on page (all official RHA 3 contain 0.3% lidocaine)"),
    # ---------------- REVOLAX DEEP (UK vs Korean version) ----------------
    "R08525": REV | dict(variant_id="", lidocaine_source="image", pack_source="page_text", image_matches_text="yes",
                         image_reads="Revolax Deep with Lidocaine carton; lower part (licence holder text) not visible",
                         evidence=[E("page_text", "Revolax Deep Dermal Filler – 1 x 1.1ml"), E("page_text", "monophasic cross-linked HA gel with lidocaine")],
                         status_words=["backordered"], confidence="uncertain", needs_human_review=True,
                         review_reason="UK/CE vs Korean version not stated and not visible on the image (variant identity)"),
    "R09273": REV | dict(variant_id="F-revolax-deep/non-uk-korean-version", market="other_non_UK", lidocaine_source="page_text", pack_source="page_text",
                         image_matches_text="unclear", image_reads="white carton with grey lattice pattern, 'REVOLAX DEEP with Lidocaine', 1.1mL - a different carton design from the FOX GROUP UK box",
                         evidence=[E("page_text", "The pack consists of: 1 x 1.1ml syringe 2 x 27G needles 24 mg/ml cross-linked hyaluronic acid 3mg/ml lidocaine")],
                         conflicts=["carton design differs from the 'FOX GROUP - exclusive UK & IE licence holder' box shown by other suppliers"],
                         confidence="uncertain", needs_human_review=True, review_reason="pack design suggests a non-UK (or older) version; confirm market"),
    "R09556": REV | dict(variant_id="F-revolax-deep/uk-ce-version", market="UK/CE", lidocaine_source="image", pack_source="page_title", image_matches_text="yes",
                         image_reads="Revolax Deep with Lidocaine carton, end panel 'FOXGROUP'",
                         evidence=[E("page_title", "Revolax Deep Dermal Filler - 1x1.1ml"), E("page_text", "REVOLAX Deep with Lidocaine is a thick, long-lasting hyaluronic acid dermal filler")],
                         status_words=["Sold out"], confidence="likely", review_reason="UK version inferred from the FOX GROUP carton in the image"),
    "R09616": REV | dict(variant_id="F-revolax-deep/uk-ce-version", market="UK/CE", lidocaine_source="page_text", pack_source="page_text", image_matches_text="yes",
                         image_reads="Revolax Deep carton 'FOX GROUP exclusive UK & IE licence holder'",
                         evidence=[E("page_text", "HA concentration 24mg/ml Lidocaine HCl 0.3% Volume 1.1ml CE Marked on the box and the inner pack."),
                                   E("page_title", "Revolax Deep UK Official Box")], confidence="likely"),
    "R06135": REV | dict(variant_id="F-revolax-deep/uk-ce-version", market="UK/CE", lidocaine_source="page_text", pack_source="page_text", image_matches_text="yes",
                         image_reads="Revolax Deep carton 'FOX GROUP exclusive UK & IE licence holder'",
                         evidence=[E("page_text", "Hyaluronic acid concentration 24mg/ml Lidocaine HCl 0.3% Volume 1.1ml"), E("page_text", "Box Contents: 1x syringe 2x sterile needles")],
                         options_seen=["Non Prescription Item (PAY VAT)", "Prescription Item (VAT FREE)"], confidence="likely"),
    "R06820": REV | dict(variant_id="F-revolax-deep/uk-ce-version", market="UK/CE", lidocaine_source="page_title", pack_source="page_title", image_matches_text="yes",
                         image_reads="Revolax Deep carton 'FOX GROUP exclusive UK & IE licence holder'",
                         evidence=[E("page_title", "Revolax Deep with Lido 1×1.1ml"), E("page_text", "Manufactured by Across")],
                         confidence="likely", review_reason="volume only in page title; UK version from carton in image"),
    # ---------------- JUVEDERM VOLIFT ----------------
    "R03232": VOL | dict(market="UK/CE", unit_count="2", lidocaine_source="page_text", pack_source="page_text", image_matches_text="yes",
                         image_reads="Juvederm Volift with Lidocaine 2 x 1 mL carton, 'Supplied for UK' sticker",
                         evidence=[E("page_text", "Box Contents: 2 x 1 ml syringes 4 x single use 30G 1/2\" sterile needles"), E("page_text", "17.5 mg/ml hyaluronic acid 3 mg/ml lidocaine hydrochloride")],
                         confidence="likely"),
    "R08259": VOL | dict(unit_count="1", lidocaine_source="page_text", pack_source="page_text", image_matches_text="yes",
                         image_reads="single Volift with Lidocaine syringe blister with 'SINGLE SYRINGE' badge",
                         evidence=[E("page_text", "The pack contains: 1 x 1ml syringe."), E("page_text", "containing hyaluronic acid (HA) and lidocaine")],
                         status_words=["16 in stock"], confidence="likely", review_reason="split pack: single syringe (manufacturer box holds 2)"),
    "R05563": VOL | dict(unit_count="2", lidocaine_source="page_text", pack_source="page_title", image_matches_text="yes",
                         image_reads="Juvederm Volift with Lidocaine 2 x 1 mL carton",
                         evidence=[E("page_title", "Juvederm Volift + Lidocaine (2x1ml)"), E("page_text", "Added lidocaine (a local anaesthetic) provides extra comfort.")],
                         confidence="likely"),
    "R10163": VOL | dict(unit_count="1", lidocaine_source="page_text", pack_source="page_title", image_matches_text="no",
                         image_reads="full Volift 2 x 1 mL carton",
                         evidence=[E("page_title", "Juvederm Volift with lidocaine SINGLE SYRINGE (1x1ml)"), E("page_text", "What is in the box? 2 x 1ml syringes")],
                         conflicts=["page title says SINGLE SYRINGE (1x1ml) but description says 'What is in the box? 2 x 1ml syringes' and image shows the 2-syringe carton"],
                         options_seen=["Prescription", "Non-Prescription"], status_words=["clone"], confidence="uncertain", needs_human_review=True,
                         review_reason="single vs box conflict on the page (listing title also says 'clone')"),
    "N00157": VOL | dict(unit_count="2", lidocaine_source="page_text", pack_source="page_text", image_matches_text="yes",
                         image_reads="Juvederm Volift with Lidocaine 2 x 1 mL carton",
                         evidence=[E("page_text", "Each box contains two 1mL Juvéderm® VOLIFT® with Lidocaine syringes, 4 singleuse 30G1/2” sterile needles")],
                         status_words=["OutOfStock"], confidence="likely"),
    "R04895": VOL | dict(unit_count="2", lidocaine_source="image", pack_source="page_text", image_matches_text="yes",
                         image_reads="Juvederm Volift with Lidocaine 2 x 1 mL carton",
                         evidence=[E("page_text", "Size and Care Info 2 x 1ml"), E("page_text", "Juvéderm VOLIFT with VYCROSS™ Technology")],
                         confidence="likely", review_reason="lidocaine only visible on the carton image"),
    # ---------------- PROFHILO STRUCTURA ----------------
    "R07733": STR | dict(pack_source="page_text", image_matches_text="yes", image_reads="Profhilo Structura carton, 45 mg + 45 mg/2 ml, no hologram sticker visible",
                         evidence=[E("page_text", "1 x 2ml PROFHILO® STRUCTURA is indicated for facial treatment and for restoring adipose tissue.")],
                         confidence="likely", review_reason="UK hologram not visible"),
    "R09582": STR | dict(pack_source="page_title", image_matches_text="yes", image_reads="Profhilo Structura carton with HA hologram sticker",
                         evidence=[E("page_title", "Profhilo Structura – 1x2ml"), E("page_text", "PROFHILO® STRUCTURA is indicated for facial treatment and for restoring adipose tissue.")],
                         status_words=["Sold out"], confidence="likely"),
    "R06835": STR | dict(kind="product", pack_source="page_title", image_matches_text="yes",
                         image_reads="Profhilo Structura carton plus a separate Profhilo Structura cannula box",
                         evidence=[E("page_title", "PROFHILO STRUCTURA WITH CANNULA (1 × 2mL)"), E("page_text", "Profhilo Structura with cannula 2x1ml")],
                         conflicts=["page title says 1 x 2 mL but description says 'with cannula 2x1ml'"],
                         confidence="uncertain", needs_human_review=True,
                         review_reason="volume conflict on the page; also check whether 'with cannula' is the standard UK pack (Moda lists the cannula box as included) or a bundle"),
    "R05164": STR | dict(pack_source="page_text", image_matches_text="yes", image_reads="Profhilo Structura carton with hologram sticker",
                         evidence=[E("page_text", "Size and Care Info 1 x 2ml")], confidence="likely"),
    "R05609": STR | dict(pack_source="page_text", image_matches_text="yes", image_reads="Profhilo Structura carton with HA hologram sticker",
                         evidence=[E("page_text", "Composition 45mg high HA and 45g low HA per 2ml – total 90mg HA"),
                                   E("page_text", "Box contents 1 x 2ml pre-filled syringe Supplied in a separate box 1 x Steriglide 0.50 x 38mm cannula & needle")],
                         confidence="likely"),
}


def main():
    out = ROOT / "llm_results"
    out.mkdir(exist_ok=True)
    for i, d in D.items():
        r = BASE | d
        (out / f"{i}.json").write_text(json.dumps({"id": i, "result": r, "usage": {"decided_by": "claude-session (no API key; same rules and schema as classify_llm.py)"}},
                                                  ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(D), "decisions written")


if __name__ == "__main__":
    main()
