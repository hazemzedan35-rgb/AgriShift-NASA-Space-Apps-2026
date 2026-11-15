"""Cross-validate all six Stage1 user files, independently of its quality report."""
import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from collections import defaultdict

PARAMETERS = ('T2M','T2M_MAX','T2M_MIN','PRECTOTCORR','RH2M','WS2M','ALLSKY_SFC_SW_DWN','PS')
EXPECTED_UNITS={'T2M':'C','T2M_MAX':'C','T2M_MIN':'C','PRECTOTCORR':'mm/day',
                'RH2M':'%','WS2M':'m/s','ALLSKY_SFC_SW_DWN':'MJ/m^2/day','PS':'kPa'}
FILENAMES = ('daily_climate.csv','daily_climate.json','metadata.json',
             'monthly_summary.csv','quality_report.json','raw_nasa_response.json')


def verify_source(source_dir):
    source_dir=Path(source_dir)
    for fn in FILENAMES:
        if not (source_dir/fn).is_file():raise FileNotFoundError(f'Missing required Stage1 file: {fn}')
    def load(fn):return json.loads((source_dir/fn).read_text(encoding='utf-8'))
    meta=load('metadata.json'); raw=load('raw_nasa_response.json'); quality=load('quality_report.json')
    daily_json=load('daily_climate.json')
    with (source_dir/'daily_climate.csv').open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f); columns=reader.fieldnames; records=list(reader)
    with (source_dir/'monthly_summary.csv').open(encoding='utf-8-sig',newline='') as f:
        months=list(csv.DictReader(f))
    if columns != ['date',*PARAMETERS]:raise ValueError('Unexpected daily_climate.csv columns')
    req=meta.get('request',{})
    if meta.get('data_status') != 'LIVE_NASA_API' or meta.get('source_mode') != 'live':
        raise ValueError('Stage1 metadata does not identify LIVE_NASA_API source')
    if req.get('community')!='AG' or req.get('time_standard')!='LST':
        raise ValueError('Unexpected Stage1 community or time standard')
    if req.get('parameters')!=list(PARAMETERS):
        raise ValueError('Stage1 parameter mismatch')
    if not -90<=float(req['latitude'])<=90 or not -180<=float(req['longitude'])<=180:
        raise ValueError('Invalid location')
    if raw.get('header',{}).get('start')!=req['start'].replace('-','') or raw.get('header',{}).get('end')!=req['end'].replace('-',''):
        raise ValueError('Raw NASA header does not agree with metadata request date range')
    if list(raw.get('geometry',{}).get('coordinates',[]))[:2] != [float(req['longitude']),float(req['latitude'])]:
        raise ValueError('Raw NASA coordinates do not match requested point')
    for p in PARAMETERS:
        if meta.get('nasa_parameters',{}).get(p,{}).get('units')!=EXPECTED_UNITS[p]:
            raise ValueError(f'NASA units do not match expectation: {p}')
        if quality.get('observed_units',{}).get(p)!=EXPECTED_UNITS[p]:
            raise ValueError(f'Quality report unit mismatch: {p}')
    start,end=date.fromisoformat(req['start']),date.fromisoformat(req['end'])
    expected_days=(end-start).days+1
    if expected_days!=len(records) or len(records)!=len(daily_json) or len(set(x['date'] for x in records))!=len(records):
        raise ValueError('Daily length/duplicate dates inconsistency')
    raw_params=raw['properties']['parameter']
    for i,row in enumerate(records):
        expected_date=(start+timedelta(days=i)).isoformat()
        if row['date']!=expected_date or daily_json[i]['date']!=expected_date:
            raise ValueError(f'Daily date grid mismatch at row {i}')
        rawdate=expected_date.replace('-','')
        for p in PARAMETERS:
            got=float(row[p]); rawval=raw_params[p][rawdate]; jval=daily_json[i][p]
            if got!=float(rawval) or got!=float(jval):
                raise ValueError(f'Raw/CSV/JSON mismatch: {p}, {expected_date}')
    group=defaultdict(list)
    for row in records:group[row['date'][:7]].append(row)
    if len(months)!=len(group):raise ValueError('Missing monthly summary rows')
    for line in months:
        key=line['month']; rr=group[key]
        def avg(p):return sum(float(z[p]) for z in rr)/len(rr)
        def total(p):return sum(float(z[p]) for z in rr)
        expected={'days_in_selection':len(rr), 'mean_temperature_c':avg('T2M'),
                  'precipitation_total_mm':total('PRECTOTCORR'),
                  'mean_relative_humidity_pct':avg('RH2M'),
                  'solar_radiation_total_mj_m2':total('ALLSKY_SFC_SW_DWN')}
        for k,v in expected.items():
            if abs(float(line[k])-v)>0.0011:
                raise ValueError(f'Monthly summary mismatch: {key} {k}')
    if quality.get('rows')!=len(records) or quality.get('date_grid_complete') is not True:
        raise ValueError('Quality report contradicts daily data')
    if any(quality.get('missing_values_by_parameter',{}).get(p)!=0 for p in PARAMETERS):
        raise ValueError('Quality report identifies missing values')
    hashes={fn:hashlib.sha256((source_dir/fn).read_bytes()).hexdigest() for fn in FILENAMES}
    return records, meta, {'verified_daily_rows':len(records),
        'first_day':start.isoformat(),'last_day':end.isoformat(),
        'csv_json_raw_exactly_equal':True,'monthly_summary_matches_daily':True,
        'units_checked':True,'sha256_by_file':hashes}
