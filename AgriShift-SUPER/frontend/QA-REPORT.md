# AgriShift Cinematic Frontend QA

Status: **frontend upgrade complete for handoff; online photographic delivery must still be checked on a normal internet-connected browser.**

## Completed checks
- JavaScript syntax: `node --check dist/js/decision-studio.js` and `node --check dist/js/cinema-effects.js` — PASS.
- HTML parser: both pages parse; unique `id` attributes — PASS.
- In-memory headless Chromium desktop 1440x900 and mobile 390x844 — no uncaught JS errors.
- Horizontal viewport: no page-level overflow at 1440px or 390px — PASS.
- Fullscreen menu opens, Escape closes and focus is returned — PASS in desktop test.
- Landing carousel arrow shifts scroll position — PASS.
- Mocked original API using bundled real pilot JSON: shows 4 plans, within-budget shows 2; compare and stale results handling — PASS.
- Map URL generation from numeric coordinates and coordinate range validation — PASS.
- Scientific calculation implementation unchanged — PASS by source inspection; **no new scientific correctness claim**.

## Limitations / checks for teammate to complete
- Browser environment blocked direct HTTP/file navigation; tests used in-memory HTML/CSS/JS. Server API+frontend combined deployment not tested directly here.
- Live third-party image download blocked in sandbox; external photographic media links were confirmed from Wikimedia source pages, but rendering in the user's browser needs final verification.
- Wikimedia Commons may have zero nearby geotagged images at a coordinate; the UI reports this instead of making up field imagery.
- OpenStreetMap embeds depend on browser/network settings.
- User-provided badge contains NASA marks; check official use/compliance before submitting as a competition asset.
- The existing backend fixed-location limitation remains unchanged. Newer backend integration requires response contract agreement.

## Original backend smoke-test added
After merging the new `frontend/` into the unchanged `AgriShift-Working-MVP(1)` backend:
- `python -m unittest discover -s tests -q`: **60 tests, 0 failures, 1 skipped**. The negative quality-control fixture prints an expected warning about a deliberately invalid NASA response.
- `python frontend/verify_integration.py --base http://127.0.0.1:8977`: **PASS** for health, climate, 12 monthly records and analyze response.
- HTTP GET for `/`, `/dashboard.html`, `/dist/css/cinema-overrides.css`, `/dist/js/cinema-effects.js`, `/dist/img/team-logo.webp` and `/dist/css/decision-studio.css`: **200 OK**.
