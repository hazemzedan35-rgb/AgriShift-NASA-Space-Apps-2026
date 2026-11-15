"""Frontend-only smoke test for the AgriShift MVP's documented API contract."""
import argparse
import json
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--base', default='http://127.0.0.1:8000')
args = parser.parse_args()


def fetch(route, body=None):
    method='POST' if body is not None else 'GET'
    data=json.dumps(body).encode() if body is not None else None
    request=urllib.request.Request(
        args.base.rstrip('/')+route,
        data=data,
        method=method,
        headers={'Content-Type':'application/json'},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise AssertionError((route, response.status))
        return json.load(response)


def check():
    health=fetch('/api/health')
    assert health.get('ok') is True, 'Health endpoint not available'
    assert int(health.get('date_count',0))>0, 'Health missing date_count'
    climate=fetch('/api/climate')
    for name in ('average_air_temperature_c','annual_rain_mm','annual_reference_et0_mm'):
        assert isinstance(climate.get(name),(int,float)),f'Missing climate field {name}'
    monthly=fetch('/api/monthly')
    assert len(monthly.get('months',[]))==12, 'Monthly endpoint does not contain 12 months'
    for m in monthly['months']:
        assert isinstance(m.get('daily_mean_mm'),(int,float)), 'Invalid monthly value'
    payload={
        'area_ha':1,
        'water_budget_m3':14500,
        'irrigation_efficiency':0.75,
        'previous_crop':'wheat',
        'priority':'balanced',
        'soil_type':'unknown',
    }
    report=fetch('/api/analyze',payload)
    assert isinstance(report.get('plans'),list) and report['plans'], 'No plans returned'
    assert isinstance(report.get('inputs'),dict), 'No echoed input section'
    assert isinstance(report.get('climate'),dict), 'No climate section'
    for plan in report['plans']:
        assert isinstance(plan.get('crops'),list), 'Plan missing crops array'
        assert isinstance(plan.get('water_proxy_m3'),(int,float)), 'Plan missing water proxy'
        assert isinstance(plan.get('within_total_budget'),bool), 'Plan missing budget status'
    print('PASS: health + climate + 12 months + analyze response contract')
    print('Plans returned:',len(report['plans']))
    print('Climate year:',climate.get('year'))

if __name__=='__main__':
    check()
