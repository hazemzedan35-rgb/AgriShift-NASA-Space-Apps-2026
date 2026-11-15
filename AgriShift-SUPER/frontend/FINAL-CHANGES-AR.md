# AgriShift — Final opening and topbar refinements

## التعديلات المحددة
- إزالة عناوين الصور الثلاث في أول مشهد من كل من `index.html` و`dashboard.html`.
- إزالة دائرة "EARTH / TO THE FIELD" التي كانت تغطي جزءًا من الصور، لتظهر الصور الثلاث وحدها.
- إزالة التدرج الداكن الذي كان مخصصًا لإبراز النص فوق الصور، للحفاظ على سطوع الصور.
- استبدال نصوص الـDashboard Topbar (`AGRISHIFT / WORKSPACE / DECISION STUDIO` و`AgriShift / FIELD COLLECTION`) بلوجو الفريق نفسه بصورة دائرية أوضح.
- إزالة شارة "OUR TEAM" المكررة من يمين شريط الـDashboard.
- الإبقاء على زر القائمة، حالة اتصال الـAPI، القائمة الكاملة، الحركات، وبيانات المحاصيل.

## ملاحظات
- صور المستخدم الأصلية موجودة كما كانت، ولم يتم تعديل ملفاتها.
- هذه النسخة Frontend فقط؛ التحليل الجديد يحتاج Backend.
- لتجربة الملفات محليًا: `cd frontend && python -m http.server 8765` ثم فتح `http://127.0.0.1:8765` و`http://127.0.0.1:8765/dashboard.html`.
