# AgriShift Dynamic Location — Verification Report

**Date:** 2026-11-13  
**Scope:** Stage A1 (Dynamic NASA POWER location) + preexisting FAO/rotation MVP.  
**Important:** A passed test does not prove agronomic suitability or live NASA availability everywhere.

## Result

- Python unit/integration suite: **71 tests, 70 passed, 1 skipped, 0 failed**.
- FastAPI endpoints tested with `TestClient`: `/`, `/dashboard.html`, `/api/health`, `/api/climate`, `/api/monthly`, `/api/analyze` returned HTTP 200 on the bundled pilot location.
- Invalid latitude (`95`) returned HTTP 422.
- Mocked NASA unavailability returned HTTP 503 instead of silently substituting pilot data.
- Two distinct **synthetic test-fixture** locations (30.7,31.6) and (31.2,31.6) returned distinct temperatures and ET0 values; repeated point used the matching point-specific cache. This is a logic/integration test, **not live NASA confirmation**.
- Chromium offline JavaScript/UI smoke tests: initial four candidates; changing water budget updated budget feasibility; mock API errors cleared old climate and plans; response for a location changed while loading was ignored; no uncaught JS errors.
- JavaScript syntax checked with Node.js; ZIP integrity verified.

## One real bug fixed

Before the fix, a failed NASA request could leave previous-location plans and climate numbers on screen. Now the frontend clears stale analysis when inputs change or a request starts, disables export, reports the failure, and ignores stale asynchronous responses. **Never show old farm data as if it belonged to the new location.**

## Not yet verified

- **Live request to NASA for a second point.** This runtime cannot resolve external NASA hostnames. This skip is environment-related, not a test pass.
- Browser-to-live-localhost integration in this environment (browser access to localhost is blocked). The API was tested directly with TestClient; the actual UI JS/CSS/HTML was tested in Chromium with explicit mock responses.
- Site-specific crop-calendars, soil effects, dynamic rotation generation, multi-year climate scenarios, ML, and real agronomic field validation are **not implemented** at this stage.

## Run locally (Windows PowerShell)

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python start_agrishift.py
```

Open `http://127.0.0.1:8000/dashboard.html`, use (30.5,31.5) first, and then try (30.7,31.6) online. On a first successful new NASA location, point-specific output is cached under `outputs/location_cache/`.

Optional browser-only smoke test (needs Playwright and Chromium installed):

```powershell
python -m pip install playwright
python -m playwright install chromium
python tools/offline_ui_smoke.py
```

The UI smoke script automatically uses the system Chromium when installed, otherwise Playwright's browser installation.

## Science caveats

The climate used for future proposed seasons is **NASA 2025 historical analogue**, not a forecast. ETc calculation is a reference-crop, single-Kc approach; resulting gross water figures are **planning proxies**, not irrigation prescriptions. Soil texture is collected but not yet evaluated; rotation ranking is relative to four predefined candidates. Farmer/field measurement and local expert calibration remain necessary.
