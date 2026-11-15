"""Independent soil-water and ECe screening tests (Stage A2)."""
import math
import unittest
from fastapi.testclient import TestClient
from agrishift_decision.api import app
from agrishift_decision.engine import analyze, validate_inputs, InputError
from agrishift_decision.soil import awc_for_farm,soil_crop_screen,TEXTURE_AWC

class TestSoilModule(unittest.TestCase):
    def test_fao_texture_midpoints(self):
        self.assertEqual(awc_for_farm('sand')['value_mm_per_m'],80)
        self.assertEqual(awc_for_farm('loam')['value_mm_per_m'],155)
        self.assertEqual(awc_for_farm('clay')['value_mm_per_m'],160)
    def test_unknown_has_no_fake_storage(self):
        self.assertIsNone(awc_for_farm('unknown')['value_mm_per_m'])
        self.assertIsNone(soil_crop_screen('wheat',awc_for_farm('unknown'),None,4)['readily_available_water_raw_mm'])
    def test_measured_awc_override(self):
        a=awc_for_farm('sand',180)
        self.assertEqual(a['value_mm_per_m'],180)
        self.assertEqual(a['source_kind'],'farmer_supplied_awc')
    def test_fao_equations(self):
        # FAO-56 Table22 maize root depth 1.0m lower bound, p=0.55
        r=soil_crop_screen('maize',awc_for_farm('loam'),None,5)
        self.assertEqual(r['total_available_water_taw_mm'],155)
        self.assertEqual(r['readily_available_water_raw_mm'],85.25)
        self.assertEqual(r['notional_buffer_days'],17.05)
    def test_texture_changes_buffer(self):
        low=soil_crop_screen('faba',awc_for_farm('sand'),None,5)
        high=soil_crop_screen('faba',awc_for_farm('clay'),None,5)
        self.assertLess(low['readily_available_water_raw_mm'],high['readily_available_water_raw_mm'])
    def test_salt_thresholds(self):
        self.assertEqual(soil_crop_screen('maize',awc_for_farm('sand'),1.8,4)['salinity_flag'],'above_published_threshold')
        self.assertEqual(soil_crop_screen('wheat',awc_for_farm('sand'),1.8,4)['salinity_flag'],'at_or_below_published_threshold')
        self.assertEqual(soil_crop_screen('sunflower',awc_for_farm('sand'),1.8,4)['salinity_flag'],'no_numeric_threshold_in_fao56_table23')
    def test_equal_threshold_not_exceedance(self):
        self.assertEqual(soil_crop_screen('faba',awc_for_farm('loam'),1.6,3)['salinity_flag'],'at_or_below_published_threshold')

class TestSoilIntegration(unittest.TestCase):
    def test_texture_updates_screen_not_crop_et(self):
        a=analyze({'soil_type':'sand'});b=analyze({'soil_type':'clay'})
        self.assertNotEqual(a['soil_summary']['crop_screening']['wheat']['readily_available_water_raw_mm'],b['soil_summary']['crop_screening']['wheat']['readily_available_water_raw_mm'])
        self.assertEqual(sorted(p['water_proxy_m3'] for p in a['plans']),sorted(p['water_proxy_m3'] for p in b['plans']))
    def test_override_changes_storage_with_unknown_texture(self):
        r=analyze({'soil_type':'unknown','soil_awc_mm_per_m':100})
        self.assertEqual(r['soil_summary']['awc']['value_mm_per_m'],100)
        self.assertEqual(r['soil_summary']['crop_screening']['maize']['total_available_water_taw_mm'],100)
    def test_ece_changes_salinity_screening_and_order(self):
        a=analyze({'water_budget_m3':1e9, 'soil_ece_ds_m':4})
        # Less exceedance with wheat-sunflower (0) than faba-maize (2)
        counts={p['id']:p['soil_screening']['salinity_concern_count'] for p in a['plans']}
        self.assertEqual(counts['wheat-sunflower'],0)
        self.assertEqual(counts['faba-maize'],2)
        self.assertEqual(a['plans'][0]['id'],'wheat-sunflower')
    def test_unknown_ece_is_not_safe(self):
        r=analyze({'soil_type':'unknown'})
        self.assertTrue(all(c['salinity_flag']=='not_tested' for c in r['soil_summary']['crop_screening'].values()))
    def test_reject_invalid_soil_values(self):
        for payload in ({'soil_awc_mm_per_m':-1},{'soil_awc_mm_per_m':500},{'soil_ece_ds_m':-0.1},{'soil_ece_ds_m':200},{'soil_awc_mm_per_m':math.nan},{'soil_ece_ds_m':'nope'}):
            with self.subTest(payload=payload):
                with self.assertRaises(InputError):validate_inputs(payload)
    def test_api_soil_fields(self):
        c=TestClient(app)
        response=c.post('/api/analyze',json={'soil_type':'loam','soil_ece_ds_m':2,'soil_awc_mm_per_m':120})
        self.assertEqual(response.status_code,200,response.text)
        data=response.json()
        self.assertEqual(data['soil_summary']['awc']['value_mm_per_m'],120)
        self.assertEqual(data['soil_summary']['crop_screening']['faba']['salinity_flag'],'above_published_threshold')
        self.assertIn('soil_screening',data['plans'][0])
    def test_api_rejects_invalid_soil(self):
        c=TestClient(app)
        for input_ in ({'soil_awc_mm_per_m':10},{'soil_ece_ds_m':51}):
            self.assertEqual(c.post('/api/analyze',json=input_).status_code,422)

if __name__=='__main__':unittest.main()
