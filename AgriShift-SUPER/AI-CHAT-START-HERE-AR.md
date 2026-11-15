# تشغيل الداشبورد مع شات AgriShift

1. انسخ ملف `.env` الشغّال (من مجلد agrishift (2)) إلى **جذر هذا المجلد** بجانب `START-WINDOWS.bat`.
   لو مفيش: انسخ `.env.example` باسم `.env` وضع `GEMINI_API_KEY`. لا تشارك `.env` مع أحد ولا تضعه داخل أي ZIP.
2. دبل كليك على `START-WINDOWS.bat`. يثبّت المكتبات، يشغّل السيرفر، ويفتح `http://127.0.0.1:8000/dashboard.html`.
3. اضغط زر **Ask AgriShift** أسفل يمين الصفحة. زر `ع` / `EN` داخل الشات يبدّل اللغة.
4. (اختياري) شغّل `INSTALL-ONE-CLICK-START.bat` مرة واحدة: بعدها لو السيرفر مقفول يظهر داخل الشات زر **Start AgriShift** يشغّله.
   المتصفح يسألك مرة "Open AgriShift Launcher?" وافق. لإلغاء الميزة: `reg delete "HKCU\Software\Classes\agrishift" /f`.
5. لإيقاف السيرفر: `Ctrl + C` في نافذة السيرفر.

الموديل الأساسي `gemini-3.6-flash` (حده المجاني 20 طلب/يوم)، وعند انتهائه يتحول تلقائيًا إلى `gemini-3.5-flash-lite`.
غيّر ذلك من `GEMINI_MODEL` و`GEMINI_FALLBACKS` في `.env`.
