# UPDATE — NOVEMBER 2026: ECOCROP + EGYPT CALENDAR SOURCE INTEGRATION

**See `SUBMISSION-FINAL-READ-ME-FIRST-AR.md` for the latest source-verified 12-crop data, local calendar coverage, operating instructions and limitations.** This supersedes earlier statements below describing unavailable ECOCROP profiles or four-crop-only analysis.

---

# AgriShift 12-Crop FAO-56 Evidence Edition — Submission QA

**Test date:** 2026-11-15  
**Scope:** Final merged FastAPI + editorial frontend + chatbot + expanded FAO-56 crop model.

## Automated verification

Run in the project folder:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Verified locally in this working environment:

- **154 passed; 1 skipped; 1 deselected; 84 unittest subtests passed**.
- Dedicated expansion test suite: **7/7 passed**, including per-site quantitative ETc outputs for all 12 crops, incomplete-EcoCrop unknown status, 10 annual-crop rotation screening, paddy irrigation unknown handling, and refusal to fabricate a NASA climate result during a simulated network outage.
- Previously failing legacy four-crop assertions were **migrated to assert the explicit, original four-crop baseline**, while new twelve-crop assertions are independently tested. These tests were not deleted or silently skipped.
- Existing `pytest.ini` still **ignores two obsolete AdminLTE static-contract test files** and deselects an AdminLTE asset-route assertion. The replaced cinematic UI has its own integration tests; thus the passing count does not claim every historical static contract remains applicable.
- JavaScript `node --check` passed for the modified browser assets.
- Isolated Chromium tests at 1440px and 390px with **mocked API responses** rendered 12 crop assessment cards, with no JavaScript exceptions or horizontal overflow. The browser harness did not exercise a full hosted domain, because local HTTP navigation is restricted in this environment.
- Local FastAPI `TestClient` confirms `/`, `/dashboard.html`, `/api/health`, `/api/crops`, `/api/crop-assessment`, `/api/analyze` and `/assistant/api/health` routes respond in expected offline conditions.

## Source boundaries and untested production dependencies

- The real-time **external** NASA POWER fetch for an arbitrary remote location was **not live-tested** in this sandbox. For other-than-cached sites, successful operation requires network access; errors are returned explicitly instead of substituting Nile Delta climate data.
- Gemini chat replies were **not live-tested**; they require a private server-side `GEMINI_API_KEY` and external API connectivity.
- FAO-56 Table 11 growing-period examples and Kc tables allow 12 documented **illustrative ETc** calculations. These are not field-observed evapotranspiration measurements, local agronomic advice, future forecasts, or proven water savings.
- FAO ECOCROP source CSV was **not available for direct download here**. No species envelopes are asserted and therefore climate/pH suitability remains `unknown` until species-verified source rows are imported. Soil drainage and official region-specific crop calendars are not available. This is **partial site evidence**, not complete global crop suitability.
- Flooded paddy rice has quantified atmospheric ETc but **unknown gross irrigation** (standing water, seepage, establishment). Alfalfa has only a FAO example **first-cut** model, not a complete multicut season. Neither is included in ranked hypothetical crop rotations.
- No independent agricultural field validation, global production-load, accessibility audit, or security audit was completed. Team must validate the science before deploying to farmers and add operational protections (rate limits, data policy, monitoring, secret rotation).

## Primary data provenance

- NASA POWER: <https://power.larc.nasa.gov/data-access-viewer/>
- FAO-56 Tables 11 and 12 (crop factors and examples): <https://www.fao.org/4/x0490e/x0490e0b.htm>
- FAO-56 Tables 22 and 23 (root zone and ECe): <https://www.fao.org/4/x0490e/x0490e0e.htm>
- FAO ECOCROP search: <https://gaez.fao.org/pages/ecocrop-search>
- FAO Crop Calendar (regional verification still needed): <https://cropcalendar.apps.fao.org/>

See `SUBMISSION-SCIENTIFIC-UPGRADE-AR.md` for the exact new model and crop constraints.
