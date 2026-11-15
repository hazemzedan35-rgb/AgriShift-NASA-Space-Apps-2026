### Stage A3 — مولد ديناميكي: نُفذت واختُبرت محليًا

المرحلة التالية: تخطيط مناخي بسنوات تاريخية متعددة وسيناريوهات عدم يقين؛ ثم التحقق العلمي من الأمثلة المحلية.

# AgriShift | Upgrade roadmap: 4 fixes + final verification

**Current milestone:** A1 / Dynamic location = implemented in this ZIP, subject to live NASA test at a second location.

## 1 — Dynamic farm coordinates (implemented)
- Dashboard now accepts latitude and longitude, rounded to 4 decimal degrees (reported in output).
- `POST /api/analyze` obtains 2025 NASA POWER daily observations for the selected location, calculates daily FAO-56 ET0, then recalculates candidate comparisons.
- Original (30.5 N, 31.5 E) loads directly from saved, provenance-checked data and works offline.
- Other locations require network access on first query; validated outputs are cached per exact normalized coordinate on disk, and reused offline later.
- NASA failure returns 503 and no simulated fallback is silently represented as real data.
- Quality checks: 365 dates, eight parameters, units, missing values, physical plausibility. Tests mock NASA only; a real request for an additional location must be checked manually.
- Limitation: uses historical 2025 data, not future forecasts. For large-scale deployment add grid-aware caching, request-rate control, batch processing, monitoring, retry policy and user-driven data availability checks.

## 2 — Soil input influences scientifically supported constraints (not implemented)
- Farmer provides soil texture, drainage, and optional measured values (field capacity, wilting point, rooting depth, salinity, laboratory results) with units and source/quality.
- If enough measured information exists, implement FAO-style daily soil-water balance and root-zone water capacity; change irrigation-feasibility assessments.
- Avoid invented soil suitability and numerical soil-health scores. Missing measurements remain `unknown` and do not cause made-up penalties.
- Tests: same climate and crop with demonstrably different **measured** water holding capacity should change water-stress risk under the same water delivery schedule; unknown soil leaves score unverified.

## 3 — Generate feasible crop rotations, not four hard-coded pairs (not implemented)
- Build an expanded locally documented crop catalog (calendar, stage Kc, crop family, growing duration, agroecological constraints, pests/rotation cautions), validated for Egyptian pilot zone.
- Generate valid multi-season combinations with backtracking/constraint solver; screen for season/calendar overlap, water capacity by season, previous crop history and supported restrictions.
- Ranking reports which rules excluded a sequence and compares feasible plans by farmer priorities; no unvalidated crop yield claims.
- Tests: repeatable generation, forbidden overlaps filtered, input priority changes sorting, every explanation traceable.

## 4 — Future seasons (not implemented)
- Separate three modes: (A) historical 2025 retrospective, (B) multi-year climatological planning using several actual past years, and (C) climate projection stress-test for longer horizons.
- Never present a past year replay or NASA POWER CMIP6 SSP scenarios as a weather forecast for an exact upcoming season.
- Add uncertainty bands / sensitivity instead of falsely precise future values; real short-term forecasts require an independent qualified forecast feed if added.
- Tests: explicit mode labels, temporal splits, no dates beyond source coverage represented as observations, spread across years/models.

## 5 — End-to-end verification (not implemented)
- Test browser + API, independent reference FAO/CROPWAT cases, spatial data provenance, edge cases, performance, deployment reliability and model limitations.
- Label validated science separately from estimated or user-reported inputs.
- ML is NOT required to resolve these four defects. It may be added later only with a defined target, suitable training labels and held-out evaluation.

## Running this release
```
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python start_agrishift.py
```
Open http://127.0.0.1:8000/dashboard.html. Input example **30.5, 31.5** (cached) or another latitude/longitude (live first request). New outputs are in `outputs/location_cache/`.

## Sources
- https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- https://power.larc.nasa.gov/docs/services/api/projection/
- https://www.fao.org/land-water/resources/tools/software/cropwat/en
