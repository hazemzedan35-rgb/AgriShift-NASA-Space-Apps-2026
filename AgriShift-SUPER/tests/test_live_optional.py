"""Optional live verification, NOT run by default. Set AGRISHIFT_RUN_LIVE_TEST=1."""
import os
import unittest
from datetime import date
from agrishift_power.client import fetch_daily
from agrishift_power.config import PowerRequest
from agrishift_power.transform import parse_response


@unittest.skipUnless(os.getenv("AGRISHIFT_RUN_LIVE_TEST") == "1", "Internet-dependent: opt in explicitly")
class LiveNASAIntegrationTest(unittest.TestCase):
    def test_short_live_window(self):
        request = PowerRequest(start=date(2025, 1, 1), end=date(2025, 1, 3))
        rows, qa = parse_response(fetch_daily(request), request)
        self.assertEqual(len(rows), 3)
        self.assertGreater(sum(v is not None for r in rows for k, v in r.items() if k != "date"), 0)
        self.assertEqual(qa["rows"], 3)
