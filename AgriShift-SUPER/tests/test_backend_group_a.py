"""Backend bug-fix group A. Each test was written to FAIL on Stage A3 and pass after the fix."""
import json
import tempfile
import threading
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

from fastapi.testclient import TestClient

from agrishift_decision import location_data as ld
from agrishift_decision.api import app
from agrishift_decision.engine import analyze, validate_inputs, InputError


def synthetic_power_json(elevation=None):
    """Unit-test-only NASA-shaped response (never presented as real NASA data)."""
    names = ('T2M', 'T2M_MAX', 'T2M_MIN', 'PRECTOTCORR', 'RH2M', 'WS2M', 'ALLSKY_SFC_SW_DWN', 'PS')
    vals = {k: {} for k in names}
    for i in range(365):
        d = (date(2025, 1, 1) + timedelta(days=i)).strftime('%Y%m%d')
        for key, number in zip(names, (20.0, 28.0, 12.0, 0.0, 58.0, 2.0, 19.0, 101.0)):
            vals[key][d] = number
    out = {'properties': {'parameter': vals}, 'parameters': {k: {'units': v} for k, v in ld.EXPECTED_UNITS.items()},
           'header': {'title': 'TEST ONLY'}}
    if elevation is not None:
        out['geometry'] = {'type': 'Point', 'coordinates': [31.0, 30.0, elevation]}
    return out


class FakeResponse:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return json.dumps(self.payload).encode('utf-8')


# ---------------------------------------------------------------- 1. salinity: unknown is not safe
class TestSalinityUnknownIsNotSafe(unittest.TestCase):
    def test_known_safe_plan_outranks_plan_with_unknown_threshold(self):
        # ECe 1.0 is below every published threshold, but sunflower has no published threshold.
        r = analyze({'water_budget_m3': 1e9, 'soil_ece_ds_m': 1.0, 'first_winter_year': 2026})
        top = r['plans'][0]
        self.assertNotIn('sunflower', top['sequence'], top['id'])
        self.assertEqual(top['soil_screening']['salinity_unknown_count'], 0)

    def test_unknown_count_is_reported_for_every_season(self):
        r = analyze({'water_budget_m3': 1e9, 'soil_ece_ds_m': 1.0, 'planning_seasons': 4, 'allowed_crops': ['wheat', 'sunflower'],
                     'max_results': 64, 'first_winter_year': 2026})
        self.assertEqual(r['plans'][0]['sequence'], ['wheat', 'sunflower', 'wheat', 'sunflower'])
        self.assertEqual(r['plans'][0]['soil_screening']['salinity_unknown_count'], 2)

    def test_known_exceedance_still_counts_separately(self):
        r = analyze({'water_budget_m3': 1e9, 'soil_ece_ds_m': 4.0, 'first_winter_year': 2026})
        by_id = {p['id']: p['soil_screening'] for p in r['plans']}
        self.assertEqual((by_id['wheat-sunflower']['salinity_concern_count'], by_id['wheat-sunflower']['salinity_unknown_count']), (0, 1))
        self.assertEqual((by_id['faba-maize']['salinity_concern_count'], by_id['faba-maize']['salinity_unknown_count']), (2, 0))

    def test_without_ece_unknown_count_is_zero_and_ranking_unchanged(self):
        r = analyze({'water_budget_m3': 1e9, 'first_winter_year': 2026})
        self.assertTrue(all(p['soil_screening']['salinity_unknown_count'] == 0 for p in r['plans']))
        scores = [p['comparison_score'] for p in r['plans']]
        self.assertEqual(scores, sorted(scores, reverse=True))


# ---------------------------------------------------------------- 2. honest water differences
class TestHonestWaterDifferences(unittest.TestCase):
    def test_percent_difference_vs_lowest_plan(self):
        r = analyze({'water_budget_m3': 1e9, 'max_results': 64, 'first_winter_year': 2026})
        lows = min(p['water_proxy_m3'] for p in r['plans'])
        for p in r['plans']:
            self.assertAlmostEqual(p['water_vs_lowest_pct'], round(100 * (p['water_proxy_m3'] - lows) / lows, 1), places=1)
        self.assertEqual(min(p['water_vs_lowest_pct'] for p in r['plans']), 0.0)

    def test_single_candidate_is_not_reported_as_a_close_call(self):
        r = analyze({'allowed_crops': ['wheat', 'maize'], 'planning_seasons': 2, 'first_winter_year': 2026})
        self.assertEqual(r['rotation_generation']['valid_candidate_count'], 1)
        self.assertFalse(r['rotation_generation']['water_differences_are_small'])
        self.assertIsNone(r['rotation_generation']['ranking_note'])

    def test_spread_and_close_call_flag(self):
        r = analyze({'water_budget_m3': 1e9, 'first_winter_year': 2026})
        g = r['rotation_generation']
        waters = [p['water_proxy_m3'] for p in r['plans']]
        self.assertAlmostEqual(g['water_spread_pct'], round(100 * (max(waters) - min(waters)) / min(waters), 1), places=1)
        self.assertEqual(g['water_differences_are_small'], g['water_spread_pct'] < 10.0)
        self.assertIsNotNone(g['ranking_note'] if g['water_differences_are_small'] else 'x')


# ---------------------------------------------------------------- 3. NASA fetch, cache, concurrency
class TestNasaHandling(unittest.TestCase):
    def test_coordinates_use_about_one_km_precision(self):
        self.assertEqual(ld.normalize_coordinates(31.1049, 29.9951), (31.10, 30.0))
        self.assertEqual(ld.normalize_coordinates(30.5004, 31.5004), (30.5, 31.5))
        self.assertEqual(ld._cache_path(31.1049, 29.9951).name, ld._cache_path(31.1001, 30.0049).name)

    def test_nearby_requests_share_one_cache_file(self):
        calls = []
        def fake(url): calls.append(url); return synthetic_power_json()
        with tempfile.TemporaryDirectory() as tmp:
            ld.get_reference_data(31.1049, 29.9951, fetch_json=fake, cache_root=tmp)
            ld.get_reference_data(31.1001, 30.0049, fetch_json=fake, cache_root=tmp)
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(list(Path(tmp).glob('*.json'))), 1)

    def test_retries_temporary_errors_with_backoff_then_succeeds(self):
        attempts, sleeps = [], []
        def flaky(url, timeout=None):
            attempts.append(1)
            if len(attempts) == 1: raise HTTPError(url, 429, 'Too Many Requests', {}, None)
            if len(attempts) == 2: raise URLError('temporary')
            return FakeResponse({'ok': True})
        with patch.object(ld, 'urlopen', flaky), patch.object(ld.time, 'sleep', lambda s: sleeps.append(s)):
            self.assertEqual(ld._fetch_json('https://example.invalid'), {'ok': True})
        self.assertEqual(len(attempts), 3)
        self.assertEqual(len(sleeps), 2)
        self.assertLess(sleeps[0], sleeps[1])

    def test_gives_up_after_limited_attempts_without_fake_data(self):
        attempts = []
        def down(url, timeout=None):
            attempts.append(1); raise URLError('down')
        with patch.object(ld, 'urlopen', down), patch.object(ld.time, 'sleep', lambda s: None):
            with self.assertRaises(ld.ClimateDataError): ld._fetch_json('https://example.invalid')
        self.assertEqual(len(attempts), ld.FETCH_ATTEMPTS)

    def test_client_errors_are_not_retried(self):
        attempts = []
        def bad_request(url, timeout=None):
            attempts.append(1); raise HTTPError(url, 400, 'Bad Request', {}, None)
        with patch.object(ld, 'urlopen', bad_request), patch.object(ld.time, 'sleep', lambda s: None):
            with self.assertRaises(ld.ClimateDataError): ld._fetch_json('https://example.invalid')
        self.assertEqual(len(attempts), 1)

    def test_undecodable_response_is_a_clean_error(self):
        class Bad(FakeResponse):
            def read(self): return b'\xff\xfe\x00bad'
        with patch.object(ld, 'urlopen', lambda url, timeout=None: Bad({})), patch.object(ld.time, 'sleep', lambda s: None):
            with self.assertRaises(ld.ClimateDataError): ld._fetch_json('https://example.invalid')

    def test_concurrent_identical_requests_fetch_once_and_never_corrupt_cache(self):
        calls, results, errors = [], [], []
        gate = threading.Barrier(8)
        def slow(url):
            calls.append(1)
            threading.Event().wait(0.05)
            return synthetic_power_json()
        with tempfile.TemporaryDirectory() as tmp:
            def worker():
                try:
                    gate.wait()
                    results.append(ld.get_reference_data(31.2, 30.1, fetch_json=slow, cache_root=tmp))
                except Exception as ex:  # noqa: BLE001 - the test reports any failure
                    errors.append(repr(ex))
            threads = [threading.Thread(target=worker) for _ in range(8)]
            [t.start() for t in threads]; [t.join() for t in threads]
            self.assertEqual(errors, [])
            self.assertEqual(len(results), 8)
            self.assertEqual(len(calls), 1)
            files = list(Path(tmp).iterdir())
            self.assertEqual([f.suffix for f in files], ['.json'])
            json.loads(files[0].read_text(encoding='utf-8'))

    def test_corrupt_cache_file_is_refetched_not_a_server_error(self):
        calls = []
        def fake(url): calls.append(1); return synthetic_power_json()
        with tempfile.TemporaryDirectory() as tmp:
            ld.get_reference_data(31.3, 30.2, fetch_json=fake, cache_root=tmp)
            cache = next(Path(tmp).glob('*.json'))
            for broken in ('{"truncated":', '[]', '{"meta":{}}'):
                with self.subTest(broken=broken):
                    cache.write_text(broken, encoding='utf-8')
                    ld.get_reference_data(31.3, 30.2, fetch_json=fake, cache_root=tmp)
                    self.assertGreater(json.loads(cache.read_text(encoding='utf-8'))['summary']['days'], 0)
            self.assertEqual(len(calls), 4)

    def test_cache_folder_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(ld, 'MAX_CACHE_FILES', 3):
            for i in range(6):
                ld.get_reference_data(10 + i, 20, fetch_json=lambda u: synthetic_power_json(), cache_root=tmp)
            self.assertLessEqual(len(list(Path(tmp).glob('*.json'))), 3)
            self.assertTrue((Path(tmp) / ld._cache_path(15, 20).name).exists(), 'newest entry must survive pruning')


# ---------------------------------------------------------------- 4. elevation from NASA
class TestElevation(unittest.TestCase):
    def test_uses_elevation_returned_by_nasa(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, meta, summary, eto, _ = ld.get_reference_data(31.4, 30.3, fetch_json=lambda u: synthetic_power_json(450.0), cache_root=tmp)
        self.assertEqual(summary['elevation_m'], 450.0)
        self.assertEqual(summary['elevation_source'], 'nasa_power_response')

    def test_elevation_changes_clear_sky_radiation_and_et0(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            low = ld.get_reference_data(31.5, 30.5, fetch_json=lambda u: synthetic_power_json(0.0), cache_root=a)[2]['eto_total_mm']
            high = ld.get_reference_data(31.5, 30.5, fetch_json=lambda u: synthetic_power_json(2500.0), cache_root=b)[2]['eto_total_mm']
        self.assertNotEqual(low, high)

    def test_missing_or_absurd_elevation_falls_back_to_labelled_assumption(self):
        for payload in (synthetic_power_json(), synthetic_power_json(99999.0), synthetic_power_json(float('nan'))):
            with self.subTest(), tempfile.TemporaryDirectory() as tmp:
                summary = ld.get_reference_data(31.6, 30.6, fetch_json=lambda u, p=payload: p, cache_root=tmp)[2]
                self.assertEqual(summary['elevation_m'], 0.0)
                self.assertEqual(summary['elevation_source'], 'assumed_zero')

    def test_climate_output_reports_elevation_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            ref = ld.get_reference_data(31.7, 30.7, fetch_json=lambda u: synthetic_power_json(120.0), cache_root=tmp)
        out = analyze({'latitude': 30.7, 'longitude': 31.7, 'first_winter_year': 2026}, reference_data=ref)
        self.assertEqual(out['climate']['elevation_m'], 120.0)
        self.assertEqual(out['climate']['elevation_source'], 'nasa_power_response')


# ---------------------------------------------------------------- 5. dates are settings, not magic numbers
class TestDatesAndReferenceYear(unittest.TestCase):
    def test_default_first_winter_year_never_points_to_a_season_already_started(self):
        from agrishift_decision.config import default_first_winter_year as f
        self.assertEqual(f(date(2026, 5, 1)), 2026)
        self.assertEqual(f(date(2026, 11, 10)), 2026)   # sowing day itself is still plannable
        self.assertEqual(f(date(2026, 11, 14)), 2027)
        self.assertEqual(f(date(2027, 1, 1)), 2027)

    def test_request_can_choose_first_winter_year(self):
        r = analyze({'first_winter_year': 2030, 'planning_seasons': 4})
        dates = [c['planting_date'] for c in r['plans'][0]['crops']]
        self.assertEqual([d[:4] for d in dates], ['2030', '2031', '2031', '2032'])
        self.assertEqual(r['inputs']['first_winter_year'], 2030)
        self.assertIn('2030', r['method']['crop_windows']['winter'])

    def test_default_start_year_comes_from_config(self):
        from agrishift_decision.config import default_first_winter_year
        r = analyze({})
        self.assertEqual(r['inputs']['first_winter_year'], default_first_winter_year())

    def test_leap_year_window_still_works(self):
        r = analyze({'first_winter_year': 2027, 'planning_seasons': 4})   # window crosses 29 Feb 2028
        self.assertEqual(len(r['plans'][0]['crops']), 4)

    def test_invalid_first_winter_year_rejected(self):
        for bad in (1999, 2101, 2026.5, True, 'next', [2026]):
            with self.subTest(bad=bad), self.assertRaises(InputError):
                validate_inputs({'first_winter_year': bad})

    def test_reference_year_defined_once(self):
        from agrishift_decision.config import REFERENCE_YEAR
        self.assertEqual(REFERENCE_YEAR, 2025)
        self.assertEqual(analyze({'first_winter_year': 2026})['climate']['year'], REFERENCE_YEAR)
        self.assertEqual(TestClient(app).get('/api/monthly').json()['year'], REFERENCE_YEAR)

    def test_api_accepts_first_winter_year(self):
        client = TestClient(app)
        ok = client.post('/api/analyze', json={'first_winter_year': 2029})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()['plans'][0]['crops'][0]['planting_date'][:4], '2029')
        self.assertEqual(client.post('/api/analyze', json={'first_winter_year': 1900}).status_code, 422)


# ---------------------------------------------------------------- 6. soil screening for EVERY season
class TestSoilScreeningEverySeason(unittest.TestCase):
    def test_by_season_lists_all_planned_seasons(self):
        for seasons in (2, 4, 6):
            with self.subTest(seasons=seasons):
                r = analyze({'planning_seasons': seasons, 'soil_type': 'loam', 'soil_ece_ds_m': 2.0, 'first_winter_year': 2026})
                for p in r['plans']:
                    rows = p['soil_screening']['by_season']
                    self.assertEqual(len(rows), seasons)
                    self.assertEqual([x['crop_id'] for x in rows], p['sequence'])
                    self.assertEqual([x['season'] for x in rows], [c['season'] for c in p['crops']])
                    self.assertTrue(all('salinity_flag' in x and 'readily_available_water_raw_mm' in x for x in rows))

    def test_legacy_winter_summer_keys_still_present(self):
        p = analyze({'first_winter_year': 2026})['plans'][0]
        self.assertIn('winter', p['soil_screening'])
        self.assertIn('summer', p['soil_screening'])


# ---------------------------------------------------------------- 7. packaging + input details
class TestPackagingAndInputs(unittest.TestCase):
    def test_dev_requirements_include_test_client_dependency(self):
        text = (Path(__file__).resolve().parents[1] / 'requirements-dev.txt').read_text(encoding='utf-8')
        self.assertIn('-r requirements.txt', text)
        self.assertIn('httpx', text)

    def test_booleans_are_not_accepted_as_numbers(self):
        for payload in ({'area_ha': True}, {'water_budget_m3': False}, {'irrigation_efficiency': True}, {'soil_awc_mm_per_m': True}, {'soil_ece_ds_m': True}):
            with self.subTest(payload=payload), self.assertRaises(InputError):
                validate_inputs(payload)


if __name__ == '__main__':
    unittest.main()
