"""Persian version of the clinic needs file -> output/clinic_needs_fa.xlsx (reads output/clinic_needs_master.xlsx; run needs_master_xlsx.py first).
Usage: python -I scripts/needs_master_fa.py"""
import collections, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from clinic_needs_master import ITEMS, SOURCES
import clinic_needs_fa as FA
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

assert len(FA.ITEMS) == len(ITEMS), (len(FA.ITEMS), len(ITEMS))
src = openpyxl.load_workbook(ROOT / "output/clinic_needs_master.xlsx")
ml = [r for r in src["Master list"].iter_rows(min_row=2, values_only=True)]
assert [r[1] for r in ml] == [i[1] for i in ITEMS]
F = "Tahoma"; HF, HFILL = Font(name=F, bold=True, color="FFFFFF", size=10), PatternFill("solid", fgColor="2F4F6F")
FILL = {"Good": "C6EFCE", "Weak": "FFF2CC", "Missing": "F8CBAD", "Service / fit-out": "DDEBF7",
        "Complete": "C6EFCE", "Partial": "FFF2CC", "Incomplete": "F8CBAD"}

def sheet(wb, title, cols, widths, first=False):
    ws = wb.active if first else wb.create_sheet(title)
    ws.title = title; ws.sheet_view.rightToLeft = True; ws.append(cols)
    for j, w in enumerate(widths, 1):
        c = ws.cell(row=1, column=j); c.font, c.fill = HF, HFILL; c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="right")
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A2"; return ws
def fmt(ws):
    for c in ws[ws.max_row]: c.font = Font(name=F, size=10); c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="right")

wb = Workbook()
# 1. guide
g = sheet(wb, "راهنما", ["این فایل چیست؟"], [130], first=True)
for t in ["این فایل یک چک‌لیست است: «یک کلینیک زیبایی و پوست در بریتانیا چه چیزهایی لازم دارد؟» و برای هر قلم: «آیا در سایت ما هست؟»",
          f"{len(ITEMS)} قلم در {len(FA.SECTIONS)} دسته. منبع: راهنماهای رسمی (CQC، JCCP، شورای احیای بریتانیا، ACE و غیره) و کاتالوگ عمده‌فروش‌ها - نه لیست ۲۴ داروخانه‌ی ما.",
          "پوشش فقط با آگهی‌های فاز ۱ ما حساب شده است. 🟢 خوب داریم = حداقل ۳ فروشنده و ۵ آگهی | 🟡 کم داریم | 🔴 نداریم | ⚪ خدمات (فاز ۲).",
          "وضعیت دسته: 🟢 کامل = حداقل ۸۰٪ اقلام را خوب داریم و هیچ قلم الزامی کم نیست | 🔴 ناقص = کمتر از ۵۰٪ | 🟡 نیمه‌کامل = بین این دو.",
          "سطح الزام: الزامی = راهنمای رسمی می‌گوید باید باشد | توصیه‌شده | اگر آن درمان را انجام دهد | رایج (همه دارند ولی الزامی نیست) | اختیاری.",
          "برگه‌ها: ۱) وضعیت دسته‌ها ← مهم‌ترین برگه  ۲) کمبودها ← فقط اقلامی که نداریم یا کم داریم  ۳) لیست کامل ← همه‌ی اقلام  ۴) منابع.",
          "عددها با جستجوی کلمه در اسم محصولات به دست آمده و تقریبی است."]:
    g.append([t]); fmt(g)
# 2. sections
cs = {r[0]: r for r in src["Complete or not"].iter_rows(min_row=2, values_only=True)}
s = sheet(wb, "وضعیت دسته‌ها", ["دسته", "وضعیت", "تعداد اقلام کالایی", "🟢 خوب داریم", "🟡 کم داریم", "🔴 نداریم", "درصد پوشش خوب",
                                 "اقلام الزامی که کم داریم", "از کجا می‌شود تأمین کرد", "خدمات (فاز ۲)"], [30, 14, 10, 9, 9, 9, 10, 60, 40, 9])
fa_item = {ITEMS[i][1]: FA.ITEMS[i] for i in range(len(ITEMS))}
for sec, r in cs.items():
    req = "؛ ".join(fa_item.get(x.strip(), x) for x in (r[6] or "").split(";") if x.strip())
    st = r[7]
    s.append([FA.SECTIONS[sec], FA.STATUS.get(st, st), r[1], r[2], r[3], r[4], r[5], req, r[8] or "", r[9]]); fmt(s)
    s.cell(row=s.max_row, column=7).number_format = "0%"
    if st in FILL: s.cell(row=s.max_row, column=2).fill = PatternFill("solid", fgColor=FILL[st])
# 3. gaps + 4. full list
gp = sheet(wb, "کمبودها", ["دسته", "قلم", "سطح الزام", "وضعیت ما", "تعداد فروشنده‌ی ما", "از کجا می‌شود تأمین کرد", "شیوه‌ی فروش"], [28, 60, 18, 14, 10, 40, 14])
fl = sheet(wb, "لیست کامل", ["دسته", "قلم", "توضیح (انگلیسی)", "سطح الزام", "منبع رسمی", "نوع", "دفعات خرید", "چه کسی قیمت را ببیند", "شیوه‌ی فروش",
                              "آگهی‌های ما", "فروشنده‌های ما", "وضعیت ما", "از کجا می‌شود تأمین کرد", "نمونه از لیست ما", "بماند؟", "یادداشت"],
           [26, 52, 30, 16, 16, 12, 12, 18, 13, 9, 9, 14, 30, 50, 8, 24])
order = {"Required": 0, "Recommended": 1, "If offered": 2, "Standard practice": 3, "Optional": 4}
gaps = []
for i, r in enumerate(ml):
    sec, item, spec, clinic, level, srcs, kind, freq, access, mode, n, nsup, cov, wh, ex = r[:15]
    fl.append([FA.SECTIONS[sec], FA.ITEMS[i], spec, FA.LEVEL[level], srcs, FA.KIND[kind], FA.FREQ[freq], FA.ACCESS[access], FA.MODE[mode],
               n, nsup, FA.COV[cov], wh, ex, "", ""]); fmt(fl)
    fl.cell(row=fl.max_row, column=12).fill = PatternFill("solid", fgColor=FILL[cov])
    if cov in ("Weak", "Missing"): gaps.append((order[level], cov != "Missing", sec, FA.ITEMS[i], level, cov, nsup, wh, mode))
for _, _, sec, it, level, cov, nsup, wh, mode in sorted(gaps):
    gp.append([FA.SECTIONS[sec], it, FA.LEVEL[level], FA.COV[cov], nsup, wh or "", FA.MODE[mode]]); fmt(gp)
    gp.cell(row=gp.max_row, column=4).fill = PatternFill("solid", fgColor=FILL[cov])
fl.auto_filter.ref = f"A1:P{fl.max_row}"; gp.auto_filter.ref = f"A1:G{gp.max_row}"
# 5. sources
so = sheet(wb, "منابع", ["کد", "منبع", "لینک"], [10, 100, 60])
for k, (name, url) in SOURCES.items():
    so.append([k, name, url]); fmt(so)
    if url.startswith("http") and " " not in url:
        c = so.cell(row=so.max_row, column=3); c.hyperlink = url; c.font = Font(name=F, size=10, color="0563C1", underline="single")
wb._sheets = [wb[n] for n in ["راهنما", "وضعیت دسته‌ها", "کمبودها", "لیست کامل", "منابع"]]
p = ROOT / "output/clinic_needs_fa.xlsx"; wb.save(p); print(p, len(gaps), "gaps")
