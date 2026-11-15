"""Integration checks for the new unified AgriShift build. NASA/Gemini remain offline in tests."""
import os
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from agrishift_decision.api import app
from agrishift_decision import location_data as ld

ROOT=Path(__file__).resolve().parents[1]
client=TestClient(app, raise_server_exceptions=False)

def test_new_site_and_static_assets():
    for url in ('/','/dashboard.html','/dist/js/decision-studio.js',
                '/dist/js/agrishift-chat.js','/dist/js/agrishift-chat-config.js',
                '/dist/img/crops/sorghum.png','/dist/img/crops/sugarbeet-team-photo.png'):
        r=client.get(url)
        assert r.status_code==200, (url, r.status_code)
    html=client.get('/dashboard.html').text
    assert 'useGpsBtn' in html and 'planning_seasons' in html
    assert 'latitude' in html and 'longitude' in html

def test_coordinates_are_not_silently_replaced_by_pilot():
    with patch.object(ld,'_fetch_json',side_effect=ld.ClimateDataError('offline')):
        r=client.post('/api/analyze',json={'latitude':32.5,'longitude':31.4})
        assert r.status_code==503
        assert 'offline' in r.json()['detail']

def test_specific_location_monthly_uses_location_lookup():
    from agrishift_decision.engine import load_reference_data
    data=load_reference_data()
    with patch('agrishift_decision.api.get_reference_data',return_value=data) as lookup:
        out=client.get('/api/monthly?latitude=30.5&longitude=31.5')
        assert out.status_code==200
        assert len(out.json()['months'])==12
        lookup.assert_called_once_with(30.5,31.5)

def test_farm_4_and_6_seasons_with_real_bundled_pilot():
    for n in (4,6):
        r=client.post('/api/analyze',json={'latitude':30.5,'longitude':31.5,'planning_seasons':n,'water_budget_m3':100000})
        assert r.status_code==200, r.text
        result=r.json()
        assert result['rotation_generation']['planning_seasons']==n
        assert all(len(p['crops'])==n for p in result['plans'])
        assert result['climate']['latitude']==30.5
        assert result['climate']['monthly_eto']

def test_sources_are_honest_and_crop_catalogue_status():
    r=client.get('/api/data-sources');assert r.status_code==200
    s=r.json()['integration_status']
    assert s['power_daily']=='implemented'
    assert s['ecocrop_automated_lookup']=='bundled_source_profiles_offline'
    assert s['fao_egypt_crop_calendar']=='user_supplied_records_offline_with_manual_zone_selection'
    d=client.get('/api/crops').json()
    assert d['analysis_ready_count']==12 and d['library_count']==12
    assert d['rotation_candidate_count']==10

def test_chat_is_mounted_without_including_secret_file():
    assert not (ROOT/'agrishift_chatbot/.env').exists()
    r=client.get('/assistant/api/health')
    assert r.status_code==200 and isinstance(r.json()['ok'],bool)
    # Authentication key intentionally not stored in the distribution.
    with patch('agrishift_chatbot.service.KEY',''):
        r=client.post('/assistant/api/chat',json={'messages':[{'role':'user','content':'Hello'}],
              'lat':30.5,'lon':31.5,'place':'demo','lang':'en'})
    assert r.status_code==503
