"""Evidence-traceable 12-crop environmental screening, NOT a suitability certificate.

Sources: user-provided historical FAO EcoCrop CSV (exact species row IDs), FAO Egypt
crop-calendar XLSX (exact sheet row references), NASA POWER daily data, FAO-56.
Missing field soil measurements and unverified local crop schedules remain unknown.
No arbitrary global % success / suitability score is generated.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from .engine import calculate_crop, summarize_climate
from .soil import awc_for_farm, soil_crop_screen
from .config import REFERENCE_YEAR
from .calendar_evidence import get_calendar, validate_zone

PROFILE_PATH=Path(__file__).with_name('ecocrop_profiles.json')

@lru_cache(maxsize=1)
def _profiles():
    return json.loads(PROFILE_PATH.read_text(encoding='utf-8'))

def _reading(row,key):
    try:
        n=float(row[key]);return n if -999<n<99999 else None
    except (KeyError,TypeError,ValueError):return None

def _range_diagnostic(value, absolute, optimal, source, unit, dimension):
    result={'status':'unknown','observed':value,'absolute_bounds':absolute,'optimal_bounds':optimal,
            'source':source,'unit':unit,'dimension':dimension}
    if value is None or not absolute or any(n is None for n in absolute):return result
    lo,hi=absolute
    result['status']='outside_reference_range' if value<lo or value>hi else 'within_reference_range'
    if optimal and all(n is not None for n in optimal) and lo<=value<=hi:
        result['band']='within_published_optimal_range' if optimal[0]<=value<=optimal[1] else 'within_absolute_outside_optimal'
    else: result['band']='outside_absolute' if result['status']=='outside_reference_range' else 'optimal_range_unavailable'
    result['observed']=round(value,2)
    result['caution']='Species-level historical ecological envelope, not an agronomic guarantee or probability.'
    return result

def _soil_texture(value,ec):
    src=ec.get('source_url')
    diag={'status':'unknown','observed':value,'eco_optimal':ec.get('soil_texture_optimal'),
          'eco_absolute':ec.get('soil_texture_absolute'),'source':src,'caution':'Texture categories are approximate (clay=heavy, loam=medium, sand=light), not a soil laboratory diagnosis.'}
    category={'clay':'heavy','loam':'medium','sand':'light'}.get(value)
    if not category or not ec.get('soil_texture_absolute'):return diag
    absolute=str(ec['soil_texture_absolute']).lower();optimal=str(ec.get('soil_texture_optimal') or '').lower()
    diag['status']='within_reference_category' if category in absolute else 'outside_reference_category'
    diag['optimal_band']=category in optimal
    return diag

def _drainage(value,ec):
    diag={'status':'unknown','observed':value,'eco_optimal':ec.get('soil_drainage_optimal'),
          'eco_absolute':ec.get('soil_drainage_absolute'),'source':ec.get('source_url'),
          'caution':'Descriptive EcoCrop classes are not measured hydraulic conductivity.'}
    if value not in ('well','moderate','poor') or not ec.get('soil_drainage_absolute'):return diag
    absolute=str(ec['soil_drainage_absolute']).lower()
    optimal=str(ec.get('soil_drainage_optimal') or '').lower()
    variants={'well':('well',),'moderate':('moderate','medium'),'poor':('poor','imperfect')}
    diag['status']='within_reference_category' if any(v in absolute for v in variants[value]) else 'outside_reference_category'
    diag['optimal_band']=any(v in optimal for v in variants[value])
    return diag

def assess_all(request,reference_data):
    db,meta,summary,eto,climate=reference_data
    inp=request; el={r['date']:r for r in eto};cl={r['date']:r for r in climate}
    profiles=_profiles()
    awc=awc_for_farm(inp.get('soil_type','unknown'),inp.get('soil_awc_mm_per_m'))
    zone=validate_zone(inp.get('calendar_zone','unknown'))
    annual_rain=[_reading(row,'PRECTOTCORR') for row in climate]
    annual_rain_mm=round(sum(annual_rain),2) if all(x is not None for x in annual_rain) else None
    results=[]
    first_year=inp['first_winter_year']
    for cid,crop in db['crops'].items():
        cal=calculate_crop(cid,db,cl,el,inp['area_ha'],inp['irrigation_efficiency'],first_year)
        n0,n1,n2,n3=crop['stages_days']
        mids=[r['etc_mm_day'] for r in cal['daily'][n0+n1:n0+n1+n2]]
        soil=soil_crop_screen(cid,awc,inp.get('soil_ece_ds_m'),sum(mids)/len(mids))
        ece=soil['salinity_flag']
        salinity={'status':('unknown' if ece in ('not_tested','no_numeric_threshold_in_fao56_table23') else
                             'caution' if ece in ('above_published_threshold','within_published_threshold_range_uncertain') else 'within_reference_threshold'),
            'value_ds_m':inp.get('soil_ece_ds_m'),'reference_threshold_ds_m':soil['fao56_ece_threshold_ds_m'],
            'reference_threshold_range_ds_m':soil['fao56_ece_threshold_range_ds_m'],'flag':ece,
            'reference':'FAO-56 Chapter 8 Table 23; saturation-extract ECe ONLY, not irrigation-water EC'}
        temps=[];daily_min=[];daily_max=[];rain_values=[]
        for day in cal['daily']:
            row=cl.get(day['reference_2025_date'],{})
            for arr,key in ((temps,'T2M'),(daily_min,'T2M_MIN'),(daily_max,'T2M_MAX'),(rain_values,'PRECTOTCORR')):
                val=_reading(row,key)
                if val is not None:arr.append(val)
        climate_stats={'reference_year':REFERENCE_YEAR,
            'mean_temp_c':round(sum(temps)/len(temps),2) if len(temps)==len(cal['daily']) else None,
            'coldest_daily_min_c':round(min(daily_min),2) if len(daily_min)==len(cal['daily']) else None,
            'warmest_daily_max_c':round(max(daily_max),2) if len(daily_max)==len(cal['daily']) else None,
            'historical_rain_mm':round(sum(rain_values),2) if len(rain_values)==len(cal['daily']) else None,
            'historical_annual_rain_mm':annual_rain_mm,
            'rain_days_with_data':len(rain_values),'day_count':len(cal['daily']),
            'source':'NASA POWER 2025 daily data at requested coordinates, matched to FAO example growing dates; NOT a forecast'}
        ec=profiles.get(cid,{})
        verified=bool(ec.get('source_url') and ec.get('species') and ec.get('source_row_id'))
        source=ec.get('source_url') if verified else None
        t=_range_diagnostic(climate_stats['mean_temp_c'],ec.get('temperature_c'),ec.get('temperature_optimal_c'),source,'°C','seasonal_mean_temperature')
        ph=_range_diagnostic(inp.get('soil_ph'),ec.get('soil_ph'),ec.get('soil_ph_optimal'),source,'pH','field_soil_ph')
        rain=_range_diagnostic(annual_rain_mm,ec.get('annual_rainfall_mm'),ec.get('annual_rainfall_optimal_mm'),source,'mm/year','annual_rainfall_rainfed_context')
        rain['irrigation_caveat']='Annual natural rainfall is a rainfed climate envelope, NOT a feasibility veto for irrigated farming; irrigation supply must be assessed separately.'
        texture=_soil_texture(inp.get('soil_type','unknown'),ec)
        drainage=_drainage(inp.get('soil_drainage','unknown'),ec)
        calendar=get_calendar(cid,zone)
        if calendar['entries']:
            lengths=[entry['growing_days_range'] for entry in calendar['entries'] if entry['growing_days_range']]
            in_range=any(lo<=cal['growth_days']<=hi for lo,hi in lengths)
            calendar['fao56_growth_duration_comparison']='within_at_least_one_local_range' if in_range else 'outside_available_local_ranges' if lengths else 'unknown_no_numeric_duration'
            calendar['modeled_planting_date']=cal['planting_date']
            calendar['model_uses_regional_calendar']='No. The ETc/rotation model still uses explicit FAO-56 example sowing convention; treat local calendar as an independent check.'
        signals=(t,ph,salinity,texture,drainage)
        dimension_states={
           'climate_temperature':t['status'],'soil_ph':ph['status'],'soil_salinity':salinity['status'],
           'soil_texture':texture['status'],'soil_drainage':drainage['status'],
           'regional_calendar':calendar['status']}
        known=sum(s!='unknown' and s!='region_not_selected' and s!='no_matching_regional_records' for s in dimension_states.values())
        caution=any(x['status'] in ('caution','outside_reference_range','outside_reference_category') for x in signals) or calendar.get('fao56_growth_duration_comparison')=='outside_available_local_ranges'
        missing=[key for key,v in dimension_states.items() if v in ('unknown','region_not_selected','no_matching_regional_records')]
        results.append({'id':cid,'name':crop['name'],'family':crop['family'],'season':crop['season'],
            'quantitative_et':{'crop_et_mm':cal['crop_et_mm'],'growth_days':cal['growth_days'],
               'gross_planning_proxy_m3':cal['gross_planning_proxy_m3'],
               'gross_planning_proxy_mm':cal['gross_planning_proxy_mm'],'water_scope':cal['water_scope'],
               'reference_rainfall_mm':cal['reference_rainfall_mm'],'planting_date':cal['planting_date'],
               'harvest_estimated_date':cal['harvest_estimated_date'],'kc_stages':cal['kc_stages'],
               'coefficient_reference':crop['kc_basis'],'growth_stage_reference':crop['duration_basis']},
            'suitability':{
               'status':'partial_caution' if caution else 'partial_evidence' if known else 'insufficient_data',
               'confidence':'partial_evidence_no_field_validated_global_verdict',
               'assessed_dimensions':known,'possible_dimensions':6,
               'climate_temperature':t,'soil_ph':ph,'soil_salinity':salinity,
               'climate_rainfall_rainfed_reference':rain,
               'soil_texture':texture,'soil_drainage':drainage,
               'regional_calendar':calendar,'climate_observations':climate_stats,
               'ecocrop_species':ec.get('species'),'ecocrop_taxon_note':ec.get('taxon_note'),
               'ecocrop_row_id':ec.get('source_row_id'),'ecocrop_database_snapshot':'Historical FAO ECOCROP mirrored by OpenCLIM; user supplied',
               'soil_water_capacity':{'taw_mm':soil['total_available_water_taw_mm'],
                         'raw_mm':soil['readily_available_water_raw_mm'],
                         'status':'estimated_storage_not_suitability' if soil['total_available_water_taw_mm'] is not None else 'unknown'},
               'crop_calendar':calendar['status'],'overall_suitability_score':None,
               'missing_evidence':missing+(['field_specific_agronomic_validation'] if True else [])},
            'rotation_eligible':bool(crop.get('rotation_eligible',True)),
            'rotation_note':('Eligible for comparative hypothetical sequence only; regional sowing window and climate suitability must be checked separately.'
               if crop.get('rotation_eligible',True) else crop.get('model_scope')),
            'source_links':{'fao56_kc':'https://www.fao.org/4/x0490e/x0490e0b.htm',
                            'fao56_soil':'https://www.fao.org/4/x0490e/x0490e0e.htm',
                            'ecocrop_profile':source,
                            'ecocrop_row_id':ec.get('source_row_id'),'fao_crop_calendar':calendar['source_url']}})
    return {'project':'AgriShift','status':'SOURCED_12_CROP_ENVIRONMENTAL_SCREENING',
        'location':summarize_climate(meta,summary,climate),'source_year':REFERENCE_YEAR,
        'crop_count':len(results),'rotation_ready_count':sum(x['rotation_eligible'] for x in results),
        'crops':results,'calendar_zone':zone,'data_coverage':{'fao56_crop_et_count':len(results),
            'ecocrop_verified_profiles':sum(bool(x.get('source_url') and x.get('source_row_id') and x.get('species')) for x in profiles.values()),
            'regional_calendar_crop_count':sum(x['suitability']['regional_calendar']['status']=='regional_records_available' for x in results),
            'paddy_extra_water':'not_modeled','alfalfa_multi_cut':'not_modeled'},
        'limitations':[
          'NASA POWER 2025 historical observations (not forecast or multi-year climate normals).',
          'EcoCrop species-specific temperature, pH, rainfall, texture and drainage reference envelopes are historical, not measured yield or probability.',
          'EcoCrop optimal/absolute temperature categories are compared with mean temperatures over illustrative growth windows; extremes are descriptive, not a field suitability certification.',
          'ECOCROP annual rain reference is rainfed ecological context, NOT an irrigated-field viability veto.',
          'FAO Crop Calendar export covers Egypt only; without user-selected verified region, regional sowing dates remain unknown.',
          'Published regional sowing windows are displayed but do not replace FAO-56 illustrative dates in ETc or rotation calculation.',
          'Measuring soil pH, ECe and drainage is user responsibility; GPS does not infer these.',
          'Soil texture heavy/medium/light mapping is an approximate screening comparison.',
          'Cotton profile is G. barbadense only; other cotton species may differ. Sugar beet profile is species-level Beta vulgaris.',
          'Paddy rice ETc excludes ponding and deep percolation; total irrigation is unmodeled.',
          'Alfalfa example quantifies one cutting only, not a full perennial cutting cycle.',
          'Do not use as planting authorization or crop-yield prediction; independent local field validation is required.'
        ]}
