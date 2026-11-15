# AgriShift — Final submission QA

## Latest local tests

- `python -m pytest -q --ignore=tests/test_frontend_adminlte_contract.py` → **159 passed, 1 skipped, 1 deselected, 84 subtests passed**.
- The skipped test is an optional live external NASA request. The deselected test suite contains legacy AdminLTE-only checks; the project now uses the separate cinematic frontend.
- The evidence tests cover all 12 EcoPortCode identities and bounds, Egypt regional calendar provenance and missing crops, unknown GPS-to-zone assumptions, soil pH/texture/drainage input, and source-aware API results.
- Isolated Chromium smoke testing on **1440px desktop and 390px mobile** using real frontend JS, real local API test-response and HTML verified: **12 rendered crop cards, source IDs, Egypt Excel row provenance, zero JS page errors, no horizontal overflow**.
- `node --check` was run against `crop-evidence.js`, `decision-studio.js` and `crop-atlas.js`.
- Historical NASA data were read from the project's existing bundled pilot data (2025). External NASA POWER retrieval at a fresh location was not run in this environment.
- Gemini chatbot live replies and deployment security/rate limiting have not been independently tested. A browser demo does NOT certify agronomic validity.

## Model scope

- FAO-56 ETc calculations: 12 profiles, representative published stages (not actual irrigation schedules).
- Rotation ranking: 10 annual profiles, hypothetical; environmental ECOCROP checks are **advisory only**, NOT used to silently approve planting or to assert optimal crops.
- Field suitability: six possible dimensions (temperature, measured soil pH, measured soil ECe, farmer-reported texture, farmer-reported drainage, regional crop calendar availability). With missing data, outputs explicitly remain partial.
- Rainfall: separate annual rainfed reference; never a viability veto for irrigated farms.
- Calendar: manual Egypt zone selection; not spatially inferred from GPS. FAO-56 illustrative sowing is still used in ETc/rotation code.
- No fabricated global suitability score, modeled yields, profit, water savings, future forecast, or soil measurements.

## Submission/demo procedure

1. Install requirements, start `start_agrishift.py`.
2. Visit dashboard; choose sample coordinates 30.5,31.5 and optionally `Delta region`.
3. Run Suitability Lab; confirm 12 profiles, 12 ECOCROP records and 7 matching Delta-calendar crop profiles.
4. Optionally supply actual measured soil pH / ECe / texture / drainage (do not invent values).
5. Expand a crop's sources, verify ECOCROP code and original Excel row. Export JSON.
6. Run rotation plans and read the per-plan site warnings. Compare with historical (not forecast) chart.
7. Test an actual new location with working internet and a real Gemini key separately before a public demo.
