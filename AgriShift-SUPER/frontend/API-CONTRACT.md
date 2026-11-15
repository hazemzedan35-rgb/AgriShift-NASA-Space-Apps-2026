# AgriShift Frontend/Backend API Contract — Current MVP

**Status:** verified against the supplied `AgriShift-Working-MVP(1).zip`; not a contract for a hypothetical updated backend.

## Transport and origin

The frontend uses same-origin relative routes (`/api/...`). For local development, serve `frontend/` using the FastAPI app, or configure a reverse proxy for API routes. A separate `python -m http.server` serves only the **saved reference preview** and cannot run interactive calculations. No CORS workaround, tokens or client-side provider URL input is required for the current prototype.

## GET /api/health

Response fields:

```json
{"ok":true,"project":"AgriShift","date_count":365,"data_source":"LIVE_NASA_API"}
```

`data_source` is provenance metadata of the saved historical dataset, not a statement that the current request made a live NASA network call.

## GET /api/climate

Required response:

```json
{
  "year":2025,
  "latitude":30.5,
  "longitude":31.5,
  "average_air_temperature_c":23.2,
  "annual_rain_mm":39.81,
  "annual_reference_et0_mm":1995.712,
  "daily_mean_reference_et0_mm":5.468,
  "source":"NASA POWER daily point API, processed with FAO-56",
  "time_standard":"LST"
}
```

## GET /api/monthly

```json
{"year":2025,"months":[{"month":"2025-01","eto_total_mm":69.725,"daily_mean_mm":2.249}]}
```

All 12 months must be supplied to render the chart. This excerpt is a **shape illustration**, not a complete chart dataset.

## POST /api/analyze

Current MVP request:

```json
{
  "area_ha":1,
  "water_budget_m3":14500,
  "irrigation_efficiency":0.75,
  "previous_crop":"wheat",
  "priority":"balanced",
  "soil_type":"unknown"
}
```

Original validation:
- `area_ha`: 0.01–10,000 hectares.
- `water_budget_m3`: 0–1,000,000,000 cubic meters (**TOTAL for both seasons**, not per season).
- `irrigation_efficiency`: 0.35–1.00.
- `previous_crop`: `wheat`, `faba`, `maize`, `sunflower`, `unknown`.
- `priority`: `balanced`, `water`, `diversity`.
- `soil_type`: `unknown`, `clay`, `loam`, `sand` (context only in this backend).

Response fields required by current UI:

```json
{
  "project":"AgriShift",
  "status":"RESEARCH_PROTOTYPE",
  "climate":{"year":2025,"average_air_temperature_c":23.2,"annual_rain_mm":39.81,"annual_reference_et0_mm":1995.712},
  "inputs":{"area_ha":1,"water_budget_m3":14500,"irrigation_efficiency":0.75,"previous_crop":"wheat","priority":"balanced","soil_type":"unknown"},
  "plans":[
    {
      "id":"faba-sunflower",
      "rank":1,
      "crops":[{"id":"faba","name":"Faba bean (fresh harvest)","season":"winter","planting_date":"2026-11-10","harvest_estimated_date":"2027-02-17","crop_et_mm":232.19,"gross_planning_proxy_m3":3095.88}],
      "water_proxy_m3":14012.68,
      "budget_difference_m3":487.32,
      "within_total_budget":true,
      "comparison_score":100.0,
      "diversity_heuristic":100.0,
      "comparison_weights":{"water":0.55,"diversity":0.45},
      "signals":["Historical 2025 climate analogue only; not a weather or yield forecast."]
    }
  ]
}
```

The above response contains a **single illustrative crop entry** to show field names; the real backend returns full rotations. Use real responses for the UI.

The frontend does **not** calculate `ET0`, `ETc`, plan scoring, crop suitability, or water demand. Values come directly from the server. It only visualizes, filters and compares returned results.

### Error handling

- `422` Pydantic validation errors or `HTTPException.detail` are rendered as friendly text.
- Offline/unexpected responses hide previous analysis results and disable export.
- In-flight requests are aborted/invalidated on input changes; stale analysis cannot overwrite newer data.
- Plan strings are inserted using `textContent`, not `innerHTML`.

## Important contract decisions for next backend

1. Agree on a **versioned** `GET /api/v1/capabilities` response before exposing new controls. Suggested capability names are proposed, not currently implemented: `dynamic_location`, `seasons_4_6`, `soil_screening`, `year_selection`, `multi_year_scenarios`.
2. Preserve `/api/analyze` shape or supply a documented response adapter. The renderer already loops over `plans[]` and `plan.crops[]`, so it can display longer sequences if the server returns these fields, but the FORM does not request them yet.
3. Make `/api/climate` and `/api/monthly` location-aware if the backend allows new farms; the original routes return fixed reference data regardless of location.
4. Agree on exact water-budget semantics: whole horizon vs per season, units, and treatment of rainfall.
5. Include `data_source`, `reference_year`/scenario information, provenance and uncertainty in new responses. The frontend must label historical analogues correctly.
6. Add new inputs **only after** the new API endpoint, validation and contract tests are confirmed. Keep API credentials server-side.
7. Public deployment should add appropriate throttling, security headers and data handling policies in the backend and reverse proxy; not implemented by frontend-only changes.

## Quick contract smoke test

Run the original backend, then:

```powershell
python verify_integration.py --base http://127.0.0.1:8000
```

A passing HTTP contract check is necessary, but not sufficient, for real-field agricultural validation.
