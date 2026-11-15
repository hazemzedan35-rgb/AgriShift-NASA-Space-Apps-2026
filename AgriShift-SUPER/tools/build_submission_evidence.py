"""Reproducibly import USER SUPPLIED EcoCrop and Egypt crop-calendar source files.

Run from project root: python tools/build_submission_evidence.py
The selected EcoPortCode IDs below are reviewed exact taxon matches from source, not fuzzy names.
Crop calendars are source records with provenance, not automatically valid for GPS coordinates.
"""
import csv, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'evidence'
SOURCE_ECO='https://github.com/OpenCLIM/ecocrop/blob/main/EcoCrop_DB.csv'
SOURCE_CAL='https://cropcalendar.apps.fao.org/'
ECO_IDS={
  'wheat':('2114','Triticum aestivum'),
  'faba':('2146','Vicia faba'),
  'maize':('2175','Zea mays'),
  'sunflower':('1191','Helianthus annuus'),
  'rice':('1574','Oryza sativa'),
  # Egyptian long-staple cotton is typically G. barbadense; this is a *specific
  # species reference*, NOT evidence about all cotton cultivars and farms.
  'cotton':('1158','Gossypium barbadense'),
  'potato':('1971','Solanum tuberosum'),
  'tomato':('1379','Lycopersicon esculentum'),
  'onion':('364','Allium cepa'),
  # Beta vulgaris profile is species-level, not sugar-beet cultivar specific.
  'sugarbeet':('514','Beta vulgaris'),
  'alfalfa':('1428','Medicago sativa'),
  'sorghum':('48747','Sorghum bicolor')
}
# Exact Egyptian export labels, distinguishing fresh broad beans from dry broad beans.
CAL_NAMES={
 'wheat':['Wheat, bread'], 'faba':['Bean, broad green'], 'maize':[],
 'sunflower':['Sunflower'], 'rice':['Rice'], 'cotton':[],
 'potato':['Potato'],'tomato':['Tomato'],'onion':['Onion'],
 'sugarbeet':['Beet, sugar'],'alfalfa':[],'sorghum':['Sorghum']
}

def val(r,k):
    x=(r.get(k) or '').strip()
    if x.lower() in ('','na','n/a','nan','null','none'):return None
    try: f=float(x)
    except ValueError:return None
    return f if f==f and abs(f)!=float('inf') else None

def bounds(r,a,b,low=-1000,high=100000):
    x,y=val(r,a),val(r,b)
    return [x,y] if x is not None and y is not None and low<=x<=y<=high else None

def build_ecocrop():
    with (DATA/'EcoCrop_DB.csv').open(newline='',encoding='latin-1') as f: rows=list(csv.DictReader(f))
    ids={r['EcoPortCode']:r for r in rows}
    out={}
    for cid,(code,name) in ECO_IDS.items():
        r=ids.get(code)
        if not r or r['ScientificName'].lower()!=name.lower():raise ValueError('Taxon mismatch '+cid)
        out[cid]={
          'species':name,'source_row_id':code,'source_url':SOURCE_ECO,
          'source_dataset':'User supplied EcoCrop_DB.csv, OpenCLIM mirror of historical FAO ECOCROP',
          'temperature_c':bounds(r,'TMIN','TMAX',-60,75),
          'temperature_optimal_c':bounds(r,'TOPMN','TOPMX',-60,75),
          'soil_ph':bounds(r,'PHMIN','PHMAX',0,14),
          'soil_ph_optimal':bounds(r,'PHOPMN','PHOPMX',0,14),
          'annual_rainfall_mm':bounds(r,'RMIN','RMAX',0,20000),
          'annual_rainfall_optimal_mm':bounds(r,'ROPMN','ROPMX',0,20000),
          'growth_days_range':bounds(r,'GMIN','GMAX',1,1000),
          'soil_texture_optimal':r.get('TEXT','').strip() or None,
          'soil_texture_absolute':r.get('TEXTR','').strip() or None,
          'soil_drainage_optimal':r.get('DRA','').strip() or None,
          'soil_drainage_absolute':r.get('DRAR','').strip() or None,
          'source_note':'Historical species envelope, NOT a global on-farm suitability probability. Requires cultivar, site soil measurements, management and calendar validation.',
          'taxon_note':(
             'Gossypium barbadense only; not all Gossypium cotton species. Confirm cultivated species.' if cid=='cotton' else
             'Beta vulgaris species, may cover non-sugar-beet types; verify cultivar-specific tolerances.' if cid=='sugarbeet' else
             'Source uses Lycopersicon esculentum, a synonym of Solanum lycopersicum.' if cid=='tomato' else
             'Species-level ecological envelope, not cultivar-specific.'
          )}
    path=ROOT/'agrishift_decision'/'ecocrop_profiles.json'
    path.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return out

# Capture all rows for selected 12 crops, with precise worksheet row for auditing.
def build_calendar():
    # Read cached extract created using artifact_tool from the uploaded workbook.
    cache=DATA/'crop_calendar_xlsx_extracted.json'
    if not cache.exists():raise FileNotFoundError('Run scripts/source_calendar_extract.py with artifact_tool first')
    raw=json.loads(cache.read_text(encoding='utf-8'))
    out=[]
    def num(x):
        if x in (None,''):return None
        try:
          v=int(str(x).strip())
          return v
        except (ValueError,TypeError):return None
    def datepart(day,month):
        d,m=num(day),num(month)
        if d is None or m is None or not 1<=m<=12 or not 1<=d<=31:return None
        # Date-window uncertainty is source-provided; no invented dates.
        import calendar
        if d>calendar.monthrange(2025,m)[1]:return None
        return {'day':d,'month':m}
    for ix,row in enumerate(raw['rows'],start=3):
        if len(row)<17 or row[0]!='Egypt':continue
        cid=next((cid for cid,names in CAL_NAMES.items() if row[1] in names),None)
        if not cid:continue
        period=str(row[11] or '').strip()
        pat=re.fullmatch(r'\s*(\d+)\s*(?:-\s*(\d+))?\s*',period)
        days=[int(pat.group(1)),int(pat.group(2) or pat.group(1))] if pat and str(row[12]).lower() in ('days','day') else None
        dates={
          'sow_early':datepart(row[4],row[5]),'sow_late':datepart(row[6],row[7]),
          'harvest_early':datepart(row[13],row[14]),'harvest_late':datepart(row[15],row[16])
        }
        out.append({
          'crop_id':cid,'reported_crop':row[1], 'country':'Egypt',
          'zone':str(row[2]).strip() if row[2] else None,
          'sowing_window':{'start':dates['sow_early'],'end':dates['sow_late']},
          'harvest_window':{'start':dates['harvest_early'],'end':dates['harvest_late']},
          'growing_days_range':days,'additional_information':str(row[3])[:300] if row[3] else None,
          'source_file':'Crop_Calendar_Data_All.xlsx','sheet':'Crop Calendar Data',
          'source_excel_row':ix,'source_url':SOURCE_CAL,
          'source_note':'Historical regional calendar; does not verify farm location or current cultivar.'
        })
    zones=sorted(set(r['zone'] for r in out if r['zone']))
    payload={'source_url':SOURCE_CAL,'source_workbook':'Crop_Calendar_Data_All.xlsx',
            'country':'Egypt','records':out,'zones':zones,
            'missing_crop_calendar_records':[c for c in ECO_IDS if not any(r['crop_id']==c for r in out)],
            'notes':['Some rows lack AgroEcological Zone; these are NOT mapped to any location automatically.',
                     'Field corn/maize is NOT the same as Corn, sweet and will not be silently substituted.',
                     'Faba bean (fresh harvest) is mapped to Bean, broad green, not the dry-seed crop.',
                     'No automated GIS zoning or country-wide calendar inference. Farmer must select a known zone.']}
    (ROOT/'agrishift_decision'/'egypt_crop_calendar.json').write_text(json.dumps(payload,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    return payload

if __name__=='__main__':
    p=build_ecocrop();r=build_calendar()
    print('Imported',len(p),'EcoCrop species',len(r['records']),'calendar crop entries across',len(r['zones']),'named zones')
    print('Calendar missing',r['missing_crop_calendar_records'])
