"""Stage A3: real combinatorial multi-season generation, policy and API tests."""
import unittest
from datetime import date
from fastapi.testclient import TestClient
from agrishift_decision.rotation import generate_sequences, seasonal_slots, RotationError
from agrishift_decision.engine import analyze, validate_inputs, load_reference_data, InputError
from agrishift_decision.api import app

CATALOG=load_reference_data()[0]['crops']
# Legacy four-crop baseline remains a dedicated regression scenario after the 12-crop expansion.
LEGACY_BASELINE=['wheat','faba','maize','sunflower']

class TestSequenceGenerator(unittest.TestCase):
    def test_slot_calendar(self):
        self.assertEqual([(s['season'],s['year']) for s in seasonal_slots(6)],
                         [('winter',2026),('summer',2027),('winter',2027),('summer',2028),('winter',2028),('summer',2029)])
    def test_combination_count_grows_with_horizon(self):
        for seasons,count in ((2,4),(4,16),(6,64)):
            with self.subTest(seasons=seasons):
                g=generate_sequences(CATALOG,seasons,LEGACY_BASELINE)
                self.assertEqual(g['generated_count'],count)
                self.assertEqual(g['valid_count'],count)
                self.assertEqual(len(set(g['sequences'])),count)
    def test_eligible_catalog_drives_search(self):
        g=generate_sequences(CATALOG,4,['wheat','faba','sunflower'])
        self.assertEqual(g['valid_count'],4)
        self.assertTrue(all(seq[1]=='sunflower' and seq[3]=='sunflower' for seq in g['sequences']))
    def test_strict_family_filter_is_optional_not_mandatory(self):
        all_=generate_sequences(CATALOG,4,LEGACY_BASELINE,'wheat',False)
        strict=generate_sequences(CATALOG,4,LEGACY_BASELINE,'wheat',True)
        self.assertEqual(all_['valid_count'],16)
        self.assertGreater(strict['excluded_family_rule_count'],0)
        self.assertGreater(strict['valid_count'],0)
        for seq in strict['sequences']:
            family_path=[CATALOG['wheat']['family']]+[CATALOG[c]['family'] for c in seq]
            self.assertTrue(all(a!=b for a,b in zip(family_path,family_path[1:])))
    def test_strict_can_make_crop_selection_infeasible(self):
        g=generate_sequences(CATALOG,4,['wheat','maize'],'wheat',True)
        self.assertEqual(g['valid_count'],0)
    def test_bad_pool_never_silently_substituted(self):
        for pool in ([],['wheat'],['sunflower'],['wheat','invented'],['wheat','wheat','maize']):
            with self.subTest(pool=pool),self.assertRaises(RotationError):
                generate_sequences(CATALOG,4,pool)

class TestEngineA3(unittest.TestCase):
    def test_four_season_engine_has_distinct_valid_sequences(self):
        r=analyze({'planning_seasons':4,'max_results':20,'water_budget_m3':10**9})
        g=r['rotation_generation']
        self.assertEqual(g['generated_before_rules'],16)
        self.assertEqual(g['valid_candidate_count'],16)
        self.assertEqual(g['returned_plan_count'],16)
        self.assertFalse(g['results_truncated'])
        self.assertEqual(len({p['id'] for p in r['plans']}),16)
        self.assertTrue(all(len(p['crops'])==4 for p in r['plans']))
        self.assertEqual(sorted(p['rank'] for p in r['plans']),list(range(1,17)))
    def test_six_seasons_capped_with_truthful_generation_count(self):
        r=analyze({'planning_seasons':6,'max_results':8})
        g=r['rotation_generation']
        self.assertEqual(g['generated_before_rules'],64)
        self.assertEqual(g['valid_candidate_count'],64)
        self.assertEqual(g['returned_plan_count'],8)
        self.assertTrue(g['results_truncated'])
    def test_every_plan_uses_alternating_planting_windows_and_no_overlap(self):
        r=analyze({'planning_seasons':6,'max_results':20})
        for p in r['plans']:
            spans=[(date.fromisoformat(c['planting_date']),date.fromisoformat(c['harvest_estimated_date'])) for c in p['crops']]
            self.assertTrue(all(a<=b for a,b in spans))
            self.assertTrue(all(spans[i][1]<spans[i+1][0] for i in range(len(spans)-1)))
            self.assertEqual([c['season'] for c in p['crops']],['winter','summer','winter','summer','winter','summer'])
    def test_subsets_and_strict_change_generated_search(self):
        a=analyze({'planning_seasons':4,'allowed_crops':['wheat','maize','sunflower'],'max_results':20})
        b=analyze({'planning_seasons':4,'strict_family_rotation':True,'max_results':20})
        self.assertEqual(a['rotation_generation']['valid_candidate_count'],4)
        self.assertLess(b['rotation_generation']['valid_candidate_count'],16)
        self.assertTrue(all('faba' not in p['sequence'] for p in a['plans']))
    def test_full_budget_is_sum_of_each_season(self):
        r=analyze({'planning_seasons':4,'max_results':20,'water_budget_m3':30000})
        for p in r['plans']:
            self.assertAlmostEqual(p['water_proxy_m3'],round(sum(c['gross_planning_proxy_m3'] for c in p['crops']),2),places=2)
            self.assertEqual(p['within_total_budget'], p['water_proxy_m3']<=r['inputs']['water_budget_m3'])
            self.assertAlmostEqual(p['budget_difference_m3'],round(30000-p['water_proxy_m3'],2),places=2)
        self.assertEqual(r['rotation_generation']['water_budget_scope'],'total_across_all_planning_seasons')
    def test_salinity_and_soil_screening_present_every_sequence(self):
        r=analyze({'planning_seasons':4,'soil_ece_ds_m':4,'soil_type':'sand'})
        self.assertEqual(r['soil_summary']['awc']['value_mm_per_m'],80)
        self.assertTrue(all('soil_screening' in p for p in r['plans']))
        self.assertTrue(all(p['soil_screening']['salinity_concern_count']>=0 for p in r['plans']))
    def test_infeasible_strict_not_faked(self):
        with self.assertRaisesRegex(InputError,'No crop sequences'):
            analyze({'planning_seasons':4,'strict_family_rotation':True,'allowed_crops':['wheat','maize'],'previous_crop':'wheat'})
    def test_invalid_parameters_caught(self):
        for payload in (
            {'planning_seasons':3},{'planning_seasons':'4'},{'planning_seasons':True},
            {'allowed_crops':['wheat']},{'allowed_crops':['banana','wheat','maize']},
            {'allowed_crops':['wheat','wheat','maize']},{'strict_family_rotation':'yes'},
            {'max_results':0},{'max_results':65},{'max_results':3.4}):
            with self.subTest(payload=payload),self.assertRaises(InputError):
                inp=validate_inputs(payload)
                # Crop pool checks depend on catalog and occur after input checks.
                if 'allowed_crops' in payload:
                    analyze(payload)

class TestApiA3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c=TestClient(app)
    def test_api_combinatorial_4(self):
        r=self.c.post('/api/analyze',json={'planning_seasons':4,'max_results':20,'water_budget_m3':30000})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['rotation_generation']['valid_candidate_count'],16)
    def test_api_combinatorial_6(self):
        r=self.c.post('/api/analyze',json={'planning_seasons':6,'max_results':6})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['rotation_generation']['generated_before_rules'],64)
        self.assertEqual(len(r.json()['plans']),6)
    def test_api_strict_conflict_returns_422(self):
        r=self.c.post('/api/analyze',json={'planning_seasons':4,'allowed_crops':['wheat','maize'], 'strict_family_rotation':True, 'previous_crop':'wheat'})
        self.assertEqual(r.status_code,422,r.text)
        self.assertIn('No crop sequences',str(r.json()))
    def test_api_validates_pool(self):
        for payload in ({'allowed_crops':['banana','maize']},{'allowed_crops':['wheat']},{'planning_seasons':9},{'max_results':100}):
            self.assertEqual(self.c.post('/api/analyze',json=payload).status_code,422)

if __name__=='__main__':unittest.main()
