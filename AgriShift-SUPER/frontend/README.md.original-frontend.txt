# AgriShift Field Collection — Frontend-only handoff

This is the frontend-only update based on the user-provided cinematic frontend ZIP. No backend source files changed.

**Start here:** `DISPENSA-REDESIGN-HANDOFF.md` (features, motion, limitations, and QA), `API-CONTRACT.md` (existing API fields), `PHOTO-CREDITS.md` (real photo sources).

## Files
- `index.html` — redesigned editorial homepage.
- `dashboard.html` — crop collection and functioning Decision Studio.
- `dist/css/dispensa-inspired.css` — new independent design layer.
- `dist/js/dispensa-interactions.js` — collection interactions.
- `dist/js/decision-studio.js` — original unmodified analysis behavior.
- `dist/img/team-logo.webp` — supplied team badge.

## Run with original legacy backend
Extract the original `AgriShift-Working-MVP(1).zip`. Replace its `frontend/` directory with this one. In the project root run:

```powershell
python -m pip install -r requirements.txt
python start_agrishift.py
```

Open `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/dashboard.html`.

## Preview without backend

```powershell
cd frontend
python -m http.server 8765
```

Open `http://127.0.0.1:8765/dashboard.html?preview=1` to use the **saved, explicitly labeled old pilot result**. New analysis requires a running API. All bundled visuals are served locally; internet is not required for the imagery in this package.

The current pilot backend is still fixed to one reference coordinate and two seasons. Visual selection never changes the agricultural backend analysis. All recommendations should be independently validated locally.


## Offline behavior
- Visual assets are bundled locally.
- Remote font loading was removed; the UI uses local/system fallback fonts offline.
- Interactive analysis still needs the backend API.


## Lite 2026-11-14 image bundle
This lightweight build replaces the previous large PNGs with local WebP assets. The bundled images are AI-generated visual illustrations; authentic licensed photographs have **not** yet been embedded. See `PHOTO-CREDITS.md` for provenance.

## AgriShift floating chatbot widget

Both the homepage and Decision Studio now show the same floating chat button and panel. **The real chatbot API endpoint was not included in the supplied frontend ZIP**, so the UI displays a connection-pending notice until the team connects it. See [`CHATBOT-INTEGRATION-AR.md`](CHATBOT-INTEGRATION-AR.md) and edit `dist/js/agrishift-chat-config.js` with the real endpoint and request/response contract.
