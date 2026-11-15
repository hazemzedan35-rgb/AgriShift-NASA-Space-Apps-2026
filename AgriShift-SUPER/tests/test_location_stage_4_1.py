"""Stage 4.1: dynamic point-specific NASA climate, with test data never shown as NASA."""
import json
import tempfile
import unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from agrishift_decision.location_data import (normalize_coordinates,nasa_power_url,
    get_reference_data,ClimateDataError, _validated_rows)
from agrishift_decision.api import app


def synthetic_power_json():
    # For unit tests only; NO synthetic result is bundled as real NASA data.
    vals={key:{} for key in ('T2M','T2M_MAX','T2M_MIN','PRECTOTCORR','RH2M','WS2M','ALLSKY_SFC_SW_DWN','PS')}
    for i in range(365):
        d=(date(2025,1,1)+timedelta(days=i)).strftime('%Y%m%d')
        sample=(20.0,28.0,12.0,0.0,58.0,2.0,19.0,101.0)
        for key,number in zip(vals,sample):vals[key][d]=number
    from agrishift_decision.location_data import EXPECTED_UNITS
    return {'properties':{'parameter':vals},'parameters':{k:{'units':v} for k,v in EXPECTED_UNITS.items()},'header':{'title':'TEST ONLY'}}


class TestLocationSpecificData(unittest.TestCase):
    def test_coordinates(self):
        self.assertEqual(normalize_coordinates('30.50004',31.5),(30.5,31.5))
        for x,y in [(91,0),(0,181),('oops',2),(float('nan'),1),(float('inf'),0)]:
            with self.assertRaises(ValueError):normalize_coordinates(x,y)
    def test_url_parameters(self):
        url=nasa_power_url(29,30)
        self.assertTrue(url.startswith('https://power.larc.nasa.gov/api/temporal/daily/point?'))
        for token in ('latitude=29','longitude=30','start=20250101','end=20251231','community=AG','time-standard=LST'):
            self.assertIn(token,url)
    def test_pilot_uses_verified_local_data(self):
        _,meta,_,eto,climate=get_reference_data(30.5,31.5)
        self.assertEqual(meta['request']['longitude'],31.5)
        self.assertEqual(len(eto),365)
        self.assertEqual(len(climate),365)
    def test_live_fetch_cache_exact_point(self):
        with tempfile.TemporaryDirectory() as directory:
            calls=[]
            def fake_fetch(url):
                calls.append(url)
                return synthetic_power_json()
            a=get_reference_data(30.7,31.6,fetch_json=fake_fetch,cache_root=directory)
            b=get_reference_data(30.7,31.6,fetch_json=lambda _: self.fail('should use cache'),cache_root=directory)
            self.assertEqual(len(calls),1)
            self.assertEqual(a[1]['request']['latitude'],30.7)
            self.assertEqual(len(a[3]),365)
            self.assertAlmostEqual(a[2]['eto_total_mm'],b[2]['eto_total_mm'])
            self.assertEqual(len(list(Path(directory).glob('*.json'))),1)
            get_reference_data(30.8,31.6,fetch_json=fake_fetch,cache_root=directory)
            self.assertEqual(len(calls),2)
    def test_reject_missing_day_not_cached(self):
        with tempfile.TemporaryDirectory() as directory:
            payload=synthetic_power_json()
            del payload['properties']['parameter']['T2M']['20250401']
            with self.assertRaises(ClimateDataError):get_reference_data(29,31,fetch_json=lambda _:payload,cache_root=directory)
            self.assertEqual(list(Path(directory).glob('*.json')),[])
    def test_reject_unit_change(self):
        payload=synthetic_power_json()
        payload['parameters']['T2M']['units']='F'
        with self.assertRaises(ClimateDataError):_validated_rows(payload)
    def test_reject_fill_value(self):
        payload=synthetic_power_json()
        payload['properties']['parameter']['RH2M']['20250818']=-999
        with self.assertRaises(ClimateDataError):_validated_rows(payload)
    def test_api_pilot_works(self):
        c=TestClient(app)
        r=c.post('/api/analyze',json={'latitude':30.5,'longitude':31.5})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['climate']['latitude'],30.5)
        self.assertEqual(len(r.json()['climate']['monthly_eto']),12)
    def test_api_invalid_location(self):
        c=TestClient(app)
        self.assertEqual(c.post('/api/analyze',json={'latitude':91}).status_code,422)
    def test_api_when_nasa_unavailable(self):
        with patch('agrishift_decision.api.get_reference_data',side_effect=ClimateDataError('NASA unavailable')):
            c=TestClient(app)
            r=c.post('/api/analyze',json={'latitude':32.1,'longitude':40.0})
            self.assertEqual(r.status_code,503)
            self.assertIn('NASA unavailable',r.text)

if __name__=='__main__':unittest.main()
