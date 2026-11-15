"""Screening-level crop ETc and transparent two-season rotation comparison.

Method: FAO-56 single crop coefficient; standard, well-watered ETc=Kc*ET0.
IMPORTANT: This is NOT site-calibrated irrigation scheduling, soil health quantification,
or weather forecasting. The 2025 NASA observations are used as an explicitly labeled
historical seasonal-analog template for proposed seasonal windows.
"""
import csv
import json
import math
import calendar
from datetime import date, timedelta
from pathlib import Path
from .config import (REFERENCE_YEAR, REFERENCE_DAYS, COORDINATE_PRECISION_DEG, WINTER_SOWING, SUMMER_SOWING,
                     MIN_FIRST_WINTER_YEAR, MAX_FIRST_WINTER_YEAR, CLOSE_WATER_DIFFERENCE_PCT, MAX_SUPPORTED_ABS_LATITUDE,
                     default_first_winter_year)
from .soil import awc_for_farm, soil_crop_screen, FAO_CH7, FAO_CH8
from .rotation import generate_sequences, RotationError

ROOT = Path(__file__).resolve().parents[1]
CROPS_DB = ROOT/'agrishift_decision'/'crops.json'
DAILY_ETO_CSV = ROOT/'outputs'/'fao_eto_2025'/'daily_eto.csv'
DAILY_CLIMATE_CSV = ROOT/'outputs'/'nile_delta_2025'/'daily_climate.csv'
SUMMARY_JSON = ROOT/'outputs'/'fao_eto_2025'/'annual_summary.json'
METADATA_JSON = ROOT/'outputs'/'nile_delta_2025'/'metadata.json'

class InputError(ValueError):
    pass


def _load_csv(path):
    with path.open(encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))


def load_reference_data():
    db = json.loads(CROPS_DB.read_text(encoding='utf-8'))
    meta = json.loads(METADATA_JSON.read_text(encoding='utf-8'))
    summary = json.loads(SUMMARY_JSON.read_text(encoding='utf-8'))
    eto = _load_csv(DAILY_ETO_CSV)
    climate = _load_csv(DAILY_CLIMATE_CSV)
    if len(eto)!=REFERENCE_DAYS or len(climate)!=REFERENCE_DAYS: raise RuntimeError(f'Reference climate data must have exactly {REFERENCE_DAYS} rows for {REFERENCE_YEAR}')
    if [x['date'] for x in eto] != [x['date'] for x in climate]: raise RuntimeError('ET0 and climate dates are not aligned')
    if eto[0]['date']!=f'{REFERENCE_YEAR}-01-01' or eto[-1]['date']!=f'{REFERENCE_YEAR}-12-31':raise RuntimeError('Unexpected climate reference year')
    if meta['data_status']!='LIVE_NASA_API' or not summary['days']==REFERENCE_DAYS:raise RuntimeError('NASA provenance or ET0 summary missing')
    return db,meta,summary,eto,climate


def crop_coefficient(crop,day_index):
    """FAO-56 schematic curve: initial hold, linear development, mid hold, linear late decline."""
    n0,n1,n2,n3=map(int,crop['stages_days'])
    total=n0+n1+n2+n3
    if day_index<0 or day_index>=total: raise InputError(f'Growth day outside crop season: {day_index}')
    ki,km,ke=[crop[k] for k in ('kc_initial','kc_mid','kc_end')]
    if day_index<n0:return ki
    if day_index<n0+n1:return ki+(km-ki)*((day_index-n0+1)/n1)
    if day_index<n0+n1+n2:return km
    return km+(ke-km)*((day_index-(n0+n1+n2)+1)/n3)


def season_start(crop,anchor_year=2026):
    """Illustrative farm-planning sowing dates, NOT a recommended crop calendar."""
    # anchor_year is the calendar year of the winter sowing; summer sowing falls in the next year.
    if 'sowing_month' in crop and 'sowing_day' in crop:
        return date(anchor_year+(1 if crop['season']=='summer' else 0),crop['sowing_month'],crop['sowing_day'])
    return date(anchor_year,*WINTER_SOWING) if crop['season']=='winter' else date(anchor_year+1,*SUMMER_SOWING)


def _analog_date(d):
    """Use the reference year's day-of-month observations as an analogue, NEVER as a future forecast."""
    if d.month==2 and d.day==29 and not calendar.isleap(REFERENCE_YEAR): return f'{REFERENCE_YEAR}-02-28'
    return f'{REFERENCE_YEAR}-{d.month:02d}-{d.day:02d}'


def calculate_crop(crop_id, db, climate_lookup, eto_lookup, area_ha, efficiency, anchor_year=2026):
    crop=db['crops'][crop_id]; start=season_start(crop,anchor_year)
    days=sum(crop['stages_days'])
    rows=[]
    for i in range(days):
        d=start+timedelta(days=i)
        key=_analog_date(d)
        if key not in eto_lookup:raise RuntimeError('Missing ET0 analogue day: '+key)
        eto=float(eto_lookup[key]['eto_mm_day'])
        rain=float(climate_lookup[key]['PRECTOTCORR'])
        kc=crop_coefficient(crop,i)
        etc=eto*kc
        rows.append({'date':d.isoformat(),'reference_2025_date':key,'growth_day':i+1,
                     'kc':round(kc,5),'eto_mm_day':round(eto,5),
                     'etc_mm_day':round(etc,5),'reference_rainfall_mm_day':round(rain,4)})
    etc_total=sum(r['etc_mm_day'] for r in rows)
    # Flooded paddy demands extra establishment, percolation and standing-water management.
    # No invented whole-field irrigation amount: ETc is quantified but gross estimate is unknown.
    paddy_unknown = crop_id == 'rice'
    gross_mm=None if paddy_unknown else etc_total/efficiency
    return {'id':crop_id,'name':crop['name'],'family':crop['family'],'season':crop['season'],
            'planting_date':start.isoformat(),'harvest_estimated_date':(start+timedelta(days=days-1)).isoformat(),
            'growth_days':days,'crop_et_mm':round(etc_total,2),
            'gross_planning_proxy_mm':round(gross_mm,2) if gross_mm is not None else None,
            'gross_planning_proxy_m3':round(gross_mm*10*area_ha,2) if gross_mm is not None else None,
            'water_scope':'ETc only; paddy additional water not estimated' if paddy_unknown else 'ETc/efficiency planning proxy; rainfall not credited',
            'reference_rainfall_mm':round(sum(r['reference_rainfall_mm_day'] for r in rows),2),
            'kc_stages':{'initial':crop['kc_initial'],'mid':crop['kc_mid'],'end':crop['kc_end']},
            'coefficient_reference':crop['kc_basis'],'stage_duration_reference':crop['duration_basis'],
            'daily':rows}


def validate_inputs(req):
    if not isinstance(req,dict):raise InputError('Input must be a JSON object')
    raw_numbers=[req.get('area_ha',1.0),req.get('water_budget_m3',14500),req.get('irrigation_efficiency',0.75)]
    if any(isinstance(v,bool) for v in raw_numbers):raise InputError('Area, budget, efficiency must be numeric')  # float(True) would silently be 1.0
    try:
        area,water,efficiency=(float(v) for v in raw_numbers)
    except (TypeError,ValueError):raise InputError('Area, budget, efficiency must be numeric')
    if not all(math.isfinite(v) for v in [area,water,efficiency]):raise InputError('All numbers must be finite')
    if not 0.01<=area<=10000:raise InputError('Area must be between 0.01 and 10,000 ha')
    if not 0<=water<=1e9:raise InputError('Water budget must be between 0 and 1,000,000,000 m3')
    if not 0.35<=efficiency<=1:raise InputError('Efficiency must be between 0.35 and 1.00')
    prior=str(req.get('previous_crop','wheat'))
    if prior!='unknown' and prior not in json.loads(CROPS_DB.read_text(encoding='utf-8'))['crops']:raise InputError('Invalid previous crop')
    priority=str(req.get('priority','balanced'))
    if priority not in ('balanced','water','diversity'):raise InputError('Invalid priority')
    soil=str(req.get('soil_type','unknown'))
    if soil not in ('unknown','clay','loam','sand'):raise InputError('Invalid soil type')
    # Soil observations are optional. Empty strings are treated as not supplied.
    optional_soil={}
    for key,hi in [('soil_awc_mm_per_m',350),('soil_ece_ds_m',50),('soil_ph',14)]:
        value=req.get(key)
        if value is None or value=='':
            optional_soil[key]=None
        else:
            if isinstance(value,bool):raise InputError(f'{key} must be numeric')
            try: number=float(value)
            except (TypeError,ValueError): raise InputError(f'{key} must be numeric')
            lo=20 if key=='soil_awc_mm_per_m' else 0
            if not math.isfinite(number) or not lo<=number<=hi:
                raise InputError(f'{key} must be between {lo} and {hi}')
            optional_soil[key]=number
    from .location_data import normalize_coordinates
    try: latitude,longitude=normalize_coordinates(req.get('latitude',30.5),req.get('longitude',31.5))
    except ValueError as exc:raise InputError(str(exc)) from exc
    if abs(latitude)>MAX_SUPPORTED_ABS_LATITUDE:
        raise InputError(f'Latitude must be between -{MAX_SUPPORTED_ABS_LATITUDE:g} and {MAX_SUPPORTED_ABS_LATITUDE:g} degrees: closer to the poles the sun does not rise '
                         'for part of the year, so the FAO-56 daily ET0 method used here does not apply.')
    seasons=req.get('planning_seasons', 2)
    if type(seasons) is not int or seasons not in (2, 4, 6):
        raise InputError('planning_seasons must be 2, 4, or 6')
    allowed=req.get('allowed_crops')
    if allowed is not None:
        if not isinstance(allowed,list) or not allowed or len(allowed)>12 or any(not isinstance(x,str) for x in allowed):
            raise InputError('allowed_crops must be a nonempty list of supported crop IDs')
    strict=req.get('strict_family_rotation',False)
    if type(strict) is not bool:
        raise InputError('strict_family_rotation must be true or false')
    first_year=req.get('first_winter_year')
    if first_year is None or first_year=='':
        first_year=default_first_winter_year()
    elif type(first_year) is not int or not MIN_FIRST_WINTER_YEAR<=first_year<=MAX_FIRST_WINTER_YEAR:
        raise InputError(f'first_winter_year must be a whole year from {MIN_FIRST_WINTER_YEAR} to {MAX_FIRST_WINTER_YEAR}')
    max_results=req.get('max_results',12)
    if type(max_results) is not int or not 1<=max_results<=64:
        raise InputError('max_results must be an integer from 1 to 64')
    return dict(planning_seasons=seasons, first_winter_year=first_year, allowed_crops=allowed,
                strict_family_rotation=strict, max_results=max_results,
                area_ha=area,water_budget_m3=water,irrigation_efficiency=efficiency,
                previous_crop=prior,priority=priority,soil_type=soil,latitude=latitude,longitude=longitude,**optional_soil)


def validate_request(req):
    """Everything that can be checked WITHOUT climate data: inputs and crop-pool feasibility.

    The API calls this first, so an invalid request is refused before any NASA download
    or cache file is created.
    """
    inp=validate_inputs(req)
    db=json.loads(CROPS_DB.read_text(encoding='utf-8'))
    selected=inp['allowed_crops'] if inp['allowed_crops'] is not None else ['wheat','faba','maize','sunflower']
    try:
        generated=generate_sequences(db['crops'],inp['planning_seasons'],selected,inp['previous_crop'],
                                     inp['strict_family_rotation'],first_winter_year=inp['first_winter_year'])
    except RotationError as exc:
        raise InputError(str(exc)) from exc
    if not generated['sequences']:
        raise InputError('No crop sequences fit the strict family rule. Allow adjacent families or select more crops.')
    return inp


def summarize_climate(meta, summary, climate):
    avgtemp=sum(float(r['T2M']) for r in climate)/len(climate)
    rain=sum(float(r['PRECTOTCORR']) for r in climate)
    return {'year':REFERENCE_YEAR,'latitude':meta['request']['latitude'],'longitude':meta['request']['longitude'],
            'average_air_temperature_c':round(avgtemp,2),'annual_rain_mm':round(rain,2),
            'annual_reference_et0_mm':summary['eto_total_mm'],
            'daily_mean_reference_et0_mm':summary['eto_mean_mm_day'],
            'source':'NASA POWER daily point API, processed with FAO-56',
            'time_standard':meta['request']['time_standard'],
            # Pilot data were computed at 0 m (an assumption); live points use NASA's returned elevation.
            'elevation_m':summary.get('elevation_m',summary.get('elevation_assumption_m',0.0)),
            'elevation_source':summary.get('elevation_source','assumed_zero')}


def analyze(req, reference_data=None):
    inp=validate_inputs(req)
    db,meta,summary,eto,climate=reference_data if reference_data is not None else load_reference_data()
    cl={r['date']:r for r in climate}; el={r['date']:r for r in eto}
    # Expand supported crop catalogue into all user-selected alternating seasonal slots.
    selected=inp['allowed_crops'] if inp['allowed_crops'] is not None else ['wheat','faba','maize','sunflower']
    try:
        generated=generate_sequences(db['crops'], inp['planning_seasons'], selected,
                                     inp['previous_crop'], inp['strict_family_rotation'],
                                     first_winter_year=inp['first_winter_year'])
    except RotationError as exc:
        raise InputError(str(exc)) from exc
    if not generated['sequences']:
        raise InputError('No crop sequences fit the strict family rule. Allow adjacent families or select more crops.')
    # Calculate each specific crop/window only once (years can differ in leap handling).
    crop_instances={}
    for slot in generated['slots']:
        for cid in generated['choices_by_season'][slot['season']]:
            crop_instances[(cid,slot['anchor_year'])]=calculate_crop(
                cid,db,cl,el,inp['area_ha'],inp['irrigation_efficiency'],anchor_year=slot['anchor_year'])
    # One representative instance per crop (its first planned window) for the soil screening.
    crops={}
    for slot in generated['slots']:
        for cid in generated['choices_by_season'][slot['season']]:
            crops.setdefault(cid,crop_instances[(cid,slot['anchor_year'])])
    # Soil is a separate scientific screening layer, not an uncalibrated ETc multiplier.
    awc=awc_for_farm(inp['soil_type'], inp['soil_awc_mm_per_m'])
    crop_soil={}
    for cid,crop in crops.items():
        start_mid=sum(db['crops'][cid]['stages_days'][:2])
        mid_days=db['crops'][cid]['stages_days'][2]
        mid_values=[r['etc_mm_day'] for r in crop['daily'][start_mid:start_mid+mid_days]]
        crop_soil[cid]=soil_crop_screen(cid, awc, inp['soil_ece_ds_m'], sum(mid_values)/len(mid_values))
    prev=inp['previous_crop']
    prev_family=db['crops'][prev]['family'] if prev!='unknown' else None
    # Precompute water of every candidate; score relative to this actual search space.
    totals=[]
    for seq in generated['sequences']:
        total=sum(crop_instances[(cid, slot['anchor_year'])]['gross_planning_proxy_m3']
                  for cid,slot in zip(seq,generated['slots']))
        totals.append(round(total,2))
    amin,amax=min(totals),max(totals)
    water_spread_pct=round(100*(amax-amin)/amin,1) if amin>0 else 0.0
    water_small=len(totals)>1 and water_spread_pct<CLOSE_WATER_DIFFERENCE_PCT   # one plan = nothing to compare
    weights={'balanced':(0.55,0.45),'water':(0.8,0.2),'diversity':(0.25,0.75)}[inp['priority']]
    plans=[]
    for seq,total in zip(generated['sequences'],totals):
        families=[db['crops'][cid]['family'] for cid in seq]
        family_path=([prev_family] if prev_family is not None else [])+families
        edge_count=len(family_path)-1
        contrasts=sum(a!=b for a,b in zip(family_path,family_path[1:]))
        diversity=round(100*contrasts/edge_count,1) if edge_count else 0
        water_score=round(100*(amax-total)/(amax-amin),1) if amax>amin else 100.0
        score=round(weights[0]*water_score+weights[1]*diversity,1)
        feasible=total<=inp['water_budget_m3']
        instances=[crop_instances[(cid,slot['anchor_year'])] for cid,slot in zip(seq,generated['slots'])]
        salts=[crop_soil[cid]['salinity_flag'] for cid in seq]
        salt_count=salts.count('above_published_threshold')
        unknown_salt_count=salts.count('no_numeric_threshold_in_fao56_table23')  # unknown is NOT safe: counted on its own
        signals=[]
        if any(db['crops'][cid]['family']=='fabaceae' for cid in seq):
            signals.append('Includes a legume; possible rotation benefit, NOT measured soil nitrogen gain.')
        if contrasts<edge_count:
            signals.append(f'{edge_count-contrasts} adjacent crop-family repeat(s) including previous crop when known; consider pest history. This is a warning, not automatic disease prediction.')
        if salt_count:
            signals.append(f'Farmer-supplied soil ECe exceeds a FAO-56 screening threshold in {salt_count} planted season(s).')
        if inp['soil_ece_ds_m'] is not None and any(v=='no_numeric_threshold_in_fao56_table23' for v in salts):
            signals.append('At least one crop has no numeric FAO-56 Table 23 ECe threshold; its salinity safety is unknown.')
        signals.append('Historical 2025 seasonal analogue used for every year; no weather forecast or yield prediction.')
        crop_out=[]
        for cid,slot,instance in zip(seq,generated['slots'],instances):
            crop_out.append({'id':cid, 'name':instance['name'],'family':instance['family'],
                             'season':slot['season'],'slot':slot['slot'],'season_year':slot['year'],
                             'planting_date':instance['planting_date'],
                             'harvest_estimated_date':instance['harvest_estimated_date'],
                             'crop_et_mm':instance['crop_et_mm'],
                             'gross_planning_proxy_m3':instance['gross_planning_proxy_m3']})
        plans.append({'id':'-'.join(seq),
            'winter_crop':seq[0], 'summer_crop':seq[1], 'sequence':list(seq), 'crops':crop_out,
            'soil_screening':{'winter':crop_soil[seq[0]],'summer':crop_soil[seq[1]],  # first two seasons (kept for older clients)
                              'by_season':[{'slot':slot['slot'],'season':slot['season'],'crop_id':cid,
                                            'salinity_flag':crop_soil[cid]['salinity_flag'],
                                            'total_available_water_taw_mm':crop_soil[cid]['total_available_water_taw_mm'],
                                            'readily_available_water_raw_mm':crop_soil[cid]['readily_available_water_raw_mm']}
                                           for cid,slot in zip(seq,generated['slots'])],
                              'salinity_concern_count':salt_count,
                              'salinity_unknown_count':unknown_salt_count,
                              'assessment_status':'provisional_crop_and_soil_screening'},
            'water_proxy_m3':total,'budget_difference_m3':round(inp['water_budget_m3']-total,2),
            'water_vs_lowest_pct':round(100*(total-amin)/amin,1) if amin>0 else 0.0,
            'within_total_budget':feasible,'relative_water_score':water_score,
            'diversity_heuristic':diversity,'comparison_score':score,
            'comparison_weights':{'water':weights[0],'diversity':weights[1]},
            'signals':signals})
    ece_given=inp['soil_ece_ds_m'] is not None
    # Known exceedances first, then crops whose threshold is unknown (never treated as safe), then the score.
    plans.sort(key=lambda p:(not p['within_total_budget'],
             p['soil_screening']['salinity_concern_count'] if ece_given else 0,
             p['soil_screening']['salinity_unknown_count'] if ece_given else 0,
             -p['comparison_score'],p['water_proxy_m3'],p['id']))
    for ix,p in enumerate(plans):p['rank']=ix+1
    total_feasible=sum(p['within_total_budget'] for p in plans)
    # Returning a capped shortlist is not the same as only generating a few plans.
    plan_count=len(plans)
    plans=plans[:inp['max_results']]
    caveats=[
      'Screening prototype only; not a planting, irrigation, fertilizer, or yield recommendation.',
      'All proposed future crop windows reuse 2025 NASA seasonal observations as a historical analogue; NOT forecasts or a multi-year climatology.',
      'FAO-56 Kc and stage durations are published regional examples; values, crop calendar and growing season need local agronomist calibration.',
      'Gross water proxy = sum(Kc*ET0)*area/irrigation-efficiency, with no effective-rainfall credit, soil water balance, salinity, or irrigation scheduling.',
      'Water budget is the total for ALL chosen seasons; per-season water constraints and daily supplies have not been modeled.',
      'Soil texture informs indicative FAO-56 TAW and RAW only; not an observed soil moisture or validated suitability score.',
      'Optional farmer-supplied AWC and saturation-extract soil ECe produce field-specific screening flags; measurements were not independently verified.',
      'Salinity comparisons use FAO-56 Table 23 thresholds where available; unknown thresholds are never treated as safe, and no yield-loss numbers are predicted.',
      'When ECe is supplied, plans are ordered by documented threshold exceedances first, then by crops with NO published threshold (unknown, never safe), then by the water/diversity score; this is not an agronomist-approved ranking.',
      'Diversity score is an explicit family-change heuristic; strict family-change screening is optional and may exclude legitimate local rotations. No measured soil-health or yield claims.',
      'NASA POWER spatial grids are not on-farm sensors. On-demand locations use live 2025 NASA POWER records or the exact-coordinate cached response.',
      'Crop water examples now cover 12 FAO-56 profiles, but paddy rice gross irrigation and multi-cut alfalfa season water remain unquantified; these two are excluded from rotation ranking.',
      'Calendar-overlapping crop sequences are excluded using FAO-56 regional examples and a stated day-of-month convention; calendars are not validated for a particular site.',
      'Full crop-suitability scores require species-matched EcoCrop thresholds, soil pH/drainage and calibrated local calendars; unavailable indicators are UNKNOWN.',
      'No ML model trained, validated or used. SMAP, HLS and GAEZ are not yet integrated.'
    ]
    from .location_data import monthly_eto
    winter_day=date(inp['first_winter_year'],*WINTER_SOWING); summer_day=date(inp['first_winter_year']+1,*SUMMER_SOWING)
    ranking_note=(f'The {plan_count} candidate plans differ by only {water_spread_pct}% in modeled water. The 0-100 relative water score stretches '
                  'that small gap, so read the percent differences instead of the score.') if water_small else None
    result={'project':'AgriShift','status':'RESEARCH_PROTOTYPE','model':'FAO56_ETc_plus_explainable_rotation_screening',
            'climate':summarize_climate(meta,summary,climate),'inputs':inp,'plans':plans,
            'rotation_generation':{'planning_seasons':inp['planning_seasons'],
              'season_slots':generated['slots'],'crop_pool':generated['choices_by_season'],
              'generated_before_rules':generated['generated_count'],
              'excluded_by_family_rule':generated['excluded_family_rule_count'],
              'excluded_by_calendar_overlap':generated.get('excluded_calendar_overlap_count',0),
              'valid_candidate_count':plan_count,'within_total_budget_count':total_feasible,
              'returned_plan_count':len(plans),'results_truncated':plan_count>len(plans),
              'water_spread_pct':water_spread_pct,'water_differences_are_small':water_small,'ranking_note':ranking_note,
              'family_rule':'strict if requested; otherwise advisory',
              'water_budget_scope':'total_across_all_planning_seasons'},
            'soil_summary':{'soil_type':inp['soil_type'],'awc':awc,'ece_ds_m':inp['soil_ece_ds_m'],
                            'crop_screening':crop_soil,'source_links':{'fao56_soil':FAO_CH7,'fao56_roots_and_salinity':FAO_CH8}},
            'method':{'crop_water':'ETc=Kc*ET0 (FAO-56)',
                      'gross_water':'gross planning proxy = ETc/assumed efficiency (no rainfall credit)',
                      'relative_score':'0-100 comparative weighted water and family-diversity heuristic; NOT probability or validated suitability',
                      'rotation_search':'Enumerate all alternating winter/summer sequences from selected crops, optional adjacent-family pruning, then rank and return a capped shortlist',
                      'soil_water':'FAO-56 TAW=AWC*root_depth, RAW=p*TAW; storage/indicative dry-down only',
                      'soil_salinity':'FAO-56 Table 23 ECe thresholds only where published; never a yield prediction',
                      'reference_year':REFERENCE_YEAR,'future_crop_years':sorted({s['year'] for s in generated['slots']}),
                      'crop_windows':{'winter':f"{winter_day.strftime('%b')} {winter_day.day}, {winter_day.year} (illustrative)",
                                      'summer':f"{summer_day.strftime('%b')} {summer_day.day}, {summer_day.year} (illustrative)"},
                      'crop_sources':db['references']},
            'limitations':caveats}
    result['climate']['monthly_eto']=monthly_eto(eto)
    result['climate']['coordinate_precision_deg']=COORDINATE_PRECISION_DEG
    result['climate']['history_only']=True
    return result
