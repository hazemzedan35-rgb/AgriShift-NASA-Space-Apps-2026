# AgriShift — تحديث الداشبورد إلى AdminLTE 4

الأساس: **Stage A3** (أحدث نسخة وتشمل A1 وA2 بالكامل). لم يتغير أي كود Backend في هذه الخطوة.

## ما المشكلة التي كانت موجودة؟

`dashboard.html` القديمة لم تكن تحمّل AdminLTE أصلًا؛ كانت تستخدم ملف CSS مكتوب من الصفر (`decision-studio.css`) وبنية HTML مختلفة، وكان فيها:

- خطوط العناوين تسقط إلى خط Serif عند غياب الإنترنت (`font` بدون عائلة بديلة، و`@import` من Google Fonts).
- حقول النموذج غير متراصة (ارتفاعات مختلفة في نفس الصف).
- سهم تسلسل المحاصيل يبقى وحيدًا في آخر السطر.
- ألوان وقيم ثابتة بدل متغيرات، فلا يوجد Light mode ولا Dark mode حقيقي.

## ما الذي تغيّر؟

- `dashboard.html`: أُعيد بناؤها على بنية AdminLTE 4 (navbar وsidebar وinfo-boxes وcards وforms وprogress وbadges)، مع تبديل Light/Dark/Auto.
- `dist/css/agrishift-dashboard.css`: ملف CSS خاص صغير فقط، بمتغيرات Bootstrap.
- `dist/css/decision-studio.css`: حُذف (لم يعد مستخدمًا).
- `dist/js/decision-studio.js`: يبني نتائج الخطط والتربة بـmarkup الجديد. نفس الـIDs ونفس السلوك (إلغاء النتائج القديمة عند تغيير المدخلات وعند فشل الموقع).
- `dist/vendor/`: مكتبات القالب محلية (لا CDN).
- `tools/offline_ui_smoke.py`: أُعيد كتابتها لتحمّل الواجهة الحقيقية بالكامل.
- `tests/test_frontend_adminlte_contract.py`: اختبارات ثابتة جديدة تمنع الرجوع لـCDN أو ملفات ناقصة أو ألوان ثابتة.
- `tests/test_stage2b_decision.py`: سطر واحد يشير الآن للأصول الجديدة.

## نتيجة التحقق

- `python -m unittest discover -s tests`: **110 اختبار، OK، 1 skipped** (اتصال NASA الحي).
- `node --check`: OK.
- Chromium حقيقي (`tools/offline_ui_smoke.py`): 8 فحوص نجحت، منها: 16 و64 خطة، تغيير المحاصيل، قاعدة العائلة 16→5، رفض الاختيار الناقص، رفض الموقع غير المتاح، عدم وجود أي طلب خارجي، وعدم وجود Overflow أفقي على 390px.
- لقطة الشاشة: `outputs/AgriShift-Dashboard-AdminLTE.png`.

## لم نغيّره بعد (خطوات قادمة)

- `index.html` ما زالت صفحة استقبال بتصميم خاص (داكنة)، وتحمّل Google Fonts.
- بعض ملفات `*-AR.md` القديمة (START-HERE وVALIDATION وUPGRADE-ROADMAP...) ما زالت تصف مراحل سابقة.
- إصلاحات الـBackend (الملوحة، NASA، التواريخ...) موثقة في `BACKEND-FIXES-GROUP-A-AR.md`.
