# قوانین کاتالوگ — مشخصات کامل (تمام جزئیات)

**ترتیب اجرای pipeline:** `cleanup_categories → categorize_all → apply_scope → کاتالوگ هر دسته → build_*_reference → reference_match → master_catalogue → canonical_names → master_catalogue (بار دوم) → auto_consolidate → full_export/category_export → build_site`
(master دو بار اجرا می‌شود: اول برای ساخت ایندکس لیستینگ که canonical_names لازم دارد، بعد برای اعمال نام‌ها.)

---

## A. دسته‌بندی — هر لیستینگ در کدام دسته می‌رود

### A1. سیگنال‌ها (`categorize_all.py`)
هر لیستینگ از صفحهٔ اسکرَیپ‌شده خوانده و رأی‌ها جمع می‌شوند:
- **S1 دستهٔ فروشنده** (breadcrumb / WooCommerce / Shopify / مسیر URL / فیلد Category) — قوی‌ترین
- **S1b نام برند/وندور** از فیلد وندور یا عنوان صفحه
- **S2 عنوان صفحه** — با قوانین کلیدواژه (از خاص به عام)
- **S3 دیکشنری برند** (`data/brands_scope.csv`) ← برند شناخته‌شده ← دسته
- **S4 فیلدهای قانونی/دارویی** صفحه (POM / P / GSL / MD، نوع دارو…)
- **S5 توضیحات** (ضعیف‌تر) · **S6 عنوان لیستینگ** (ضعیف‌ترین، آخرین راه)
- **اطمینان:** high = ≥۲ سیگنال قوی هم‌رأی بدون تضاد؛ medium = یک سیگنال قوی؛ low = ضعیف/متناقض (به لیست بازبینی دستی).

### A2. بیست دسته
توکسین · فیلر · اسکین‌بوستر/PN/مزوتراپی · بایواستیمولاتور · چربی‌سوز · ویتامین و IV · کاهش‌وزن · داروی تزریقی/بیهوشی/اورژانس · داروی خوراکی · داروی موضعی/چشم/سایر · واکسن · سوزن/کانولا/سرنگ · مصرفی و PPE · دستگاه و تجهیزات · اسکین‌کر/مو/پیل · مکمل · Beauty (ناخن/ابرو/مژه/PMU/آرایش) · آموزش/خدمات · محصول نیست.

### A3. override دستی دسته
`data/category_overrides.csv` (`id,category,note`) — اول از همه اعمال می‌شود و بر همهٔ سیگنال‌ها غلبه دارد.
`cleanup_categories.py` این‌ها را برنامه‌ای (idempotent) برای خطاهای شناخته‌شده می‌سازد: کرم‌های Profhilo (Haenkenium/Figura/Pura) ← اسکین‌کر؛ داروهای موضعی POM لایسنس‌دار (Emla, Fucidin, Betnovate, Hydrocortisone, Differin, Rozex, Skinoren, aciclovir — ولی **نه** برند کازمسوتیکال Noon azelaic) ← دارو؛ EpiPen/Lignospan ← دارو.

### A4. Scope (`apply_scope.py` + `medicine_scope.py` + `scope_overrides.csv`)
قوانین regex به ازای هر دسته، ردیف را به یک action ← برچسب نگاشت می‌کنند:
`keep→Phase 1` · `phase2→Phase 2 - later` · `remove→Removed - general pharmacy` · `salon→Later phase - nail & facial salons` · `move:<cat>` دسته را عوض می‌کند.
override به ازای id در `scope_overrides.csv` آخر از همه اعمال می‌شود (برای خارج‌کردن ضدبارداری، کیت تست خانگی، تنفسی، X-ray، تصفیه هوا، تزریقی‌های فارماسی عمومی Praluent/Xolair/Genotropin).
تأمین‌کننده‌های Refine Pharma و DermaFocus ← «On hold». **فقط ردیف‌های `Phase 1` در سایت می‌آیند.**

---

## B. محصول — گروه‌بندی لیستینگ‌ها در یک محصول

### B1. روش الف — مرجع‌محور (مطمئن). `reference_match.py` + `data/reference/*.csv`
برای دسته‌های: **فیلر، بوستر، اسکین‌کر، توکسین، چربی‌سوز** (هرکدام فایل مرجع خودش). برای هر لیستینگ:

۱. **تشخیص برند** (به این ترتیب):
   الف. `\b<برند>\b` در عنوان؛
   ب. اگر نبود، تطبیق **squashed**: برند با حذف فاصله/نقطه، زیررشتهٔ عنوانِ squashed باشد (پس `LipoLab` = `Lipo Lab`)؛
   ج. اگر نبود، برندِ parse‌شدهٔ لیستینگ در صورتی که برند مرجع باشد.
   هیچ برند مرجعی نبود ← **passthrough** (کد روش ب دست‌نخورده می‌ماند).
۲. **حذف‌ها** (قبل از تطبیق):
   - **accessory** ← `review-accessory`، محصول نیست: `roller banner | banner | poster | sticker | lanyard | t-shirt | brochure | leaflet | display stand | shelf`
   - **bundle** ← `review-bundle`: `free | get 1 | get one | + 1 x | buy 1 get | bundle | worth £ | multibuy`
۳. **انتخاب محصول:** از ردیف‌های مرجع آن برند، همانی که **طولانی‌ترین alias**‌اش زیررشتهٔ عنوان است؛ اگر هیچ alias نبود، ردیف `default`؛ اگر هیچ‌کدام ← `review-nomatch`.
۴. **لیدوکائین:** مرجع `yes`→بله، `no`→خیر، `detect`→ اگر عنوان `lidocaine | +lido | lido | with lido` داشت.
۵. **تعداد پک** — قانون خواندن تو، به ترتیب، اولین که پیدا شد:
   **عنوان ← کل صفحهٔ محصول (`page_text`) ← OCR عکس (`image_text`) ← در غیر این صورت پیش‌فرض مرجع (علامت «assumed»)**.
   ستون `decision` منبع را ثبت می‌کند: `(title)` · `(page)` · `(image(OCR))` · `(assumed (not stated))` · `(reference (kit))`.
   - الگوهای پک، STRICT (روی صفحه/عکس، برای پرهیز از خطا): `box of N` · `pack of N` · `N x <num>ml` (مثل 10x8ml) · `<num>ml x N` (8ml x 10 / 10mlx8) · `N vials/pcs/pieces/syringes`. LOOSE (فقط عنوان): `xN` · `Nx`. فقط وقتی `۱ ≤ N ≤ ۶۰`.
   - محصولی که نامش **«Kit»** دارد، پک را از مرجع می‌گیرد (کیت بستهٔ ثابت است)، عنوان نادیده.
۶. **سایز/واحد/مادهٔ مؤثره** همیشه از **مرجع** (فیکس خطای اعشار): حجم فیلر، واحد توکسین + نوع واحد (+ ml/ویال برای توکسین مایع Relfydess ۱.۵ml، Alluzience ۰.۶۲۵ml)، اکتیو ایجنت + ml ویال چربی‌سوز.
۷. **نسخهٔ بازار:** `hologram | ROI | Irish/Ireland` در **محصول اصلی ادغام** می‌شود (کد جدا نمی‌سازد).
۸. **کد** = `TAG-BRAND-LINE[-LIDO][-NX]`. یک محصول به ازای (برند، لاین، تعداد پک، ±لیدوکائین).

### B2. روش ب — parse (برندهای بدون مرجع). `<category>_catalogue.py`
برند + لاین + spec از عنوان و صفحه (`page_facts`: متن کل صفحه در همهٔ تب‌ها، بعد OCR عکس) parse می‌شود. نویز حذف، فیکس اعشار (بخش D). این‌ها کد را می‌سازند تا وقتی مرجع برند ساخته شود.

### B3. ادغام امن بین‌محصولی. `auto_consolidate.py`
فقط در دسته‌های برنددار (توکسین، فیلر، بوستر، بایواستیم، چربی‌سوز، نخ PDO، اسکین‌کر، Beauty، مکمل، کاهش‌وزن). محصولات را بر اساس `(دسته، برند، spec نرمال‌شده)` گروه می‌کند و دو محصول را **فقط وقتی مجموعه توکن‌های هستهٔ نامشان کاملاً یکسان باشد** (برابر، نه زیرمجموعه) ادغام می‌کند. محصولات متفاوت جدا می‌مانند:
- شناسه‌های تک‌رقمی **حفظ** می‌شوند (RHA 2 ≠ RHA 3، Vol 1 ≠ Vol 2)؛
- گیج/mm/mg حفظ (30G ≠ 29G)؛ فقط ml و توکن پک `xN` از هسته حذف می‌شوند.
تعداد فروشنده/لیستینگ از ایندکس بازشماری می‌شود (ادغام هرگز دوبار نمی‌شمارد).

### B4. اندازهٔ پک = محصول جدا
تعداد پک‌های مختلف یک محصول، **کدهای جدا** هستند (۱ ویال در برابر ۱۰ ویال؛ ۱×۱ml در برابر ۲×۱ml) تا قیمت‌هر-واحد قابل مقایسه باشد. هولوگرام/ROI و تک-در-برابر-دوقلو برای نام جدا نیستند، ولی دوقلو یک SKU پکِ جدا است.

---

## C. نام نمایشی در لیست (عنوان)

اولویت در `master_catalogue.py` (بعدی، قبلی را override می‌کند):
۱. نام parse‌شده (روش ب) — `برند + لاین/variant`؛
۲. **نام canonical** (عنوان بهترین داروخانه، بخش C2) آن را override می‌کند؛
۳. **نام مرجع** هر دو را برای ردیف‌های مرجع‌محور override می‌کند و `verified = reference-matched` می‌گذارد.

**عنوان کاملِ یک‌خطی:**
- مرجع‌محور ← نام **+ presentation داخل پرانتز**: `Juvederm Ultra 4 (2 x 1ml with lidocaine)` · `Botox 100 units (1 vial)` · `Relfydess 150 units (1 x 1.5ml vial)` · `Aqualyx (10 x 8ml vials)`.
- بدون‌مرجع ← عنوان خود داروخانه **عیناً** (که از قبل سایز/پک دارد)، چیزی اضافه نمی‌شود تا سایز تکراری نشود.

### C1. کلمات نویز حذف‌شده از هر عنوان (`canonical_names.clean()`)
HTML entityها decode (`&amp;`→`&`)؛ ® ™ © حذف؛ پرانتزهای **یادداشتی** که عدد ندارند حذف (نگه‌داشتن `(1 x 2ml)`، حذف `(Discontinued)`، `(Medic Only)`)؛ `Single ` ابتدایی حذف. عبارت‌های حذفی:
`appropriate training recommended/required · stock item · prescription item · vat payable · zero/no/pay/incl/ex/inc/plus vat · available on request · out of/in stock · best seller · new in · brand new · online(/exclusive) · special offer · clearance · short dated · free delivery · next day · buy(/now/online) · shop now · uk stock · genuine · authentic · official`، و الگوهای یادداشت `exp/expiry <تاریخ> · discontinued · previously… · medic(s) only · while stocks last · limited stock · new packaging · new formula`.
کلمات تماماً کوچک، Title-case می‌شوند؛ توکن‌هایی مثل `H+L, RHA, CE, PDO, PLLA, PCL, CaHA, PDRN, PN, IU, PFS, SPF, ROI, EU, UK, HA, LED, RF, IPL, DNA, NCTF` دست‌نخورده؛ واحدها (2ml, 25g, 1x2ml) کوچک می‌مانند.

### C2. منبع عنوان برای محصولات بدون مرجع (`canonical_names.py`)
- **رتبه‌بندی داروخانه‌ها per-category**، خودکار از داده: برای هر `(دسته، داروخانه)` امتیاز = میانگینِ روی عنوان‌هایش از `(۱ اگر سایز دارد) + (۱ اگر پک دارد) − ۱.۵ اگر نویز دارد`.
  regex سایز = `\d+(ml|mg|mcg|g|%|iu)`؛ پک = `N x N | pack/box of | xN | single | double | kit | vials | syringes`؛ نویز = `stock item | vat | prescription item | out of stock | appropriate training | available on request`.
- برای هر محصول، عنوان انتخابی = از **بالاترین داروخانه در امتیاز که آن محصول را دارد**، با tie-break طولانی‌ترین عنوان تمیز (کامل‌ترین). تک‌فروشنده ← عنوان همان فروشنده.
- رتبه‌بندی کامل در `catalogue/final/title_source_priority.csv` برای بازبینی نوشته می‌شود.

---

## D. فرمت سایز/پک و فیکس اعشار
- فرمت بازار (`master_catalogue.py`): `_packspec` ← `N x Vml[ with lidocaine]`؛ `_vials` ← `N x Vml vial(s)` برای توکسین/چربی‌سوز (توکسین پودری فقط `1 vial`)؛ `_mkt` برچسب بی‌معنی `UK/std` را حذف می‌کند (فقط HG / ROI می‌ماند).
- ادغام تکراری‌های اعشاری در بوستر و فیلر: `1 == 1.0`؛ دوقلوی اعشاریِ گم‌شده `35→3.5، 15→1.5، 10→1.0` **فقط وقتی دوقلوی اعشاری از قبل موجود باشد** برای همان برند+لاین+پک(+لیدو+بازار).
- برچسب فیلد در صفحهٔ محصول = **«Pack size»** (نه «Spec»).

## E. گروه هم‌ارز (نمایش جایگزین‌ها کنار هم)
توکسین ← مولکول / «Botulinum toxin type A»؛ فیلر ← برند؛ بوستر ← کلاس فعال (Polynucleotide/PDRN · HA bio-remodelling · Amino-acid · Mesotherapy cocktail · Exosome · PRP)؛ چربی‌سوز ← اکتیو ایجنت (Deoxycholic acid · Phosphatidylcholine · Lecithin/proprietary · Mesotherapy lipolytic)؛ دارو ← مولکول؛ اسکین‌کر ← کاربرد (پیل/SPF/رتینوئید/ویتامین C/کلینزر/سرم/مرطوب‌کننده/چشم/ماسک/…)؛ سوزن ← زیرنوع؛ دستگاه ← مدالیته.
مولکول/ایجنت یکسان، برند متفاوت = کد جدا، گروه یکسان ← کنار هم به‌عنوان جایگزین نمایش.

## F. دسته‌های کالایی (spec-محور، برند = ویژگی)
سوزن/کانولا/سرنگ و مصرفی/PPE: کد = **spec** (زیرنوع + گیج + طول، یا حجم + luer، یا جنس + سایز برای دستکش)، و **برند یک ویژگی قابل‌فیلتر** است — همان spec از هر سازنده‌ای کنار هم مقایسه می‌شود (مثلاً سوزن 30G 13mm از ۱۲ فروشنده = یک کد). داروها بر اساس **مولکول فعال** (ژنریک‌ها قابل‌تعویض، سازنده ویژگی)؛ داروهای برنددار به مولکولشان نگاشت (Kenalog→triamcinolone و…).

## G. قانونی / POM
دسته‌های POM = **توکسین، همهٔ داروها، کاهش‌وزن، واکسن**. در سایت این محصولات **نمایش داده می‌شوند** (نام + مشخصات) ولی **قیمت قفل** است (`🔒 Login`) تا کاربر تأیید شود؛ بعد از verify قیمت نمایش.

## H. حالت مقایسه
محصولِ **بیش از یک داروخانه** ← مقایسهٔ قیمت (هر-واحد). تک‌داروخانه ← فقط لیست.

## I. اطمینان / verified
`reference-matched` = نگاشت به مرجع رسمی برند (بالاترین اعتماد). ردیف‌های روش ب تیر خود کاتالوگ را دارند (high / high* برند-تأییدنشده / rule / partial / review). ستون `source` مرجع به منبع لینک می‌دهد (emc SmPC، صفحهٔ سازنده/توزیع‌کنندهٔ UK).

## J. پوشش مرجع تا الان (`data/reference/`)
- **توکسین:** هر ۹ برند (emc/SmPC) — Botox, Azzalure, Dysport, Bocouture, Xeomin, Alluzience, Letybo, Nuceiva, Relfydess.
- **فیلر:** Juvederm, Teosyal, Restylane, Belotero, Revolax, Stylage, Aessoa.
- **بوستر:** Profhilo, Sunekos, Nucleofill, Jalupro, Seventy Hyal.
- **چربی‌سوز:** Aqualyx, Lemon Bottle, Lipo Lab, Deso(Face/Body), Kabelline, Dr. Lipo, Alidya, BCN Adipo, Cincelar, Mesoestetic, MesoSculpt, Inno-TDS, Pine/Skinny Bottle.
- **اسکین‌کر:** خط موضعی Profhilo (Haenkenium, Figura, Pura).
بقیه هنوز روش ب (عنوان داروخانه) تا وقتی مرجعشان ساخته شود — این کار باقی‌مانده است، دسته به دسته.

## K. خروجی بازبینی هر دسته
`scripts/category_export.py "<Category>"` ← فایل با تب **Products** و تب **Listings-per-product** (هر محصول ← داروخانه‌هایش + لینک کلیک‌کردنی لیستینگ). هر وقت یک دسته تمام شد تولید می‌شود.
