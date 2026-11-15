"""FAO Crop Calendar: exact-zone, crop-specific, source-row traceable lookup.

No spatial polygons have been supplied. GPS alone cannot prove that a farm falls
inside an agro-ecological zone, so zones are explicit user selections only.
"""
import json
from functools import lru_cache
from pathlib import Path
DATA=Path(__file__).with_name('egypt_crop_calendar.json')
@lru_cache(maxsize=1)
def load():
    return json.loads(DATA.read_text(encoding='utf-8'))

def zones():return load()['zones']

def validate_zone(value):
    if value in ('',None,'unknown','auto'):return 'unknown'
    if value not in zones():raise ValueError('Unknown FAO Crop Calendar zone; choose a zone from the available Egypt list')
    return value

def get_calendar(crop_id,region=None):
    region=validate_zone(region)
    if region=='unknown':
        return {'status':'region_not_selected','zone':None,'entries':[],
                'note':'GPS does not validate Egypt agro-ecological zone. Choose it manually, or leave the calendar unknown.',
                'source_url':load()['source_url']}
    found=[r for r in load()['records'] if r['crop_id']==crop_id and r['zone']==region]
    return {'status':'regional_records_available' if found else 'no_matching_regional_records',
            'zone':region,'entries':found,
            'note':('Published Egypt crop calendar records for selected zone; cultivation schedule still needs variety and local validation.'
                     if found else 'No matching record; do not copy dates from another crop, zone, or country.'),
            'source_url':load()['source_url']}
