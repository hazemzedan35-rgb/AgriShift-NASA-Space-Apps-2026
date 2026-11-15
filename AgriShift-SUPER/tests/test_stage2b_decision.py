"""Unit and integration tests for Stage 2b / Stage 3 / local API."""
import math
import unittest
from datetime import date
from fastapi.testclient import TestClient
from agrishift_decision.engine import (analyze,calculate_crop,crop_coefficient,
   load_reference_data,validate_inputs,InputError)
from agrishift_decision.api import app

class TestCropKc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db,cls.meta,cls.summary,cls.eto,cls.climate=load_reference_data()
    def test_reference_records(self):
        self.assertEqual(len(self.eto),365)
        self.assertEqual(self.climate[0]['date'],'2025-01-01')
        self.assertEqual(self.meta['data_status'],'LIVE_NASA_API')
    def test_kc_initial_mid_end(self):
        for crop in self.db['crops'].values():
            a,b,c,d=crop['stages_days'];n=a+b+c+d
            self.assertAlmostEqual(crop_coefficient(crop,0),crop['kc_initial'])
            self.assertAlmostEqual(crop_coefficient(crop,a+b),crop['kc_mid'])
            self.assertAlmostEqual(crop_coefficient(crop,n-1),crop['kc_end'])
    def test_kc_growth_stages(self):
        crop=self.db['crops']['wheat']; a,b,c,d=crop['stages_days']
        self.assertAlmostEqual(crop_coefficient(crop,a-1),crop['kc_initial'])
        self.assertAlmostEqual(crop_coefficient(crop,a+b-1),crop['kc_mid'])
        self.assertAlmostEqual(crop_coefficient(crop,a+b+c-1),crop['kc_mid'])
    def test_out_of_range(self):
        crop=self.db['crops']['wheat']
        for i in (-1,sum(crop['stages_days'])):
            with self.assertRaises(InputError):crop_coefficient(crop,i)
    def test_crop_finite_water(self):
        r=analyze({'area_ha':1})
        for p in r['plans']:
            self.assertGreater(p['water_proxy_m3'],0)
            self.assertEqual(len(p['crops']),2)
    def test_crop_schedule(self):
        r=analyze({'first_winter_year':2026})   # explicit year: the default now depends on today's date
        for p in r['plans']:
            for c in p['crops']:
                start=date.fromisoformat(c['planting_date'])
                end=date.fromisoformat(c['harvest_estimated_date'])
                self.assertGreaterEqual(end,start)
                self.assertIn(start.year,(2026,2027))
    def test_crop_etc_consistent_with_sum(self):
        db,_,_,eto,climate=load_reference_data()
        c=calculate_crop('maize',db,{r['date']:r for r in climate},{r['date']:r for r in eto},1,.75)
        self.assertAlmostEqual(c['crop_et_mm'],round(sum(v['etc_mm_day'] for v in c['daily']),2),2)
        self.assertAlmostEqual(c['gross_planning_proxy_m3'],round(c['crop_et_mm']/.75*10,2),1)
    def test_previous_crop_changes_diversity(self):
        w=analyze({'previous_crop':'wheat'});f=analyze({'previous_crop':'faba'})
        scoresw={p['id']:p['diversity_heuristic'] for p in w['plans']}
        scoresf={p['id']:p['diversity_heuristic'] for p in f['plans']}
        self.assertNotEqual(scoresw,scoresf)
    def test_priority_changes_ranking_scores(self):
        a=analyze({'priority':'water'});b=analyze({'priority':'diversity'})
        x={p['id']:p['comparison_score'] for p in a['plans']}
        y={p['id']:p['comparison_score'] for p in b['plans']}
        self.assertNotEqual(x,y)
    def test_budget_changes_feasibility_not_water_model(self):
        low=analyze({'water_budget_m3':0});high=analyze({'water_budget_m3':1e9})
        self.assertTrue(all(not p['within_total_budget'] for p in low['plans']))
        self.assertTrue(all(p['within_total_budget'] for p in high['plans']))
        self.assertEqual(sorted(p['water_proxy_m3'] for p in low['plans']),sorted(p['water_proxy_m3'] for p in high['plans']))
    def test_area_scaling(self):
        a=analyze({'area_ha':1});b=analyze({'area_ha':2})
        x={p['id']:p['water_proxy_m3'] for p in a['plans']}
        y={p['id']:p['water_proxy_m3'] for p in b['plans']}
        for k in x:self.assertAlmostEqual(y[k],2*x[k],places=1)
    def test_efficiency_changes_gross(self):
        a=analyze({'irrigation_efficiency':0.5})
        b=analyze({'irrigation_efficiency':1})
        x={p['id']:p['water_proxy_m3'] for p in a['plans']}
        y={p['id']:p['water_proxy_m3'] for p in b['plans']}
        for k in x:self.assertAlmostEqual(x[k],2*y[k],places=1)
    def test_soil_not_used_as_unvalidated_scoring(self):
        a=analyze({'soil_type':'clay'});b=analyze({'soil_type':'sand'})
        self.assertEqual([p['id'] for p in a['plans']],[p['id'] for p in b['plans']])
    def test_no_suggested_yield_or_ml(self):
        r=analyze({})
        self.assertIn('No ML model trained', ' '.join(r['limitations']))
        self.assertNotIn('yield_prediction',r)
    def test_ranking_stable(self):
        r=analyze({})
        self.assertEqual(sorted(p['rank'] for p in r['plans']),[1,2,3,4])
        self.assertTrue(all(p['comparison_weights'] for p in r['plans']))
    def test_invalid_inputs(self):
        for request in [{'area_ha':0},{'area_ha':'abc'},{'water_budget_m3':-1},{'irrigation_efficiency':0.1},{'irrigation_efficiency':2},{'previous_crop':'banana'},{'priority':'magic'},{'soil_type':'dirty'},{'area_ha':math.nan}]:
            with self.subTest(request=request):
                with self.assertRaises(InputError):validate_inputs(request)

class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.client=TestClient(app)
    def test_home_dashboard(self):
        for route in ('/','/dashboard.html','/dist/js/decision-studio.js','/dist/css/adminlte.min.css','/dist/css/agrishift-dashboard.css','/dist/vendor/bootstrap/bootstrap.min.js','/dist/vendor/bootstrap-icons/fonts/bootstrap-icons.woff2'):
            r=self.client.get(route)
            self.assertEqual(r.status_code,200,route)
    def test_health(self):
        d=self.client.get('/api/health').json()
        self.assertEqual(d['date_count'],365)
        self.assertEqual(d['data_source'],'LIVE_NASA_API')
    def test_climate_monthly(self):
        c=self.client.get('/api/climate').json()
        m=self.client.get('/api/monthly').json()
        self.assertEqual(len(m['months']),12)
        self.assertAlmostEqual(c['annual_reference_et0_mm'],round(sum(v['eto_total_mm'] for v in m['months']),2),1)
    def test_analysis_success(self):
        r=self.client.post('/api/analyze',json={'area_ha':1,'water_budget_m3':14500})
        self.assertEqual(r.status_code,200,r.text)
        d=r.json();self.assertEqual(len(d['plans']),4)
        self.assertEqual(d['climate']['year'],2025)
    def test_analysis_reject_invalid(self):
        for obj in ({'area_ha':-5},{'previous_crop':'banana'},{'irrigation_efficiency':-1}):
            self.assertEqual(self.client.post('/api/analyze',json=obj).status_code,422)

if __name__=='__main__':unittest.main()
