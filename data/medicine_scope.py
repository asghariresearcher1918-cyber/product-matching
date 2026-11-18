"""Scope of the three medicine categories for phase 1 (aesthetic & skin clinics). Agreed with the owner 2026-11-18.
Each rule: (group, action, regex on the lower-cased page name + listing title). First match wins; unmatched = general pharmacy.
action: "keep"            -> phase 1
        "phase2"          -> men's / women's health, MSK etc. - later phase
        "remove"          -> not used by aesthetic / skin clinics (not deleted: scope = "Removed - general pharmacy")
        "move:<category>" -> right product, wrong category
"""

DEFAULT = ("General pharmacy (not clinic use)", "remove")  # vaccines too: travel, flu, childhood

ORAL = [
    ("Weight loss", "move:Weight-loss medicine", r"foundayo|wegovy|rybelsus|xenical|\balli\b|orlistat"),
    ("Complications: antibiotics", "keep", r"amoxicillin|amoxiclav|augmentin|fluclox|clarithro|azithro|doxycycl|vibramycin|lymecycl|tetralysal|minocyc|minocin|erythro|cefalexin|keflex|zinnat|clindamycin|metronidazole|ciproflox|oxytetracycl|moxiflox|ampicillin|penicillin"),
    ("Complications: antivirals", "keep", r"aciclovir|valaciclovir|valtrex|zovirax|famciclovir"),
    ("Complications: antihistamines", "keep", r"cetirizine|loratadine|loratidine|clarityn|fexofenadine|chlorphenamine|piriton|hydroxyzine|ucerax|benadryl allergy relief|phenergan"),
    ("Complications: steroids", "keep", r"prednis|dexamethasone"),
    ("Emergency: aspirin, glucose, GTN, acetazolamide", "keep", r"aspirin|glucogel|gluco boost|glucose|dextrogel|rapilose|glyceryl|acetazol"),
    ("Nausea (antiemetics)", "keep", r"ondansetron|cyclizine|metoclopramide|metolopramide|maxolon|prochlorperazine|stemetil|buccastem|domperidone"),
    ("Pain after treatment", "keep", r"^(paracetamol|ibuprofen|brufen)"),
    ("Skin & hair treatments (acne, hair loss, melasma, fungal)", "keep", r"isotretinoin|roaccutane|spironolactone|finasteride|propecia|proscar|minoxidil|dianette|yasmin|tranexamic|terbinafine|itraconazole|fluconazole|ivermectin|hydroxychloroquine|methotrexate|ciclosporin|neoral|nizoral"),
    ("Men's & women's health", "phase2", r"sildenafil|tadalafil|viagra|revatio|premarin|elleste|utrogestan|sandrena|testogel|progynova|femoston|climagest|tibolone|zumenon|vagifem|provera|norethisterone|microgynon|rigevidon|cilique|brevinor|gedarel|clomid|clomifene"),
]

TOPICAL = [
    ("Topical anaesthetics", "keep", r"emla|\blmx|ametop|xylocaine pump|xylonor"),
    ("Complications: eye drops (timolol, apraclonidine, brimonidine, brinzolamide)", "keep", r"timolol(?!.*travo)|iopidine|apraclonidine|brimonidine|alphagan|azopt|brinzolamide"),
    ("Lash growth (bimatoprost, off-label)", "keep", r"bimatoprost|lumigan"),
    ("Acne, rosacea, pigmentation, actinic (prescription)", "keep", r"acnecide|aknemycin|adapalene|differin|epiduo|duac|treclin|tretinoin|retirides|zindaclin|zineryt|erythromycin/zinc|dalacin|finacea|skinoren|azelaic|rozex|metronidazole gel|soolantra|mirvaso|hydroquinone|efudix|solaraze|aldara|actikerall|warticon"),
    ("Topical steroids & anti-infectives (post-procedure, dermatitis)", "keep", r"hydrocortisone|betnovate|betamethasone|dermovate|eumovate|elocon|synalar|diprosalic|fucibet|fucidin|daktacort|canesten hc|mildison|lotriderm|clobaderm|nystaform|nystatin chlorhex|bactroban|elidel|protopic|dovobet|dovonex|enstilar|silkis"),
    ("Scars, bruising, sweating, hair, aftercare", "keep", r"dermatix|kelo-?cote|hirudoid|driclor|regaine|aloe vera|aciclovir cream|compeed cold sore|silver nitrate"),
    ("Emergency: GTN, salbutamol, glucose, ipratropium", "keep", r"glyceryl|\bgtn\b|deponit|percutol|salbutamol|ventolin|glucose|ipratropium"),
    ("Men's & women's health", "phase2", r"oestrogel|sandrena|evorel|estradot|estraderm|testim|tostran|androfeme|vagifem|estriol|crinone|cyclogest|lenzetto|progynova"),
]

INJECTABLE = [
    # wrong category
    ("Dermal filler", "move:Dermal filler", r"neauvia|\buth (deep|fine|sub)|rha kiss"),
    ("Mesotherapy / skin booster vials", "move:Skin booster / polynucleotide / mesotherapy", r"dermaqual|md-?(matrix|muscle)|ami peptox|strikecell|pink glow|\brrs\b|ultracol|evolutha|ares hb|allskin|inno-?exfo|amino formula|me line|revitacare"),
    ("Skincare / aftercare", "move:Skincare, haircare & peels", r"aftermed|puri lips|arnicare|alyval|srs glycolic|topilase|4t medical wound|orajel|ralvo"),
    ("Consumables / needles", "move:Clinic consumables & PPE", r"skin marking pencil|ampoule opener|vial opener|vial pliers"),
    ("Needles / cannulas", "move:Needles, cannulas & syringes", r"surflo"),
    ("Training", "move:Training, services & marketing", r"injection training"),
    ("Vitamins & IV", "move:Vitamin & IV therapy", r"hydroxocobalamin|vitamin d|colecalciferol|ergocalciferol|pyridoxine|bepanthene|ascorell|myers|nad\+?|magnesium sulph|magnesium sulfate|vitamin b1|thiamine"),
    # phase 1
    ("Emergency: adrenaline & kits", "keep", r"adrenaline(?!.*(lidocaine|xylocaine|bupivacaine))|epinephrin|epipen|jext|emerade|emergency|\bekit|aer kit"),
    ("Hyaluronidase", "keep", r"hyalase|hyaluronidase|disolvidase"),
    ("Local anaesthetics (incl. dental cartridges)", "keep", r"lidocaine|lignocaine|xylocaine|bupivacaine|marcain|chirocaine|ropivacaine|citanest|prilocaine|lignospan|scandonest|septanest|articaine|anestadent|emla|lmx"),
    ("Diluents, saline, water for injection", "keep", r"sodium chloride|saline|bac[- ]?stat|bacteriostatic|tor-?bac|water for injection|sterile water|irripod|irriclens|posiflush|glucose"),
    ("Steroid injections (keloid, scars)", "keep", r"kenalog|triamcinolone|adcortyl|depo[- ]?medrone|betamethasone"),
    ("Sclerotherapy & 5-FU", "keep", r"fibrovein|aethoxysklerol|fluorouracil"),
    ("Emergency: other (CQC / ACE lists)", "keep", r"chlorphenamine|hydrocortisone|ondansetron|zofran|cyclizine|glucagen|glyceryl|salbutamol|dexamethasone|prednisolone|loratadine|atropine|sodium bicarbonate|tranexamic"),
    ("PRP anticoagulant", "keep", r"acd-?a"),
    # later
    ("Men's & women's health", "phase2", r"testosteron|nebido|sustanon|caverject|papaverine"),
    ("Joint / MSK injections", "phase2", r"ostenil|durolane|synvisc|monovisc|cingal|sinovial|sinogel|kiomedine|biolevox|haxl|arthrosamid|orthovisc"),
    ("Iron infusions", "phase2", r"ferinject|venofer|cosmofer"),
]

RULES = {
    "Medicine - oral": ORAL,
    "Medicine - topical / eye / other": TOPICAL,
    "Medicine - injectable / anaesthetic / emergency": INJECTABLE,
}

VACCINE = [  # agreed 2026-11-18: only adult hepatitis B (staff immunisation, JCCP standard 7)
    ("Hepatitis B - staff immunisation (adult)", "keep", r"engerix ?b(?!.*paed)"),
]
RULES["Vaccine"] = VACCINE
