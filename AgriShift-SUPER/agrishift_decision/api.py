"""AgriShift local REST API with cached NASA reference dataset and static website."""
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
from .suitability import assess_all
from .calendar_evidence import validate_zone, zones, load as load_calendar
from agrishift_chatbot.service import app as chatbot_app
from .engine import analyze, load_reference_data, summarize_climate, validate_request, InputError
from .config import REFERENCE_YEAR, MIN_FIRST_WINTER_YEAR, MAX_FIRST_WINTER_YEAR
from .location_data import get_reference_data, ClimateDataError, monthly_eto

APP_ROOT=Path(__file__).resolve().parents[1]
app=FastAPI(title='AgriShift Decision API',version='1.0.0',description='Transparent prototype, NOT verified planting advice.')

class FarmInput(BaseModel):
    latitude: float = Field(default=30.5, ge=-90, le=90)
    longitude: float = Field(default=31.5, ge=-180, le=180)
    area_ha:float=Field(default=1,ge=0.01,le=10000)
    water_budget_m3:float=Field(default=14500,ge=0,le=1e9)
    irrigation_efficiency:float=Field(default=0.75,ge=0.35,le=1)
    previous_crop:str='wheat'
    planning_seasons:Literal[2,4,6]=2
    first_winter_year:int|None=Field(default=None,ge=MIN_FIRST_WINTER_YEAR,le=MAX_FIRST_WINTER_YEAR,description='Calendar year of the first winter sowing. Default: the next winter sowing date that has not already passed.')
    allowed_crops:list[str]|None=None
    strict_family_rotation:bool=False
    max_results:int=Field(default=12,ge=1,le=64)
    priority:Literal['balanced','water','diversity']='balanced'
    soil_type:Literal['unknown','clay','loam','sand']='unknown'
    soil_awc_mm_per_m:float|None=Field(default=None,ge=20,le=350,description='Measured/estimated available water capacity in mm per metre of soil')
    soil_ece_ds_m:float|None=Field(default=None,ge=0,le=50,description='Saturated-paste soil extract EC, dS/m. Not irrigation-water EC.')
    soil_ph:float|None=Field(default=None,ge=0,le=14,description='Laboratory/field measured soil pH, if available. Does NOT infer from GPS.')
    soil_drainage:Literal['unknown','well','moderate','poor']='unknown'
    calendar_zone:str=Field(default='unknown',max_length=120)  # explicitly selected FAO Egypt agro-ecological zone; not inferred from GPS

@app.exception_handler(RequestValidationError)
async def request_validation_error(request, exc):
    """Clean 422 for bad input. FastAPI's default body echoes the offending value back, and a
    JSON value such as NaN/Infinity/1e400 cannot be written into a JSON response (HTTP 500).
    We keep only where the problem is, what it is, and its type."""
    detail=[{'loc':[part if isinstance(part,(int,str)) else str(part) for part in error.get('loc',())],
             'msg':str(error.get('msg','Invalid value')),'type':str(error.get('type','value_error'))}
            for error in exc.errors()]
    return JSONResponse(status_code=422,content={'detail':detail})

@app.get('/api/health')
def health():
    _,meta,_,eto,_=load_reference_data()
    return {'ok':True,'project':'AgriShift','date_count':len(eto),'data_source':meta['data_status']}

def _requested_location(latitude, longitude):
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail='Provide both latitude and longitude')
    if latitude is None:
        return load_reference_data()
    try:
        from .location_data import normalize_coordinates
        lat, lon = normalize_coordinates(latitude, longitude)
        from .config import MAX_SUPPORTED_ABS_LATITUDE
        if abs(lat) > MAX_SUPPORTED_ABS_LATITUDE:
            raise HTTPException(status_code=422, detail='Latitude not supported by current FAO-56 ET0 method')
        return get_reference_data(lat, lon)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ClimateDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.get('/api/climate')
def climate(latitude:float|None=Query(None,ge=-90,le=90), longitude:float|None=Query(None,ge=-180,le=180)):
    _,meta,summary,_,rows=_requested_location(latitude,longitude)
    result=summarize_climate(meta,summary,rows)
    result['reference_only']=(latitude is None)
    return result

@app.get('/api/monthly')
def monthly(latitude:float|None=Query(None,ge=-90,le=90), longitude:float|None=Query(None,ge=-180,le=180)):
    _,meta,_,eto,_=_requested_location(latitude,longitude)
    return {'year':REFERENCE_YEAR,'latitude':meta['request']['latitude'],
            'longitude':meta['request']['longitude'], 'months':monthly_eto(eto),
            'reference_only':(latitude is None)}

@app.get('/api/data-sources')
def data_sources():
    return {'nasa_power':'https://power.larc.nasa.gov/docs/services/api/temporal/daily/',
            'fao56':'https://www.fao.org/4/X0490E/x0490e00.htm',
            'fao_cropwat':'https://www.fao.org/land-water/resources/tools/software/cropwat/en',
            'fao_ecocrop':'https://www.fao.org/geospatial/data-and-tools/data-portals/ecocrop/en',
            'nasa_appeears':'https://appeears.earthdatacloud.nasa.gov/',
            'integration_status':{'power_daily':'implemented','fao56_reference':'implemented',
                'cropwat_application':'reference_only','ecocrop_automated_lookup':'bundled_source_profiles_offline',
                'fao_egypt_crop_calendar':'user_supplied_records_offline_with_manual_zone_selection',
                'appeears':'not_connected'}}

@app.get('/api/crops')
def crops():
    db,*_=load_reference_data()
    return {'crop_database_status':db['database_status'], 'crops':db['crops'],'references':db['references'],
            'analysis_ready_count':len(db['crops']),'library_count':12,
            'rotation_candidate_count':sum(c.get('rotation_eligible',True) for c in db['crops'].values()),
            'limitation':'12 FAO-56 ETc examples and 12 source-traceable ECOCROP species envelopes; 10 hypothetical annual rotation candidates. Paddy rice field water and alfalfa multi-cut water are unmodeled; field validation still required.'}

@app.get('/api/calendar-zones')
def calendar_zones():
    calendar=load_calendar()
    return {'country':'Egypt','zones':zones(), 'records':len(calendar['records']),
            'source_url':calendar['source_url'],
            'note':'These are source labels, not GIS polygons. Farmers must select the correct zone; GPS alone does not determine it.'}

@app.post('/api/analyze')
def analyze_farm(payload:FarmInput):
    try:
        fields=payload.model_dump()
        fields['calendar_zone']=validate_zone(fields['calendar_zone'])
        checked=validate_request(fields)  # refuse bad requests BEFORE a NASA download
        reference=get_reference_data(checked['latitude'], checked['longitude'])
        result=analyze(fields, reference_data=reference)
        screening=assess_all({**checked,'calendar_zone':fields['calendar_zone'],
                              'soil_drainage':fields['soil_drainage']},reference)
        by_id={x['id']:x for x in screening['crops']}
        result['environmental_evidence']={
            'model':'EcoCrop historical species envelopes + FAO Egypt calendar (user-selected zone)',
            'calendar_zone':fields['calendar_zone'],
            'rankings_updated_by_screening':False,
            'note':'Environmental screens are diagnostic, not an agronomically validated plan ranking. Check all cautions.',
            'crops':{cid:{'status':x['suitability']['status'],
                          'missing_evidence':x['suitability']['missing_evidence'],
                          'ecocrop_row_id':x['suitability']['ecocrop_row_id'],
                          'regional_calendar_status':x['suitability']['regional_calendar']['status']}
                     for cid,x in by_id.items()}}
        for plan in result['plans']:
            risk=[cid for cid in plan['sequence'] if by_id[cid]['suitability']['status']=='partial_caution']
            plan['site_screening']={'caution_crop_ids':risk,'regional_calendar_zone':fields['calendar_zone'],
                'screening_status':'advisory_only_not_a_field_recommendation',
                'note':'Published ECOCROP and calendar diagnostics do not certify rotation feasibility.'}
            if risk:plan['signals'].append('EcoCrop or growth-period screening cautions for: '+', '.join(sorted(set(risk)))+'. See 12-crop assessment.')
        return result
    except (InputError,ValueError) as exc:raise HTTPException(status_code=422, detail=str(exc))
    except ClimateDataError as exc:raise HTTPException(status_code=503, detail=str(exc))

@app.post('/api/crop-assessment')
def crop_assessment(payload:FarmInput):
    try:
        fields=payload.model_dump()
        # Validate numeric/environmental inputs without forcing every crop into a rotation.
        from .engine import validate_inputs
        fields['calendar_zone']=validate_zone(fields['calendar_zone'])
        cleaned=validate_inputs(fields)
        cleaned['soil_ph']=fields.get('soil_ph')
        cleaned['soil_drainage']=fields['soil_drainage']
        cleaned['calendar_zone']=fields['calendar_zone']
        reference=get_reference_data(cleaned['latitude'],cleaned['longitude'])
        return assess_all(cleaned,reference)
    except (InputError,ValueError) as exc:raise HTTPException(status_code=422,detail=str(exc))
    except ClimateDataError as exc:raise HTTPException(status_code=503,detail=str(exc))

app.mount('/assistant', chatbot_app, name='assistant')

@app.get('/')
def home():return FileResponse(APP_ROOT/'frontend'/'index.html')

@app.get('/index.html')
def index():return FileResponse(APP_ROOT/'frontend'/'index.html')

@app.get('/PHOTO-CREDITS.md')
def photo_credits(): return FileResponse(APP_ROOT/'frontend'/'PHOTO-CREDITS.md', media_type='text/markdown')

@app.get('/dashboard.html')
def dashboard():return FileResponse(APP_ROOT/'frontend'/'dashboard.html')

app.mount('/dist',StaticFiles(directory=str(APP_ROOT/'frontend'/'dist')),name='dist')
