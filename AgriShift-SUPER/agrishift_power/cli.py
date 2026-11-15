"""Command line interface; one NASA request per unique query, cached thereafter."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .client import PowerAPIError, fetch_daily
from .config import PowerRequest
from .output import save_outputs
from .transform import PowerDataError, parse_response


def _date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="AgriShift Stage 1 — NASA POWER Daily Data Pipeline")
    p.add_argument("--lat", type=float, default=30.5, help="Latitude; default 30.5")
    p.add_argument("--lon", type=float, default=31.5, help="Longitude; default 31.5")
    p.add_argument("--start", type=_date, default=date(2025, 1, 1))
    p.add_argument("--end", type=_date, default=date(2025, 12, 31))
    p.add_argument("--time-standard", choices=("LST", "UTC"), default="LST")
    p.add_argument("--out", type=Path, default=Path("outputs/nile_delta_2025"))
    p.add_argument("--from-json", type=Path, metavar="PATH", help="Process existing POWER JSON without network")
    p.add_argument("--offline-fixture", action="store_true", help="Use synthetic 3-day fixture (requires matching dates)")
    p.add_argument("--refresh", action="store_true", help="Ignore cached NASA response and download again")
    p.add_argument("--strict", action="store_true", help="Exit nonzero if units/missing values/suspicious data are flagged")
    return p


def run(args) -> tuple[Path, dict, str]:
    request = PowerRequest(args.lat, args.lon, args.start, args.end, args.time_standard)
    if args.from_json and args.offline_fixture:
        raise ValueError("Choose either --from-json or --offline-fixture")
    if args.offline_fixture:
        path = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "synthetic_3days.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        source_mode = "fixture"
    elif args.from_json:
        payload = json.loads(args.from_json.read_text(encoding="utf-8"))
        source_mode = "imported"
    else:
        raw_path = args.out / "raw_nasa_response.json"
        meta_path = args.out / "metadata.json"
        use_cache = False
        if not args.refresh and raw_path.is_file() and meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                use_cache = (
                    meta.get("source_mode") == "live"
                    and meta["request"]["request_url"] == request.url()
                )
            except (OSError, ValueError, KeyError, TypeError):
                pass
        if use_cache:
            payload = json.loads(raw_path.read_text(encoding="utf-8"))
            source_mode = "live"
            print("Using cached NASA POWER raw response; use --refresh to re-download.")
        else:
            print("Requesting NASA POWER daily data (one API request)...")
            payload = fetch_daily(request)
            source_mode = "live"

    rows, report = parse_response(payload, request)
    report["data_provenance"] = {
        "live": "LIVE_NASA_API",
        "fixture": "SYNTHETIC_TEST_FIXTURE",
        "imported": "UNVERIFIED_IMPORTED_JSON",
    }[source_mode]
    if source_mode != "live":
        report["science_ready"] = False
        report["warnings"].append(
            "Unverified provenance: this dataset must not be presented as observed NASA climate data."
        )
    save_outputs(args.out, request, payload, rows, report, source_mode=source_mode)
    return args.out, report, source_mode


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        out, report, mode = run(args)
    except (ValueError, OSError, PowerAPIError, PowerDataError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Mode: {mode} | Days: {report['rows']} | {report['first_day']} .. {report['last_day']}")
    print("Missing values:", report["missing_values_by_parameter"])
    print("Output folder:", out.resolve())
    for name in ("daily_climate.csv", "daily_climate.json", "monthly_summary.csv",
                 "metadata.json", "quality_report.json", "raw_nasa_response.json"):
        print("  -", name)
    if report["warnings"]:
        print("QUALITY WARNINGS:")
        for warning in report["warnings"]:
            print(" -", warning)
    if mode == "fixture":
        print("WARNING: SYNTHETIC TEST DATA ONLY. NOT NASA OBSERVATIONS.")
    if mode == "imported":
        print("WARNING: Imported JSON origin is not independently verified.")
    if args.strict and not report["science_ready"]:
        print("Strict quality check failed; see quality_report.json", file=sys.stderr)
        return 2
    return 0
