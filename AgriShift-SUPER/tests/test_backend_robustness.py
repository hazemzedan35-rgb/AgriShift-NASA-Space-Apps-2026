"""Backend robustness found by fuzzing Stage A3. Written to FAIL before the fixes."""
import json
import math
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from agrishift_decision import location_data as ld
from agrishift_decision.api import app
from agrishift_decision.engine import validate_inputs, InputError
from test_backend_group_a import synthetic_power_json

CLIENT = TestClient(app, raise_server_exceptions=False)


def power_with(**override):
    payload = synthetic_power_json(100.0)
    for name, value in override.items():
        for day in payload['properties']['parameter'][name]:
            payload['properties']['parameter'][name][day] = value
    return payload


class TestNeverServerErrorOnBadJson(unittest.TestCase):
    def test_non_finite_numbers_are_a_clean_422(self):
        for body in (b'{"latitude": NaN}', b'{"latitude": Infinity}', b'{"area_ha": -Infinity}', b'{"water_budget_m3": 1e400}',
                     b'{"soil_ece_ds_m": NaN}', b'{"irrigation_efficiency": NaN}'):
            with self.subTest(body=body):
                r = CLIENT.post('/api/analyze', content=body, headers={'content-type': 'application/json'})
                self.assertEqual(r.status_code, 422)
                detail = r.json()['detail']
                self.assertTrue(isinstance(detail, list) and all('loc' in d and 'msg' in d for d in detail))

    def test_other_malformed_bodies_never_500(self):
        for body in (b'', b'null', b'[]', b'{', b'"x"', b'{"allowed_crops": "wheat"}', b'{"latitude": "abc"}'):
            with self.subTest(body=body):
                r = CLIENT.post('/api/analyze', content=body, headers={'content-type': 'application/json'})
                self.assertIn(r.status_code, (422,))


class TestUnsupportedLatitude(unittest.TestCase):
    def test_validate_inputs_limits(self):
        for ok in (66.5, -66.5, 0, 30.5):
            validate_inputs({'latitude': ok})
        for bad in (66.6, -66.6, 80, -90, 90):
            with self.subTest(lat=bad), self.assertRaises(InputError) as ctx:
                validate_inputs({'latitude': bad})
            self.assertIn('66.5', str(ctx.exception))

    def test_polar_request_is_422_and_never_calls_nasa(self):
        with patch.object(ld, '_fetch_json', side_effect=AssertionError('NASA must not be called')):
            r = CLIENT.post('/api/analyze', json={'latitude': 80, 'longitude': 20})
        self.assertEqual(r.status_code, 422)
        self.assertIn('66.5', r.json()['detail'])

    def test_direct_call_also_refuses_polar_points_without_network(self):
        with patch.object(ld, '_fetch_json', side_effect=AssertionError('NASA must not be called')):
            with self.assertRaises(ld.ClimateDataError):
                ld.get_reference_data(80, 20, cache_root=tempfile.gettempdir())


class TestInvalidRequestsDoNotTouchNasa(unittest.TestCase):
    def test_bad_crop_pool_for_new_location_makes_no_nasa_call_and_no_cache_file(self):
        bodies = [
            {'latitude': 31.9, 'longitude': 30.9, 'allowed_crops': ['wheat']},                      # no summer crop
            {'latitude': 31.9, 'longitude': 30.9, 'allowed_crops': ['maize', 'sunflower']},         # no winter crop
            {'latitude': 31.9, 'longitude': 30.9, 'allowed_crops': ['wheat', 'maize'],
             'previous_crop': 'wheat', 'strict_family_rotation': True},                              # every sequence repeats a family
        ]
        with tempfile.TemporaryDirectory() as tmp, patch.object(ld, 'CACHE_ROOT', Path(tmp)), \
                patch.object(ld, '_fetch_json', side_effect=AssertionError('NASA must not be called')):
            for body in bodies:
                with self.subTest(body=body):
                    self.assertEqual(CLIENT.post('/api/analyze', json=body).status_code, 422)
            self.assertEqual(list(Path(tmp).iterdir()), [])


class TestNasaPlausibility(unittest.TestCase):
    def test_physically_impossible_values_are_rejected_and_not_cached(self):
        impossible = {'solar radiation 60': dict(ALLSKY_SFC_SW_DWN=60.0), 'wind 60 m/s': dict(WS2M=60.0),
                      'Tmax 70 C': dict(T2M_MAX=70.0, T2M=40.0), 'Tmin -100 C': dict(T2M_MIN=-100.0, T2M=-20.0),
                      'rain 3000 mm/day': dict(PRECTOTCORR=3000.0)}
        for name, override in impossible.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ld.ClimateDataError):
                    ld.get_reference_data(31.0, 20.0, fetch_json=lambda u, o=override: power_with(**o), cache_root=tmp)
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_hard_but_real_weather_is_still_accepted(self):
        real = {'very hot': dict(T2M=44.0, T2M_MAX=50.0, T2M_MIN=38.0), 'bright sun 33': dict(ALLSKY_SFC_SW_DWN=33.0),
                'storm wind 25': dict(WS2M=25.0), 'cloudburst 400': dict(PRECTOTCORR=400.0), 'freezing': dict(T2M=-30.0, T2M_MAX=-25.0, T2M_MIN=-35.0)}
        for name, override in real.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                summary = ld.get_reference_data(31.0, 20.0, fetch_json=lambda u, o=override: power_with(**o), cache_root=tmp)[2]
                self.assertGreater(summary['eto_total_mm'], 0)


class TestNegativeZero(unittest.TestCase):
    def test_tiny_negative_coordinates_do_not_create_a_second_cache_key(self):
        a = ld.normalize_coordinates(-0.001, -0.004)
        b = ld.normalize_coordinates(0.001, 0.004)
        self.assertEqual(a, (0.0, 0.0))
        self.assertTrue(all(math.copysign(1, x) == 1 for x in a))
        self.assertEqual(ld._cache_path(*a).name, ld._cache_path(*b).name)


if __name__ == '__main__':
    unittest.main()
