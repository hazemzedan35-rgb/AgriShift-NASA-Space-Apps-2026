# UPDATE — NOVEMBER 2026: ECOCROP + EGYPT CALENDAR SOURCE INTEGRATION

**See `SUBMISSION-FINAL-READ-ME-FIRST-AR.md` for the latest source-verified 12-crop data, local calendar coverage, operating instructions and limitations.** This supersedes earlier statements below describing unavailable ECOCROP profiles or four-crop-only analysis.

---

# AgriShift — FAO-56 12-Crop Scientific Upgrade (Submission edition)

## What's really implemented
- Twelve crop entries with individual FAO-56 Table 12 Kc profiles, Table 11 published example stage durations (regional examples, not Egyptian growing calendars), and quantitative ETc calculations on NASA POWER historical 2025 data for the supplied coordinates.
- `POST /api/crop-assessment`: twelve individual ETc outputs, estimated mm, dates and rainfall *context*, FAO-56 soil root-zone storage (Table 22), source-traceable salinity comparisons (Table 23), and explicit unknown status for missing soil pH, drainage, local calendar or EcoCrop temperature envelopes. No composite percentage invented.
- Ten annual crops can participate in hypothetical `POST /api/analyze` rotations. The model filters calendars that overlap. The first 4 original crops remain selected by default for backward compatibility; the UI supports choosing up to 10 eligible crops.
- Paddy rice: **ETc only**. Actual paddy water requirements include standing-water management, land preparation, percolation, etc., none of which are modeled here; return `gross_planning_proxy_m3: null`, not a fabricated number. Excluded from rotation ranking.
- Alfalfa: **first cutting (60-day published FAO example) only**, not full hay-growing season or multiple cuttings. Excluded from rotation ranking.
- New dashboard section `#crop-suitability` shows all twelve crop ETc and known/unknown screening evidence; no display of fictitious suitability percentage.
- Latitude and longitude sent by GPS or fields; data from NASA POWER per coordinates when network is available (or exact-position cache). The provided 2025 Nile Delta dataset remains available for the pilot.

## Critical scientific honesty
- Historic 2025 NASA POWER is not a forecast or multi-year climatology. No guaranteed water saving or yield projection.
- FAO-56 Table 11 gives *location-specific examples from other regions* (including Egypt for cotton) and may have discrepancies between sum of stage days and published total (notably sorghum); source stage values are retained with explanatory metadata.
- FAO-56 Table 12 Kc figures describe non-stressed managed crops in reference climatic conditions. Some entries are published ranges; selected endpoints are recorded in each crop entry. No locally calibrated Kc curves.
- The sowing *day* is a software planning convention because Table 11 usually provides only month. The tool MUST NOT present those days as FAO-issued advice or validated planting calendar.
- Soil ECe is saturated-paste EC, not irrigation-water EC. Sunflower has no numeric threshold in Table 23; tomato has a range, therefore not reduced to an arbitrary single threshold.
- Crop suitability is **partial** until matched ECOCROP environmental envelopes, true soil pH/drainage, regional crop calendars and local specialist review exist. No fake climate/soil percentage.

## FAO ECOCROP import (conditional, not bundled)
The provided GitHub page points to `EcoCrop_DB.csv`, but direct external CSV download was unavailable in this execution environment. No numeric EcoCrop records were fabricated. To enable temperature and soil-pH envelope diagnostics after sourcing a verified CSV:

1. Download the original `EcoCrop_DB.csv` from <https://github.com/OpenCLIM/ecocrop> and verify provenance against FAO ECOCROP <https://gaez.fao.org/pages/ecocrop-search>.
2. `python tools/import_ecocrop.py /path/EcoCrop_DB.csv --list-candidates` shows exact matches and EcoPort IDs.
3. Review each scientific species/cultivar (especially *Beta vulgaris*, *Gossypium* varieties). Create a JSON map from AgriShift crop ID to verified source row ID; don't guess species from a common name.
4. `python tools/import_ecocrop.py /path/EcoCrop_DB.csv --selection verified-selection.json` creates source-traceable `ecocrop_profiles.json` locally. Each profile includes FAO mirror source URL, original species and row identifier.
5. Run tests and independently validate for target regions before making location-specific suitability claims.

No fake GEO services: **GAEZ layer download, AppEEARS, FAO Crop Calendar live API and CROPWAT executable are NOT integrated**. Their official links are provided for research and later data acquisition only.

## Test commands

```
python -m pip install -r requirements.txt
python -m pytest -q tests/test_submission_12crop.py
python start_agrishift.py
```

The former four-crop legacy test expectations have been kept as regression checks by explicitly selecting the original four-crop baseline. The updated complete test suite is passing; see `SUBMISSION-TEST-RESULTS.md` for the test counts, ignored obsolete AdminLTE checks, and limits of offline verification.

## Primary provenance
- FAO Irrigation and Drainage Paper 56, Ch. 6 Tables 11 & 12: <https://www.fao.org/4/x0490e/x0490e0b.htm>
- FAO Irrigation and Drainage Paper 56, Ch. 8 Tables 22 & 23: <https://www.fao.org/4/x0490e/x0490e0e.htm>
- FAO ECOCROP species data portal: <https://gaez.fao.org/pages/ecocrop-search>
- GAEZ context: <https://www.fao.org/gaez/en>
- NASA POWER: <https://power.larc.nasa.gov/data-access-viewer/>
- FAO CROPWAT: <https://www.fao.org/land-water/resources/tools/software/cropwat/en>
- FAO Crop Calendar: <https://cropcalendar.apps.fao.org/>
- NASA AppEEARS (not integrated): <https://appeears.earthdatacloud.nasa.gov/>
