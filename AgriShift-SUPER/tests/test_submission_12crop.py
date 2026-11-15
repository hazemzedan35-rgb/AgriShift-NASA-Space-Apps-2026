"""Submission science safeguards for the expanded FAO-56 crop library.

These tests use the bundled real historical Nile Delta NASA dataset. External
NASA and Gemini connections are not claimed to be live-tested here.
"""
from datetime import date
import math
from fastapi.testclient import TestClient
from agrishift_decision.engine import load_reference_data,calculate_crop,analyze
from agrishift_decision.suitability import assess_all
from agrishift_decision.api import app

REFERENCE=load_reference_data()
INPUT={'latitude':30.5,'longitude':31.5,'area_ha':1,'irrigation_efficiency':0.75,
       'soil_type':'unknown','soil_awc_mm_per_m':None,'soil_ece_ds_m':None,
       'soil_ph':None,'first_winter_year':2027}

def test_exactly_twelve_nonfabricated_fao56_water_profiles():
    db,_,_,eto,climate=REFERENCE
    assert len(db['crops'])==12
    eto_by_date={r['date']:r for r in eto}; climate_by_date={r['date']:r for r in climate}
    for cid,crop in db['crops'].items():
        record=calculate_crop(cid,db,climate_by_date,eto_by_date,1,.75,2027)
        assert len(record['daily'])==sum(crop['stages_days'])>0
        assert record['crop_et_mm']>0 and math.isfinite(record['crop_et_mm'])
        assert 'FAO-56 Table' in crop['kc_basis'] or cid in ('wheat','faba','maize','sunflower')
        assert '2025' in record['daily'][0]['reference_2025_date']

def test_paddy_gross_water_unknown_not_zero_or_fabricated():
    db,_,_,eto,climate=REFERENCE
    r=calculate_crop('rice',db,{x['date']:x for x in climate},{x['date']:x for x in eto},1,.75,2027)
    assert r['crop_et_mm']>0
    assert r['gross_planning_proxy_m3'] is None
    assert 'paddy' in r['water_scope'].lower()

def test_all_12_have_suitability_evidence_or_explicit_unknown():
    r=assess_all(INPUT,REFERENCE)
    assert r['crop_count']==12
    assert r['rotation_ready_count']==10
    assert r['data_coverage']['ecocrop_verified_profiles']==12
    assert r['data_coverage']['regional_calendar_crop_count']==0
    for item in r['crops']:
        assert item['suitability']['overall_suitability_score'] is None
        assert item['suitability']['climate_temperature']['status'] in ('within_reference_range','outside_reference_range')
        assert item['suitability']['ecocrop_row_id'] is not None
        assert item['suitability']['soil_ph']['status']=='unknown'
        assert item['suitability']['soil_salinity']['status']=='unknown'

def test_soil_salinity_reference_cautions_and_unknown_sunflower():
    r=assess_all({**INPUT,'soil_ece_ds_m':4},REFERENCE)
    d={x['id']:x for x in r['crops']}
    assert d['wheat']['suitability']['soil_salinity']['status']=='within_reference_threshold'
    assert d['faba']['suitability']['soil_salinity']['status']=='caution'
    assert d['sunflower']['suitability']['soil_salinity']['status']=='unknown'
    assert d['rice']['suitability']['soil_salinity']['status']=='caution'

def test_calendars_never_overlap_in_expanded_multi_season_rotations():
    allowed=['wheat','faba','potato','onion','sugarbeet','maize','sunflower','cotton','tomato','sorghum']
    r=analyze({'planning_seasons':6,'first_winter_year':2027,'allowed_crops':allowed,'max_results':64},REFERENCE)
    assert r['rotation_generation']['generated_before_rules']==15625
    assert r['rotation_generation']['excluded_by_calendar_overlap']>0
    assert r['rotation_generation']['valid_candidate_count']>0
    for p in r['plans']:
        spans=[(date.fromisoformat(c['planting_date']),date.fromisoformat(c['harvest_estimated_date'])) for c in p['crops']]
        assert all(spans[i][1]<spans[i+1][0] for i in range(len(spans)-1))
        assert 'rice' not in p['sequence'] and 'alfalfa' not in p['sequence']

def test_rest_api_and_submission_dashboard_contract():
    c=TestClient(app)
    crop=c.get('/api/crops').json()
    assert crop['analysis_ready_count']==12 and crop['rotation_candidate_count']==10
    r=c.post('/api/crop-assessment',json={'latitude':30.5,'longitude':31.5,'soil_ece_ds_m':4})
    assert r.status_code==200,r.text
    assert len(r.json()['crops'])==12
    html=c.get('/dashboard.html').text
    assert 'id="crop-suitability"' in html
    assert 'crop-evidence.js' in html
    assert 'name="soil_ph"' in html
    assert all(f'value="{name}"' in html for name in ('potato','cotton','sorghum','sugarbeet'))

def test_missing_nasa_does_not_invent_location_climate(monkeypatch):
    from agrishift_decision import api
    from agrishift_decision.location_data import ClimateDataError
    monkeypatch.setattr(api,'get_reference_data',lambda *args: (_ for _ in ()).throw(ClimateDataError('NASA unavailable')))
    r=TestClient(app).post('/api/crop-assessment',json={'latitude':33,'longitude':11})
    assert r.status_code==503
    assert 'NASA unavailable' in r.text
