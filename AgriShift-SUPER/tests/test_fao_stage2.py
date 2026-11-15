"""Independent FAO-56 checks plus data integrity and regression tests."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from agrishift_fao.fao56 import (fao_pm, extraterrestrial_radiation, saturation_vapour_pressure,
                                 calculate_daily_eto)
from agrishift_fao.validation import verify_source
from agrishift_fao.cli import run

INPUT=Path(__file__).resolve().parents[1]/'outputs'/'nile_delta_2025'

class Fao56ScientificTests(unittest.TestCase):
    def test_fao_example_18_eto_3_point_9_mm_day(self):
        # FAO-56 Ch4 Example 18: Uccle Belgium, 6 July: reference ET0 = 3.88 ~ 3.9.
        # Intermediate numbers rounded by FAO publication.
        actual=fao_pm(tmean_c=16.9,u2_m_s=2.078,es_kpa=1.997,ea_kpa=1.409,
                      delta_kpa_c=0.122,gamma_kpa_c=0.0666,net_radiation_mj_m2_day=13.28)
        self.assertAlmostEqual(actual,3.88,delta=0.055)
    def test_fao_example_18_full_equation(self):
        # FAO-56 Example 18 supplies Tmax, Tmin, Rs, pressure and an Ea from
        # RHmax/min; give the mathematically corresponding RHmean-like value
        # to the simplified pipeline and check that *all* steps reproduce ~3.88.
        # No NASA observations are being imitated here; this is a FAO reference.
        sample={'date':'2025-07-06','T2M':16.9,'T2M_MAX':21.5,
                'T2M_MIN':12.3,'RH2M':70.55,'WS2M':2.078,
                'ALLSKY_SFC_SW_DWN':22.07,'PS':100.1}
        calculated=calculate_daily_eto(sample,50.8,100.0)
        self.assertAlmostEqual(calculated['eto_mm_day'],3.88,delta=0.06)

    def test_fao_example_18_ra(self):
        # FAO-56 Example 18: lat 50.8, J 187, Ra=41.09 MJ/m2/day.
        self.assertAlmostEqual(extraterrestrial_radiation(50.8,187),41.09,delta=0.15)
    def test_saturated_pressure_20_c(self):
        self.assertAlmostEqual(saturation_vapour_pressure(20),2.338,delta=0.004)
    def test_raises_invalid(self):
        data={'date':'2025-01-01','T2M':19,'T2M_MAX':10,'T2M_MIN':20,
             'RH2M':60,'WS2M':2,'ALLSKY_SFC_SW_DWN':15,'PS':101}
        with self.assertRaises(ValueError):calculate_daily_eto(data,30.5)
        data['T2M_MAX']=30
        with self.assertRaises(ValueError):calculate_daily_eto(data,30.5,float('nan'))
    def test_eto_positive_example_day(self):
        input={'date':'2025-01-01','T2M':14.35,'T2M_MAX':21.41,'T2M_MIN':9.0,
             'RH2M':69.97,'WS2M':1.95,'ALLSKY_SFC_SW_DWN':12.19,'PS':102.38}
        res=calculate_daily_eto(input,30.5)
        self.assertTrue(0<res['eto_mm_day']<10)
        self.assertGreater(res['rso_mj_m2_day'],0)

class RealDataIntegrityTests(unittest.TestCase):
    def test_six_files_consistent(self):
        rows,meta,check=verify_source(INPUT)
        self.assertEqual(len(rows),365)
        self.assertEqual((meta['request']['latitude'],meta['request']['longitude']),(30.5,31.5))
        self.assertTrue(check['csv_json_raw_exactly_equal'])
        self.assertTrue(check['monthly_summary_matches_daily'])
    def test_whole_year_run_and_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            summary=run(INPUT,d,0)
            self.assertEqual(summary['days'],365)
            self.assertGreater(summary['eto_total_mm'],300)
            self.assertLess(summary['eto_total_mm'],4000)
            with open(Path(d)/'daily_eto.csv',newline='',encoding='utf-8') as f:
                self.assertEqual(len(list(csv.DictReader(f))),365)
            science=json.loads((Path(d)/'science_method.json').read_text(encoding='utf8'))
            self.assertEqual(science['albedo'],0.23)
    def test_elevation_sensitivity(self):
        rows,_,_=verify_source(INPUT)
        a=calculate_daily_eto(rows[0],30.5,0)['eto_mm_day']
        b=calculate_daily_eto(rows[0],30.5,50)['eto_mm_day']
        self.assertNotEqual(a,b)
        self.assertLess(abs(a-b),0.3)

if __name__=='__main__':unittest.main()
