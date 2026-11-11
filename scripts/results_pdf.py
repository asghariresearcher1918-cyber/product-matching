"""PDF of grouped results: family -> variant -> pack -> supplier rows (clickable), plus review queue and catalogue status.
Usage: python -I scripts/results_pdf.py [OUT.pdf]"""
import collections
import csv
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "output" / "scope" / "results_sample.pdf"
pdfmetrics.registerFont(TTFont("DV", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
H1 = ParagraphStyle("h1", fontName="DVB", fontSize=15, leading=19)
H2 = ParagraphStyle("h2", fontName="DVB", fontSize=11.5, leading=15, spaceBefore=8, textColor=colors.HexColor("#1f3b57"))
H3 = ParagraphStyle("h3", fontName="DVB", fontSize=9, leading=12, spaceBefore=4)
N = ParagraphStyle("n", fontName="DV", fontSize=8.5, leading=11, textColor=colors.HexColor("#333333"))
C = ParagraphStyle("c", fontName="DV", fontSize=7.3, leading=9)
CH = ParagraphStyle("ch", fontName="DVB", fontSize=7.5, leading=9, textColor=colors.white)
CONF = {"confirmed": "#1b7f3b", "likely": "#9a6a00", "uncertain": "#b3261e"}
esc = lambda s: (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def table(data, widths):
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f4f6f")),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f9")]),
                           ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c8d0d8")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return t


def main():
    rows = list(csv.DictReader(open(ROOT / "output" / "scope" / "products_grouped.csv", encoding="utf-8")))
    others = list(csv.DictReader(open(ROOT / "output" / "scope" / "non_products.csv", encoding="utf-8")))
    fams = {f["family_id"]: f for f in csv.DictReader(open(ROOT / "catalogue" / "families.csv", encoding="utf-8"))}
    rows = [r for r in rows if r["family_id"]]
    pw = landscape(A4)[0] - 24 * mm
    conf = collections.Counter(r["confidence"] for r in rows + others)
    story = [Paragraph("Toxins &amp; fillers - method results (sample)", H1), Spacer(1, 4),
             Paragraph(f"{len(rows) + len(others)} rows from {len({r['supplier'] for r in rows + others})} suppliers. "
                       f"Grouped into {len({r['family_id'] for r in rows})} families, {len({r['variant_id'] for r in rows})} variants, "
                       f"{len({r['pack_id'] for r in rows})} packs. Confidence: " + ", ".join(f"{k} {v}" for k, v in conf.most_common()) +
                       f". Not products: {len(others)}. Step-3 decisions for this sample were made in the session with the same rules and output "
                       "schema as the API classifier (no API key yet); steps 2 and 4 ran as code. Click a title to open the supplier page.", N)]
    for fid in sorted({r["family_id"] for r in rows}, key=lambda f: -len([r for r in rows if r["family_id"] == f])):
        fr = [r for r in rows if r["family_id"] == fid]
        f = fams.get(fid, {})
        story.append(Paragraph(f"{esc(f.get('brand', ''))} {esc(f.get('line', ''))} &nbsp;<font size=8 color='#555555'>({fid} - reference: "
                               f"{f.get('reference_status', '?')}, {len(fr)} rows, {len({r['supplier'] for r in fr})} suppliers)</font>", H2))
        for vid in sorted({r["variant_id"] for r in fr}):
            vr = [r for r in fr if r["variant_id"] == vid]
            data = [[Paragraph(h, CH) for h in ("Pack", "Supplier", "Title (click)", "Evidence", "Conf.", "Review reason")]]
            for r in sorted(vr, key=lambda r: (r["pack_label"], r["supplier"])):
                col = CONF.get(r["confidence"], "#333333")
                data.append([Paragraph(esc(r["pack_label"]), C), Paragraph(esc(r["supplier"]), C),
                             Paragraph(f'<a href="{esc(r["url"])}" color="#1a56a8">{esc(r["title"])}</a>', C),
                             Paragraph(esc(r["evidence"][:230]), C), Paragraph(f'<font color="{col}">{r["confidence"]}</font>', C),
                             Paragraph(esc(r["review_reason"][:260]), C)])
            story.append(KeepTogether([Paragraph("Variant: " + esc(vr[0]["variant_label"]), H3),
                                       table(data, [28 * mm, 28 * mm, 50 * mm, pw - 28 * mm * 2 - 50 * mm - 19 * mm - 60 * mm, 19 * mm, 60 * mm])]))
    if others:
        story.append(Paragraph("Not products (kept out of the comparison)", H2))
        data = [[Paragraph(h, CH) for h in ("Kind", "Supplier", "Title (click)", "Why")]]
        for r in others:
            data.append([Paragraph(esc(r["kind"]), C), Paragraph(esc(r["supplier"]), C),
                         Paragraph(f'<a href="{esc(r["url"])}" color="#1a56a8">{esc(r["title"])}</a>', C), Paragraph(esc(r["evidence"][:200]), C)])
        story.append(table(data, [40 * mm, 35 * mm, 80 * mm, pw - 155 * mm]))

    def footer(c, d):
        c.setFont("DV", 7)
        c.setFillColor(colors.grey)
        c.drawRightString(landscape(A4)[0] - 12 * mm, 8 * mm, f"page {d.page}")

    SimpleDocTemplate(str(OUT), pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=14 * mm,
                      title="Toxins & fillers - results").build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


if __name__ == "__main__":
    main()
