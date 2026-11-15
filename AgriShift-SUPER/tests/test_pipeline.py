"""Deterministic offline tests. Run with: python -m unittest discover -s tests -v"""
import copy
import csv
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError

from agrishift_power.client import PowerAPIError, fetch_daily
from agrishift_power.config import PARAMETERS, PowerRequest
from agrishift_power.cli import main
from agrishift_power.output import month_summary, save_outputs
from agrishift_power.transform import PowerDataError, parse_response

ROOT = Path(__file__).resolve().parent
FIXTURE = json.loads((ROOT / "fixtures/synthetic_3days.json").read_text(encoding="utf-8"))
REQUEST = PowerRequest(start=date(2025, 1, 1), end=date(2025, 1, 3))


class RequestTests(unittest.TestCase):
    def test_url_has_required_fields(self):
        url = PowerRequest().url()
        for field in ("community=AG", "latitude=30.5", "longitude=31.5",
                      "start=20250101", "end=20251231", "time-standard=LST"):
            self.assertIn(field, url)
        for p in PARAMETERS:
            self.assertIn(p, url)

    def test_invalid_latitude_rejected(self):
        with self.assertRaises(ValueError):
            PowerRequest(latitude=100)

    def test_invalid_longitude_rejected(self):
        with self.assertRaises(ValueError):
            PowerRequest(longitude=float("nan"))

    def test_invalid_date_range_rejected(self):
        with self.assertRaises(ValueError):
            PowerRequest(start=date(2025, 2, 1), end=date(2025, 1, 1))

    def test_invalid_time_standard_rejected(self):
        with self.assertRaises(ValueError):
            PowerRequest(time_standard="CST")

    def test_2025_is_exactly_365_days(self):
        req = PowerRequest()
        self.assertEqual((req.end - req.start).days + 1, 365)

    def test_2024_is_leap_year(self):
        req = PowerRequest(start=date(2024, 1, 1), end=date(2024, 12, 31))
        self.assertEqual((req.end - req.start).days + 1, 366)


class TransformationTests(unittest.TestCase):
    def test_fixture_parses_three_days(self):
        rows, report = parse_response(FIXTURE, REQUEST)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["date"], "2025-01-01")
        self.assertEqual(rows[-1]["date"], "2025-01-03")
        self.assertEqual(rows[0]["PRECTOTCORR"], 0.0)
        self.assertTrue(report["science_ready"])

    def test_fill_value_is_null_not_zero(self):
        payload = copy.deepcopy(FIXTURE)
        payload["properties"]["parameter"]["T2M"]["20250102"] = -999
        rows, report = parse_response(payload, REQUEST)
        self.assertIsNone(rows[1]["T2M"])
        self.assertEqual(report["missing_values_by_parameter"]["T2M"], 1)

    def test_missing_date_key_is_flagged(self):
        payload = copy.deepcopy(FIXTURE)
        del payload["properties"]["parameter"]["T2M"]["20250103"]
        rows, report = parse_response(payload, REQUEST)
        self.assertEqual(len(rows), 3)
        self.assertEqual(report["missing_date_keys_by_parameter"]["T2M"], 1)
        self.assertIsNone(rows[2]["T2M"])

    def test_missing_parameter_is_hard_error(self):
        payload = copy.deepcopy(FIXTURE)
        del payload["properties"]["parameter"]["WS2M"]
        with self.assertRaises(PowerDataError):
            parse_response(payload, REQUEST)

    def test_incorrect_year_is_rejected(self):
        with self.assertRaises(PowerDataError):
            parse_response(FIXTURE, PowerRequest())

    def test_wrong_time_standard_is_rejected(self):
        with self.assertRaises(PowerDataError):
            parse_response(FIXTURE, PowerRequest(start=REQUEST.start, end=REQUEST.end, time_standard="UTC"))

    def test_invalid_units_flagged(self):
        payload = copy.deepcopy(FIXTURE)
        payload["parameters"]["PS"]["units"] = "Pa"
        _, report = parse_response(payload, REQUEST)
        self.assertFalse(report["science_ready"])
        self.assertTrue(any("PS:" in x for x in report["warnings"]))

    def test_physical_impossibility_flagged(self):
        payload = copy.deepcopy(FIXTURE)
        payload["properties"]["parameter"]["RH2M"]["20250101"] = 150
        _, report = parse_response(payload, REQUEST)
        self.assertEqual(report["suspicious_values"][0]["issue"], "RH2M outside 0..100%")

    def test_bad_payload_rejected(self):
        with self.assertRaises(PowerDataError):
            parse_response({"not": "NASA"}, REQUEST)

    def test_every_day_present_with_partial_missing(self):
        payload = copy.deepcopy(FIXTURE)
        for name in PARAMETERS:
            payload["properties"]["parameter"][name]["20250102"] = -999.0
        rows, _ = parse_response(payload, REQUEST)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1]["date"], "2025-01-02")

    def test_all_null_data_rejected(self):
        payload = copy.deepcopy(FIXTURE)
        for name in PARAMETERS:
            for day in payload["properties"]["parameter"][name]:
                payload["properties"]["parameter"][name][day] = -999.0
        with self.assertRaises(PowerDataError):
            parse_response(payload, REQUEST)


class OutputTests(unittest.TestCase):
    def test_monthly_sum_correct(self):
        rows, _ = parse_response(FIXTURE, REQUEST)
        months = month_summary(rows)
        self.assertEqual(len(months), 1)
        self.assertEqual(months[0]["precipitation_total_mm"], 1.2)
        self.assertEqual(months[0]["days_in_selection"], 3)

    def test_monthly_rain_incomplete_yields_null(self):
        rows, _ = parse_response(FIXTURE, REQUEST)
        rows[0]["PRECTOTCORR"] = None
        self.assertIsNone(month_summary(rows)[0]["precipitation_total_mm"])

    def test_files_written_and_reloaded(self):
        rows, report = parse_response(FIXTURE, REQUEST)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            meta = save_outputs(out, REQUEST, FIXTURE, rows, report, source_mode="fixture")
            self.assertEqual(meta["data_status"], "SYNTHETIC_FIXTURE_NOT_NASA_OBSERVATIONS")
            self.assertEqual(len(json.loads((out / "daily_climate.json").read_text())), 3)
            with (out / "daily_climate.csv").open(newline="") as f:
                data = list(csv.DictReader(f))
            self.assertEqual(len(data), 3)
            self.assertEqual(data[0]["T2M"], "15.3")
            self.assertTrue((out / "quality_report.json").exists())

    def test_full_year_365_rows_synthetic_generated_in_test(self):
        payload = copy.deepcopy(FIXTURE)
        payload["header"]["end"] = "20251231"
        start = date(2025, 1, 1)
        for p in PARAMETERS:
            first = payload["properties"]["parameter"][p]["20250101"]
            payload["properties"]["parameter"][p] = {
                (start + timedelta(days=i)).strftime("%Y%m%d"): first
                for i in range(365)
            }
        rows, report = parse_response(payload, PowerRequest())
        self.assertEqual(len(rows), 365)
        self.assertTrue(report["science_ready"])
        self.assertEqual(rows[-1]["date"], "2025-12-31")

    def test_cli_fixture_run_creates_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = main(["--offline-fixture", "--start", "2025-01-01", "--end", "2025-01-03",
                         "--out", tmp])
            self.assertEqual(code, 0)
            self.assertTrue((Path(tmp) / "daily_climate.csv").exists())
            status = json.loads((Path(tmp) / "quality_report.json").read_text())
            self.assertFalse(status["science_ready"])
            self.assertEqual(status["data_provenance"], "SYNTHETIC_TEST_FIXTURE")

    def test_cli_strict_fixture_rejected_for_scientific_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = main(["--offline-fixture", "--start", "2025-01-01", "--end", "2025-01-03",
                         "--out", tmp, "--strict"])
            self.assertEqual(code, 2)

    def test_cli_fixture_wrong_date_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = main(["--offline-fixture", "--out", tmp])
            self.assertEqual(code, 1)


class ClientTests(unittest.TestCase):
    class _FakeResponse:
        def __init__(self, data): self.data = data
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return json.dumps(self.data).encode("utf-8")

    def test_network_client_parses_response(self):
        def opener(req, timeout):
            self.assertIn("community=AG", req.full_url)
            self.assertGreater(timeout, 0)
            return self._FakeResponse(FIXTURE)
        self.assertEqual(fetch_daily(REQUEST, opener=opener, pause=lambda n: None), FIXTURE)

    def test_network_retry_then_success(self):
        count = [0]
        def opener(req, timeout):
            count[0] += 1
            if count[0] == 1:
                raise URLError("transient")
            return self._FakeResponse(FIXTURE)
        fetch_daily(REQUEST, opener=opener, pause=lambda n: None)
        self.assertEqual(count[0], 2)

    def test_nonretryable_http_400(self):
        def opener(req, timeout):
            raise HTTPError(req.full_url, 400, "Bad Request", {}, None)
        with self.assertRaises(PowerAPIError):
            fetch_daily(REQUEST, opener=opener, pause=lambda n: None)

    def test_invalid_json_rejected(self):
        class BadResponse(self._FakeResponse):
            def read(self): return b"not-json"
        with self.assertRaises(PowerAPIError):
            fetch_daily(REQUEST, opener=lambda req, timeout: BadResponse(None), pause=lambda n: None)


if __name__ == "__main__":
    unittest.main()
