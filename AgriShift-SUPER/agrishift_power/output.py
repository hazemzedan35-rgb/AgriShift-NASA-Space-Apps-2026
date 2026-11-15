"""Write raw evidence, clean data, summaries, and source/quality metadata."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from .config import PARAMETERS, PowerRequest


def write_json(path: Path, obj: dict | list) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def month_summary(rows: list[dict]) -> list[dict]:
    """Never present a partial rainfall sum as a full-month total."""
    result = []
    months = sorted({row["date"][:7] for row in rows})
    for month in months:
        items = [r for r in rows if r["date"].startswith(month)]
        def avg(p):
            xs = [r[p] for r in items if r[p] is not None]
            return round(mean(xs), 3) if xs else None
        def total_if_complete(p):
            xs = [r[p] for r in items if r[p] is not None]
            return round(sum(xs), 3) if len(xs) == len(items) else None
        result.append({
            "month": month, "days_in_selection": len(items),
            "mean_temperature_c": avg("T2M"),
            "precipitation_total_mm": total_if_complete("PRECTOTCORR"),
            "mean_relative_humidity_pct": avg("RH2M"),
            "solar_radiation_total_mj_m2": total_if_complete("ALLSKY_SFC_SW_DWN"),
        })
    return result


def save_outputs(out: Path, request: PowerRequest, payload: dict,
                 rows: list[dict], report: dict, *, source_mode: str) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "daily_climate.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("date", *PARAMETERS))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "" if v is None else v for k, v in row.items()})
    write_json(out / "daily_climate.json", rows)
    write_json(out / "raw_nasa_response.json", payload)

    monthly = month_summary(rows)
    with (out / "monthly_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=monthly[0].keys())
        writer.writeheader()
        writer.writerows(monthly)

    write_json(out / "quality_report.json", report)
    meta = {
        "project": "AgriShift",
        "stage": 1,
        "source": "NASA POWER Daily Point API",
        "source_mode": source_mode,
        "data_status": "SYNTHETIC_FIXTURE_NOT_NASA_OBSERVATIONS" if source_mode == "fixture" else (
            "IMPORTED_JSON_VERIFY_PROVENANCE" if source_mode == "imported" else "LIVE_NASA_API"),
        "fetched_or_processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "request": request.as_dict(),
        "nasa_header": payload.get("header", {}),
        "nasa_parameters": payload.get("parameters", {}),
        "nasa_geometry": payload.get("geometry", {}),
        "nasa_messages": payload.get("messages", []),
        "quality_summary": {"science_ready": report["science_ready"] and source_mode == "live",
                            "all_parameters_fully_available": report["all_parameters_fully_available"]},
        "disclaimer": "Regional gridded climate estimates; not field sensor measurements. No FAO/ET0 calculations performed in Stage 1.",
    }
    write_json(out / "metadata.json", meta)
    return meta
