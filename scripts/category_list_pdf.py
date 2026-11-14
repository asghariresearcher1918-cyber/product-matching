"""PDF list of rows in one rough keyword category (first-match order, same rules as the
category estimate shown in chat). Usage: python -I scripts/category_list_pdf.py"""
import csv
import sys
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
CAT = [
    ("toxin", r"botox|bocouture|azzalure|dysport|alluzience|letybo|relfydess|xeomin"),
    ("filler/booster/biostim (device)", r"juvederm|teosyal|redensity|rha\b|restylane|belotero|stylage|revolax|radiesse|sculptra|ellanse|profhilo|jalupro|plinest|sunekos|nucleofill|lumi|fillmed|regenovue|aliaxin|viscoderm|saypha|harmonyca|revanesse|neauvia|croma|perfectha|hyacorp|rejuran|seventy|purasomes|aqualyx|lemon ?bottle|polyphil|skinfill|nexfill|lumifil|pluryal|dermaheal|juvelook|aesplla|ejal|sonic|neuramis|e\.?p\.?t\.?q|kairax|karisma|filler|skin ?booster|polynucleotide|exosome|mesotherapy|ml\b.*syringe"),
    ("needle/cannula/syringe", r"needle|cannula|syringe|\b\d{2}g\b"),
    ("medicine (POM/P)", r"tablet|capsule|injection|ampoule|amp\b|vial|cream \d|ointment|mg\b|mcg|solution for|wegovy|mounjaro|ozempic|saxenda|emla|lidocaine|hyaluronidase|adrenaline|epipen|kenalog|pabrinex|antibiotic|eye drops|inhaler|\bpom\b"),
    ("consumable/PPE/clinic", r"glove|gauze|swab|wipe|clinell|clinisept|sharps|apron|gown|mask|couch|tourniquet|plaster|dressing|tape|micropore|cotton|steril|disinfect|bin\b|tray"),
    ("skincare/cosmetic/supplement", r"serum|cream|cleanser|spf|sunscreen|peel|mask|moistur|toner|gel\b|lotion|neostrata|heliocare|mesoestetic|supplement|collagen|vitamin|biorepeel|prx"),
]
TARGET = "skincare/cosmetic/supplement"
OTHER = "other/unknown"  # rows that matched no keyword rule
TITLES = {"skincare/cosmetic/supplement": "Skincare / cosmetics / supplements", OTHER: "Other / unknown (no keyword matched)"}
FILES = {"skincare/cosmetic/supplement": "category_skincare_cosmetics_supplements", OTHER: "category_other_unknown"}


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET
    rows = list(csv.DictReader(open(ROOT / "products_input.csv", encoding="utf-8-sig")))
    sel = []
    for x in rows:
        t = x["title"].lower()
        for k, p in CAT:
            m = re.search(p, t)
            if m:
                if k == target:
                    sel.append((x, m.group(0)))
                break
        else:
            if target == OTHER:
                sel.append((x, "none"))
    sel.sort(key=lambda s: (s[0]["title"].lower(), s[0]["supplier"]))
    out_csv = ROOT / "output" / f"{FILES[target]}.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["no", "id", "supplier", "title", "matched_keyword", "url"])
        for i, (x, kw) in enumerate(sel, 1):
            w.writerow([i, x["id"], x["supplier"], x["title"], kw, x["url"]])

    pdfmetrics.registerFont(TTFont("DV", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DVB", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    cell = ParagraphStyle("c", fontName="DV", fontSize=7.5, leading=9)
    link = ParagraphStyle("l", fontName="DV", fontSize=6.3, leading=7.6, textColor=colors.HexColor("#1a56a8"), splitLongWords=1)
    head = ParagraphStyle("h", fontName="DVB", fontSize=8, leading=10, textColor=colors.white)
    h1 = ParagraphStyle("t", fontName="DVB", fontSize=15, leading=19)
    note = ParagraphStyle("n", fontName="DV", fontSize=8.5, leading=11, textColor=colors.HexColor("#444444"))
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    data = [[Paragraph(h, head) for h in ("#", "ID", "Supplier", "Title (click to open)", "Product link", "Match")]]
    for i, (x, kw) in enumerate(sel, 1):
        u = esc(x["url"])
        data.append([Paragraph(str(i), cell), Paragraph(x["id"], cell), Paragraph(esc(x["supplier"]), cell),
                     Paragraph(f'<a href="{u}" color="#1a56a8">{esc(x["title"])}</a>', cell),
                     Paragraph(f'<a href="{u}">{u}</a>', link), Paragraph(esc(kw), cell)])
    pw = landscape(A4)[0] - 24 * mm
    fixed = [10 * mm, 15 * mm, 33 * mm, 0, 92 * mm, 17 * mm]
    fixed[3] = pw - sum(fixed)
    t = Table(data, colWidths=fixed, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f4f6f")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f8")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c8d0d8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    sup = {}
    for x, _ in sel:
        sup[x["supplier"]] = sup.get(x["supplier"], 0) + 1
    story = [
        Paragraph(f"{TITLES[target]} - {len(sel)} rows", h1), Spacer(1, 4),
        Paragraph(("Rough keyword categorisation of products_input.csv (first matching rule wins; rows matching an earlier "
                  "category such as filler, needle or medicine are not in this list). " if target != OTHER else
                  "These rows matched none of the six keyword lists used for the quick category estimate (title words only). "
                  "They were never classified from their product pages: the page-based method has so far been run only on toxins and "
                  "fillers/skin boosters/biostimulators. ") + "Not yet checked against product pages. Sorted by title so near-duplicates sit together.", note),
        Spacer(1, 3),
        Paragraph("Rows per supplier: " + esc(", ".join(f"{k} {v}" for k, v in sorted(sup.items(), key=lambda kv: -kv[1]))), note),
        Spacer(1, 6), t,
    ]

    def footer(c, d):
        c.setFont("DV", 7)
        c.setFillColor(colors.grey)
        c.drawRightString(landscape(A4)[0] - 12 * mm, 8 * mm, f"page {d.page}")

    out = ROOT / "output" / f"{FILES[target]}.pdf"
    SimpleDocTemplate(str(out), pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                      bottomMargin=14 * mm, title=TITLES[target]).build(story, onFirstPage=footer, onLaterPages=footer)
    print(out, len(sel))


if __name__ == "__main__":
    main()
