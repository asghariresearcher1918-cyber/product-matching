"""Turn a category workbook into always-openable views: per-tab CSVs + one self-contained,
mobile-friendly, RTL, dark-mode HTML page with clickable links.

Usage: python -I scripts/export_views.py output/v2_surgical_medical_supplies.xlsx "C13 — Surgical & Medical Supplies"
Writes <stem>_view.html next to the xlsx and <stem>_csv/<NN>_<tab>.csv per tab."""
import csv, html, re, sys
from pathlib import Path
from openpyxl import load_workbook

LINK_COLS = {"Product link (click)", "Name reference (name source)", "Name reference", "Source", "Product link"}


def _csvsafe(v):
    return "" if v is None else v


def main():
    xlsx = Path(sys.argv[1])
    title = sys.argv[2] if len(sys.argv) > 2 else xlsx.stem
    wb = load_workbook(xlsx)
    stem = xlsx.with_suffix("")
    csvdir = Path(str(stem) + "_csv"); csvdir.mkdir(parents=True, exist_ok=True)

    sections, buttons, counts = [], [], []
    for si, sn in enumerate(wb.sheetnames):
        ws = wb[sn]
        rows = list(ws.iter_rows(values_only=True))
        hdr = rows[0]
        linkidx = {i for i, h in enumerate(hdr) if str(h or "") in LINK_COLS}
        # CSV (utf-8-sig so Excel/phones show Persian + £ correctly)
        safe = re.sub(r"[^A-Za-z0-9]+", "_", sn).strip("_").lower()
        with open(csvdir / f"{si+1:02d}_{safe}.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            for r in rows:
                w.writerow([_csvsafe(c) for c in r])
        # HTML table
        out = ["<table><thead><tr>"]
        for h in hdr:
            out.append(f"<th>{html.escape(str(h or ''))}</th>")
        out.append("</tr></thead><tbody>")
        for r in rows[1:]:
            out.append("<tr>")
            for i, c in enumerate(r):
                v = "" if c is None else str(c)
                if i in linkidx and v.startswith("http"):
                    out.append(f'<td><a href="{html.escape(v)}" target="_blank" rel="noopener">باز کردن ↗</a></td>')
                else:
                    out.append(f"<td>{html.escape(v)}</td>")
            out.append("</tr>")
        out.append("</tbody></table>")
        on = " on" if si == 0 else ""
        sections.append(f'<section class="{on.strip()}"><div class="wrap">{"".join(out)}</div></section>')
        buttons.append(f'<button class="{on.strip()}" onclick="show({si},this)">{html.escape(sn)} ({len(rows)-1})</button>')
        counts.append(f"{len(rows)-1} {sn}")

    doc = f"""<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{--bg:#fff;--fg:#1a1a1a;--line:#d8dee6;--head:#2F4F6F;--alt:#f4f7fa;--accent:#0563C1;--mut:#7b8794}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#13171c;--fg:#e8edf2;--line:#2c343d;--head:#16324b;--alt:#1a1f25;--accent:#5aa7ff;--mut:#8a97a4}}}}
:root[data-theme="dark"]{{--bg:#13171c;--fg:#e8edf2;--line:#2c343d;--head:#16324b;--alt:#1a1f25;--accent:#5aa7ff;--mut:#8a97a4}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif;padding:16px}}
h1{{font-size:20px;margin:0 0 4px}}
.sub{{color:var(--mut);font-size:13px}}
.tabs{{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}}
.tabs button{{border:1px solid var(--line);background:var(--alt);color:var(--fg);padding:7px 12px;border-radius:8px;font-size:13px;cursor:pointer}}
.tabs button.on{{background:var(--head);color:#fff;border-color:var(--head)}}
.wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:8px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;min-width:640px}}
th,td{{border-bottom:1px solid var(--line);padding:7px 9px;text-align:right;vertical-align:top}}
thead th{{background:var(--head);color:#fff;position:sticky;top:0}}
tbody tr:nth-child(even){{background:var(--alt)}}
a{{color:var(--accent)}}
section{{display:none}} section.on{{display:block}}
</style></head><body>
<h1>{html.escape(title)}</h1>
<div class="sub">{' · '.join(html.escape(c) for c in counts)}</div>
<div class="tabs">{''.join(buttons)}</div>
{''.join(sections)}
<script>
function show(i,btn){{document.querySelectorAll('section').forEach((s,j)=>s.classList.toggle('on',i===j));
document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('on'));btn.classList.add('on');}}
</script></body></html>"""
    htmlpath = Path(str(stem) + "_view.html")
    htmlpath.write_text(doc, encoding="utf-8")
    print(f"wrote {htmlpath} and {csvdir}/ ({len(wb.sheetnames)} tabs)")


if __name__ == "__main__":
    main()
