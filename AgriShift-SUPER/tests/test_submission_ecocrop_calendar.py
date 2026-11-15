"""Evidence contract for user-supplied EcoCrop/FAO Egypt calendar data and UI."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from agrishift_decision.api import app
from agrishift_decision.calendar_evidence import get_calendar, zones
from agrishift_decision.engine import load_reference_data
from agrishift_decision.suitability import assess_all
ROOT=Path(__file__).resolve().parents[1]
CLIENT=TestClient(app)
REFERENCE=load_reference_data()
DEMO=dict(latitude=30.5,longitude=31.5,area_ha=1,irrigation_efficiency=.75,
          first_winter_year=2027,soil_type='unknown',soil_ece_ds_m=None,soil_ph=None)

def test_all_12_profiles_have_source_identity_and_valid_ranges():
    records=json.loads((ROOT/'agrishift_decision/ecocrop_profiles.json').read_text())
    assert len(records)==12
    assert len({x['source_row_id'] for x in records.values()})==12
    assert records['tomato']['species']=='Lycopersicon esculentum'  # exact CSV taxon label
    assert records['cotton']['species']=='Gossypium barbadense'  # NOT all cotton species
    assert records['sugarbeet']['species']=='Beta vulgaris'  # cultivar group not identified
    assert records['wheat']['source_row_id']=='2114'
    for cid,p in records.items():
        assert p['source_row_id'].isdigit() and 'OpenCLIM' in p['source_url']
        for field in ('temperature_c','temperature_optimal_c','soil_ph','soil_ph_optimal',
                      'annual_rainfall_mm','annual_rainfall_optimal_mm'):
            v=p[field];assert v and len(v)==2 and v[0]<=v[1],(cid,field,v)

def test_regional_calendar_is_not_inferred_from_gps():
    assert get_calendar('wheat','unknown')['status']=='region_not_selected'
    assert 'Delta region' in zones()
    expected=get_calendar('wheat','Delta region')
    assert expected['status']=='regional_records_available'
    assert all(r['zone']=='Delta region' and r['source_excel_row']>=3 for r in expected['entries'])
    assert expected['entries'][0]['sowing_window']['start']=={'day':15,'month':11}
    assert get_calendar('cotton','Delta region')['status']=='no_matching_regional_records'
    assert get_calendar('maize','Delta region')['status']=='no_matching_regional_records'
    assert get_calendar('alfalfa','Delta region')['status']=='no_matching_regional_records'
    assert get_calendar('rice','Delta region')['status']=='no_matching_regional_records'  # source has unspecified zone

def test_water_and_suitability_source_context_and_missing_soil():
    out=assess_all({**DEMO,'calendar_zone':'Delta region'},REFERENCE)
    assert out['crop_count']==12
    assert out['data_coverage']['ecocrop_verified_profiles']==12
    assert out['data_coverage']['regional_calendar_crop_count']==7
    for item in out['crops']:
        e=item['suitability']
        assert e['overall_suitability_score'] is None
        assert e['soil_ph']['status']=='unknown'  # GPS never supplies soil pH
        assert e['soil_drainage']['status']=='unknown'
        assert e['climate_observations']['historical_annual_rain_mm'] is not None
        assert e['climate_rainfall_rainfed_reference']['irrigation_caveat']
        assert e['ecocrop_row_id']

def test_measured_site_soil_changes_diagnostics_not_ecocrop_numbers():
    out=assess_all({**DEMO,'calendar_zone':'Delta region','soil_ph':6.5,
                    'soil_type':'loam','soil_drainage':'well','soil_ece_ds_m':2},REFERENCE)
    records={x['id']:x for x in out['crops']}
    wheat=records['wheat']['suitability']
    assert wheat['soil_ph']['status']=='within_reference_range'
    assert wheat['soil_texture']['status'] in ('within_reference_category','outside_reference_category','unknown')
    assert wheat['regional_calendar']['status']=='regional_records_available'
    assert wheat['assessed_dimensions']>2
    assert wheat['overall_suitability_score'] is None

def test_api_evidence_and_zone_validation_and_html_controls():
    z=CLIENT.get('/api/calendar-zones');assert z.status_code==200
    assert z.json()['records']==113
    html=CLIENT.get('/dashboard.html').text
    for tag in ('name="soil_drainage"','name="calendar_zone"','crop-evidence.js','Delta region'):
        assert tag in html
    assert '4 CURRENTLY SUPPORTED IN ANALYSIS' not in html
    r=CLIENT.post('/api/crop-assessment',json={**DEMO,'calendar_zone':'Delta region'})
    assert r.status_code==200,r.text
    assert r.json()['data_coverage']['regional_calendar_crop_count']==7
    bad=CLIENT.post('/api/crop-assessment',json={**DEMO,'calendar_zone':'Fabricated country zone'})
    assert bad.status_code==422
    plan=CLIENT.post('/api/analyze',json={'latitude':30.5,'longitude':31.5,'calendar_zone':'Delta region'})
    assert plan.status_code==200,plan.text
    assert plan.json()['environmental_evidence']['rankings_updated_by_screening'] is False
    assert plan.json()['plans'][0]['site_screening']['screening_status']=='advisory_only_not_a_field_recommendation'

