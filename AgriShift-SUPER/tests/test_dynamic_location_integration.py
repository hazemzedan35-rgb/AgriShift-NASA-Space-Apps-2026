"""End-to-end FastAPI assertions for two separately mocked NASA points.

All values here are synthetic TEST FIXTURES, never a substitute for live NASA data.
"""
import copy
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch
from fastapi.testclient import TestClient
from agrishift_decision.api import app
from tests.test_location_stage_4_1 import synthetic_power_json

class TestDynamicLocationIntegration(unittest.TestCase):
    def test_two_locations_are_distinct_and_cached_by_coordinates(self):
        calls=[]
        def stub_nasa(url):
            args=parse_qs(urlsplit(url).query)
            lat=float(args['latitude'][0])
            calls.append(lat)
            data=copy.deepcopy(synthetic_power_json())
            if lat>=31:
                # Different weather profile; physically consistent temperatures.
                for day in data['properties']['parameter']['T2M']:
                    data['properties']['parameter']['T2M'][day]=30.0
                    data['properties']['parameter']['T2M_MIN'][day]=24.0
                    data['properties']['parameter']['T2M_MAX'][day]=38.0
            return data
        with tempfile.TemporaryDirectory() as cache:
            with patch('agrishift_decision.location_data.CACHE_ROOT',__import__('pathlib').Path(cache)), patch('agrishift_decision.location_data._fetch_json',side_effect=stub_nasa):
                c=TestClient(app)
                a=c.post('/api/analyze',json={'latitude':30.7,'longitude':31.6})
                b=c.post('/api/analyze',json={'latitude':31.2,'longitude':31.6})
                again=c.post('/api/analyze',json={'latitude':30.7,'longitude':31.6})
            self.assertEqual([a.status_code,b.status_code,again.status_code],[200]*3)
            self.assertEqual(calls,[30.7,31.2])
            j1,j2=a.json(),b.json()
            self.assertEqual(j1['climate']['latitude'],30.7)
            self.assertEqual(j2['climate']['latitude'],31.2)
            self.assertNotEqual(j1['climate']['average_air_temperature_c'],j2['climate']['average_air_temperature_c'])
            self.assertNotEqual(j1['climate']['annual_reference_et0_mm'],j2['climate']['annual_reference_et0_mm'])
            self.assertEqual(again.json()['climate'],j1['climate'])

if __name__=='__main__':unittest.main()
