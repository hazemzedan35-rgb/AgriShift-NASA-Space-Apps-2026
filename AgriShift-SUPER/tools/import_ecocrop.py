"""Safely stage verified FAO EcoCrop numeric envelopes from a user-provided CSV.

1) python tools/import_ecocrop.py EcoCrop_DB.csv --list-candidates
2) Review scientific names and species ECOport IDs in the output.
3) Create ecocrop-selection.json of {"wheat":"<exact ECOport ID>", ...}.
4) python tools/import_ecocrop.py EcoCrop_DB.csv --selection ecocrop-selection.json

No species are guessed: the crop ID mapping MUST be user-verified.
Temperature and pH columns must have valid numerical ranges and source identifiers.
"""
import argparse,csv,json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'agrishift_decision'/'ecocrop_profiles.json'
SOURCE='https://github.com/OpenCLIM/ecocrop/blob/main/EcoCrop_DB.csv'
CANDIDATES={
 'wheat':['triticum aestivum'],'faba':['vicia faba'],'maize':['zea mays'],
 'sunflower':['helianthus annuus'],'rice':['oryza sativa'],
 'cotton':['gossypium hirsutum'],'potato':['solanum tuberosum'],
 'tomato':['solanum lycopersicum','lycopersicon esculentum'],
 'onion':['allium cepa'],'sugarbeet':['beta vulgaris'],
 'alfalfa':['medicago sativa'],'sorghum':['sorghum bicolor']}

def clean(s): return re.sub(r'[^a-z0-9]','',str(s or '').strip().lower())
def cell(row,*aliases):
    normalized={clean(k):v for k,v in row.items()}
    return next((str(normalized[clean(a)]).strip() for a in aliases if normalized.get(clean(a)) not in ('',None,'NA','nan')),None)
def num(row,*keys):
    s=cell(row,*keys)
    try:return float(s) if s else None
    except (TypeError, ValueError):return None

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv',type=Path);p.add_argument('--selection',type=Path)
    p.add_argument('--list-candidates',action='store_true')
    args=p.parse_args()
    if not args.selection and not args.list_candidates:p.error('Use --list-candidates, then --selection (never auto-match species)')
    with args.csv.open(newline='',encoding='utf-8-sig',errors='replace') as fp:
        rows=list(csv.DictReader(fp))
    if not rows:raise SystemExit('No rows found; verify CSV encoding and delimiter')
    keys=list(rows[0]);print('Columns:', ', '.join(keys[:80]))
    if args.list_candidates:
        for cid,species in CANDIDATES.items():
            found=[]
            for r in rows:
                name=cell(r,'ScientificName','Scientific_Name','SCINAME','SPECIES','name')
                code=cell(r,'ECOportcode','EcoPortCode','cropid','ID')
                if name and name.strip().lower() in species:
                    found.append((code,name))
            print(f'{cid}: {found or "NO EXACT MATCH; manual species verification needed"}')
        return
    mapping=json.loads(args.selection.read_text(encoding='utf-8'))
    if not isinstance(mapping,dict):raise SystemExit('Selection must be JSON object mapping crop IDs to original EcoPortCode IDs')
    profiles={}
    for cid,code in mapping.items():
        if cid not in CANDIDATES:raise SystemExit(f'Unsupported crop ID: {cid}')
        found=[r for r in rows if cell(r,'ECOportcode','EcoPortCode','cropid','ID')==str(code)]
        if len(found)!=1:raise SystemExit(f'Expected one source row for {cid} / EcoPortCode={code}; found {len(found)}')
        r=found[0];species=cell(r,'ScientificName','Scientific_Name','SCINAME','SPECIES','name')
        if not species:raise SystemExit(f'{cid}: scientific name missing; refuses untraceable profile')
        # Explicit selection plus source ID required, but scientific name is preserved verbatim.
        lo=num(r,'TMIN');hi=num(r,'TMAX');phlo=num(r,'PHMIN');phhi=num(r,'PHMAX')
        if lo is not None and hi is not None and not (-80<lo<hi<75):raise SystemExit(f'{cid}: invalid temperature bounds')
        if phlo is not None and phhi is not None and not (0<=phlo<phhi<=14):raise SystemExit(f'{cid}: invalid pH bounds')
        profiles[cid]={'species':species,'source_row_id':str(code),'source_url':SOURCE,
                       'temperature_c':[lo,hi] if lo is not None and hi is not None else None,
                       'soil_ph':[phlo,phhi] if phlo is not None and phhi is not None else None,
                       'source_note':'FAO ECOCROP historical species envelope via OpenCLIM mirror; broad physiological bounds; local calibration and taxon/variety verification required.'}
    OUTPUT.write_text(json.dumps(profiles,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Imported',len(profiles),'source-traceable profiles into',OUTPUT)
    print('IMPORTANT: EcoCrop does not establish field suitability without soil/site/calendar validation.')
if __name__=='__main__':main()
