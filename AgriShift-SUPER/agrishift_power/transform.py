"""Convert POWER JSON to exactly one record per requested calendar day."""
from __future__ import annotations

from datetime import timedelta
from math import isfinite

from .config import PARAMETERS, EXPECTED_UNITS, PowerRequest


class PowerDataError(ValueError):
    """POWER JSON failed structural or scientific checks."""


def _is_missing(raw, fill_value) -> bool:
    if raw is None:
        return True
    if isinstance(raw, bool):
        raise PowerDataError("Boolean appeared in a numerical NASA field")
    try:
        number = float(raw)
    except (TypeError, ValueError) as exc:
        raise PowerDataError(f"Non-numeric NASA observation: {raw!r}") from exc
    return not isfinite(number) or number in (-999.0, float(fill_value))


def parse_response(payload: dict, request: PowerRequest) -> tuple[list[dict], dict]:
    """Return normalized rows and QA report. Null means unknown, never zero."""
    if not isinstance(payload, dict):
        raise PowerDataError("Expected JSON object")
    try:
        series = payload["properties"]["parameter"]
        header = payload["header"]
        parameter_meta = payload["parameters"]
    except (KeyError, TypeError) as exc:
        raise PowerDataError("Missing NASA properties.parameter, header or parameters") from exc
    if not all(isinstance(obj, dict) for obj in (series, header, parameter_meta)):
        raise PowerDataError("NASA response has unexpected structure")

    missing_parameters = [p for p in PARAMETERS if p not in series or not isinstance(series[p], dict)]
    if missing_parameters:
        raise PowerDataError("Requested parameter series missing: " + ", ".join(missing_parameters))

    # Do not accept wrong-date caches as real data, even if date-grid output
    # could still have 365 rows of null values.
    expected_start = request.start.strftime("%Y%m%d")
    expected_end = request.end.strftime("%Y%m%d")
    if header.get("start") is not None and str(header["start"]) != expected_start:
        raise PowerDataError(f"NASA response start={header['start']} != {expected_start}")
    if header.get("end") is not None and str(header["end"]) != expected_end:
        raise PowerDataError(f"NASA response end={header['end']} != {expected_end}")
    reported_ts = header.get("time_standard")
    if reported_ts and str(reported_ts).upper() != request.time_standard:
        raise PowerDataError(f"NASA time_standard={reported_ts} != {request.time_standard}")

    try:
        fill = float(header.get("fill_value", -999.0))
    except (ValueError, TypeError) as exc:
        raise PowerDataError("Invalid NASA fill_value") from exc

    units = {}
    unit_warnings = []
    for p in PARAMETERS:
        metadata = parameter_meta.get(p, {})
        unit = metadata.get("units") if isinstance(metadata, dict) else None
        units[p] = unit
        norm = lambda s: str(s).replace(" ", "").lower() if s is not None else ""
        if not unit or norm(unit) != norm(EXPECTED_UNITS[p]):
            unit_warnings.append(f"{p}: NASA unit {unit!r}; expected {EXPECTED_UNITS[p]!r}. Verify before FAO calculations.")

    date_cursor = request.start
    rows: list[dict] = []
    missing_by_parameter = {p: 0 for p in PARAMETERS}
    missing_dates_by_parameter = {p: 0 for p in PARAMETERS}
    suspicious_values: list[dict] = []
    while date_cursor <= request.end:
        key = date_cursor.strftime("%Y%m%d")
        row = {"date": date_cursor.isoformat()}
        for p in PARAMETERS:
            if key not in series[p]:
                missing_dates_by_parameter[p] += 1
            raw = series[p].get(key)
            if _is_missing(raw, fill):
                row[p] = None
                missing_by_parameter[p] += 1
            else:
                row[p] = float(raw)
        if (row["T2M_MIN"] is not None and row["T2M_MAX"] is not None
                and row["T2M_MIN"] > row["T2M_MAX"]):
            suspicious_values.append({"date": row["date"], "issue": "T2M_MIN > T2M_MAX"})
        for p in ("PRECTOTCORR", "WS2M", "ALLSKY_SFC_SW_DWN", "PS"):
            if row[p] is not None and (row[p] < 0 or (p == "PS" and row[p] == 0)):
                suspicious_values.append({"date": row["date"], "issue": f"Invalid negative/zero {p}"})
        if row["RH2M"] is not None and not 0 <= row["RH2M"] <= 100:
            suspicious_values.append({"date": row["date"], "issue": "RH2M outside 0..100%"})
        rows.append(row)
        date_cursor += timedelta(days=1)

    if sum(missing_by_parameter.values()) == len(rows) * len(PARAMETERS):
        raise PowerDataError("No usable observations for the requested period")

    warnings = list(unit_warnings)
    for p, count in missing_by_parameter.items():
        if count:
            warnings.append(f"{p}: {count} missing observations")
    if suspicious_values:
        warnings.append(f"{len(suspicious_values)} physically suspicious values (see suspicious_values)")
    if missing_by_parameter["T2M"] == len(rows):
        warnings.append("T2M is entirely missing")

    report = {
        "expected_days": (request.end - request.start).days + 1,
        "rows": len(rows),
        "first_day": rows[0]["date"],
        "last_day": rows[-1]["date"],
        "date_grid_complete": len(rows) == (request.end - request.start).days + 1,
        "missing_values_by_parameter": missing_by_parameter,
        "missing_date_keys_by_parameter": missing_dates_by_parameter,
        "observed_units": units,
        "expected_units": EXPECTED_UNITS,
        "suspicious_values": suspicious_values,
        "warnings": warnings,
        "all_parameters_fully_available": not any(missing_by_parameter.values()),
        "science_ready": not warnings,
    }
    return rows, report
