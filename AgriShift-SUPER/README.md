# UPDATE — NOVEMBER 2026: ECOCROP + EGYPT CALENDAR SOURCE INTEGRATION

**See `SUBMISSION-FINAL-READ-ME-FIRST-AR.md` for the latest source-verified 12-crop data, local calendar coverage, operating instructions and limitations.** This supersedes earlier statements below describing unavailable ECOCROP profiles or four-crop-only analysis.

---

**Submission update (2026-11-15):** Read [SUBMISSION-SCIENTIFIC-UPGRADE-AR.md](SUBMISSION-SCIENTIFIC-UPGRADE-AR.md) for the 12-crop FAO-56 ETc extension and its explicit limitations. Older historical sections below describe the original 4-crop MVP.

> **Dashboard update:** `frontend/dashboard.html` now uses the AdminLTE 4 layout (Light/Dark, offline). See **DASHBOARD-ADMINLTE-AR.md** and `frontend/INTEGRATION-AR.md`.

**LATEST UPDATE (STAGE A3): Dynamic Rotation Generator** — select 2, 4 or 6 alternating seasons, choose an eligible crop pool, optional strict adjacent-family rule, rank all generated sequences, display up to 64. See `ROTATION-STAGE-A3-AR.md`. Historical NASA 2025 analogues are NOT forecasts.

# Stage A2 update — Soil Intelligence

See **SOIL-STAGE-A2-AR.md** for the new soil screening, formulas, data sources, examples and limitations. The new optional fields are `soil_awc_mm_per_m` and `soil_ece_ds_m`, and the dashboard now displays TAW, RAW and salinity signals. Soil water storage is NOT added to ETc or treated as an actual irrigation schedule. No ML has been trained.

---

# AgriShift — NASA × FAO Crop Rotation Research MVP

**Status:** Runnable research prototype, not a field-ready agricultural decision tool. 2025 NASA POWER records + FAO-56 ET0 + reference Kc-based crop ETc + four transparent two-season rotation comparisons + interactive farmer-input dashboard. No trained machine-learning model.

## Quick start

```bash
python -m pip install -r requirements.txt   # Python 3.10 or newer
python start_agrishift.py
# Browse http://127.0.0.1:8000
```

Windows users can also double click `START-WINDOWS.bat` if Python is installed. See [Arabic Quick Start](START-HERE-AR.md).

## API

- `GET /api/health`: local dataset status
- `GET /api/climate`: actual 2025 reference climate summary
- `GET /api/monthly`: monthly reference ET0
- `GET /api/crops`: crop coefficients and provenance
- `POST /api/analyze`: request farm screening comparison

Example JSON:

```json
{"latitude":30.5,"longitude":31.5,"area_ha":1,"water_budget_m3":14500,"irrigation_efficiency":0.75,"previous_crop":"wheat","priority":"balanced","soil_type":"clay"}
```

## System architecture

```
NASA POWER Daily (original JSON + verified CSV)
                     ↓
      FAO-56 daily reference ET0
                     ↓
FAO Table 11 stage durations and Table 12 Kc
                     ↓
  Stage 2b: ETc per hypothetical crop season
                     ↓
Farmer area + water budget + assumed efficiency
                     ↓
4 fixed winter → summer two-season scenarios
                     ↓
Explainable relative score + feasibility + caveats
                     ↓
FastAPI /api/analyze → responsive dashboard
```

## Data provenance and important limitations

NASA metadata saved in `outputs/nile_delta_2025/metadata.json`; `LIVE_NASA_API` records. Coordinates 30.5 N, 31.5 E; Local Solar Time; Jan 1–Dec 31, 2025; eight daily weather parameters. Files copied directly from the uploaded Stage 1 output and consistent with the original saved JSON. These are gridded estimates, not measurements inside a farmer's field. Stage A1 adds on-demand historical NASA POWER climate for user-selected coordinates; original pilot is bundled for offline use. New locations are cached only after successful NASA retrieval.

The FAO ET0 engine previously validated against an official textbook worked example; some of its assumptions include mean daily RH, nominal zero-meter altitude and cloud-factor bounds. ETc uses FAO-56 standard crop coefficients and published example stage lengths, none locally calibrated. Future 2026–27 scenario dates use 2025 observations mapped by month/day: **historical seasonal analog**, never presented as future weather forecast, climate normal or predictive ML. Gross "water proxy" intentionally excludes effective rain credit and soil water balance, so **NOT actual field irrigation needs**.

The score only compares the four candidates under transparent weights. It is NOT a soil-health metric, probability of success or yield forecast. Soil texture is collected but does not influence the engine until local agronomy rules are verified. Dry maize grain and fresh faba bean are different harvest products; compare only as illustrative alternatives, not equal expected prices or yields.

## Tests

```bash
python -m pip install -r requirements-dev.txt   # test-only dependencies (HTTP client for FastAPI's TestClient)
python -m unittest discover -s tests -v
```

70 tests including 10 dynamic-location cases; 1 optional live-network test is skipped. No real-time external API fetch is needed to use the bundled 2025 pilot point. Other points need NASA connectivity for their first request.

## References

- [NASA POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)
- [FAO-56 Crop ET methodology](https://www.fao.org/4/X0490E/x0490e0a.htm)
- [FAO-56 Table 11 stage durations / Table 12 crop coefficients](https://www.fao.org/4/X0490E/x0490e0b.htm)
- [FAO Crop Diversification](https://www.fao.org/conservation-agriculture/in-practice/species-diversification/en/)
- [Egypt seasonal crop categories](https://barp.org.in/node/2978)

[Arabic upgrade roadmap](UPGRADE-ROADMAP-AR.md)

## Next research work

1. Local crop stage and date calibration with Egyptian agronomists/extension literature.
2. Effective precipitation and soil water balance (FAO-56/FAO-CROPWAT) for defensible irrigation requirement, water availability over time, field soil measurements.
3. Separate satellite context via HLS / SMAP with spatial-resolution caveats.
4. Validated ML only with target labels and held-out testing, with transparent improvement over non-ML baseline.
