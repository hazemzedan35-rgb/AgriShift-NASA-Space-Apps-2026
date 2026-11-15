# UPDATE — NOVEMBER 2026: ECOCROP + EGYPT CALENDAR SOURCE INTEGRATION

**See `SUBMISSION-FINAL-READ-ME-FIRST-AR.md` for the latest source-verified 12-crop data, local calendar coverage, operating instructions and limitations.** This supersedes earlier statements below describing unavailable ECOCROP profiles or four-crop-only analysis.

---

# AgriShift SUBMISSION 2026 — التشغيل

1. افتح Terminal داخل مجلد `AgriShift-SUPER`.
2. `python -m pip install -r requirements.txt`
3. `python start_agrishift.py`
4. افتح `http://127.0.0.1:8000/` ثم الـDashboard.
5. اختار موقع الأرض (GPS أو الإحداثيات)، وبعدها اضغط **Assess all 12 crops** عشان تشوف حساب ETc لكل الـ12 وملاءمة الموقع حسب البيانات المتوفرة فعلاً.
6. لاختيار خطة تدوير، اختار من العشرة محاصيل السنوية الصالحة للمقارنة، ثم **Analyze rotation plans**.

الشات بوت يحتاج متغير `GEMINI_API_KEY` بشكل سري على السيرفر، واتصالًا بالخدمة. لم يتم دمج أي مفتاح حقيقي في هذا الملف.

**اقرأ `SUBMISSION-SCIENTIFIC-UPGRADE-AR.md` قبل التسليم.** مش كل خاصية من المصادر الخارجية متوصلة أو متحققة علمياً؛ خصوصًا بيانات ECOCROP الرقمية غير موجودة في الملف لأن تنزيل CSV لم ينجح، وبالتالي الحدود المناخية وpH تظهر Unknown، مش نسبة نجاح غير موثقة.

الـAPI الرئيسية: `/api/health`, `/api/climate`, `/api/monthly`, `/api/crops`, `/api/analyze`, `/api/crop-assessment`, `/api/data-sources`، والشات بوت `/assistant/api/chat`.

من غير اتصال NASA، الموقع الجديد الذي لا يوجد له كاش سيظهر HTTP 503 بدون اختلاق مناخ. مثال الدلتا التاريخي 2025 متاح للتجربة المحلية. GPS يتطلب HTTPS أو localhost وموافقة المستخدم.
