# AgriShift Architecture — Stage 1

```
Farmer location (30.5 N, 31.5 E)
          │
          ▼
  PowerRequest (validated)
          │
          ▼
NASA POWER /api/temporal/daily/point
          │
          ▼
  raw_nasa_response.json ────────┐
          │                      │
          ▼                      ▼
  parser / date-grid       metadata (API version,
  / missing-value check     sources, units, request)
          │
          ▼
  QA checks: units, dates, missing, impossible values
          │
          ├── daily_climate.csv / daily_climate.json
          ├── monthly_summary.csv
          └── quality_report.json
```

## Boundaries

- `agrishift_power/config.py`: input validation, requested parameters and URL.
- `agrishift_power/client.py`: HTTP timeout, retries for 429/5xx, API errors.
- `agrishift_power/transform.py`: strict response parsing, missing value and unit checks.
- `agrishift_power/output.py`: write artifacts with provenance and aggregate summaries.
- `agrishift_power/cli.py`: runnable commands, cache and offline fixture.
- `tests/`: data fixtures, deterministic offline unit tests, optional live integration test.
- `frontend/`: existing AgriShift frontend **still mock-backed**.

## Integration contract for Stage 2

Consume `daily_climate.json` or `daily_climate.csv`, and check `metadata.json` plus `quality_report.json` first. Don't run FAO calculations when unit warnings or missing required values are unresolved. Stage 2 must implement FAO-56 rigorously and test its ET0 against published reference examples. Stage 3 then adds rotation constraints and comparisons.
