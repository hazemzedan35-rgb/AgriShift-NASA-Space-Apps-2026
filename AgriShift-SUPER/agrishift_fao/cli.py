"""Execute FAO-56 ET0 estimation on validated user-uploaded NASA POWER data."""
import argparse
import csv
import json
from collections import defaultdict, Counter
from pathlib import Path
from statistics import mean
from .validation import verify_source
from .fao56 import calculate_daily_eto


def run(source_dir, output_dir, elevation_m):
    records,meta,verification=verify_source(source_dir)
    lat=meta['request']['latitude']; lon=meta['request']['longitude']
    daily=[calculate_daily_eto(r,lat,elevation_m) for r in records]
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    with (output_dir/'daily_eto.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(daily[0].keys())); writer.writeheader();writer.writerows(daily)
    (output_dir/'daily_eto.json').write_text(json.dumps(daily,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    groups=defaultdict(list)
    for r in daily:groups[r['date'][:7]].append(r)
    monthly=[]
    for month,rr in sorted(groups.items()):
        monthly.append({'month':month,'days':len(rr),
                        'eto_total_mm':round(sum(v['eto_mm_day'] for v in rr),3),
                        'eto_daily_mean_mm':round(mean(v['eto_mm_day'] for v in rr),3)})
    with (output_dir/'monthly_eto.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(monthly[0].keys()));w.writeheader();w.writerows(monthly)
    flags=Counter(flag for row in daily for flag in row['quality_flags'].split(';') if flag)
    summary={'project':'AgriShift','stage':'2a','calculation':'FAO-56 daily grass-reference evapotranspiration ET0',
        'location':{'latitude':lat,'longitude':lon},
        'data_period':{'start':verification['first_day'],'end':verification['last_day']},
        'days':len(daily),'eto_total_mm':round(sum(x['eto_mm_day'] for x in daily),3),
        'eto_mean_mm_day':round(mean(x['eto_mm_day'] for x in daily),3),
        'eto_min_mm_day':round(min(x['eto_mm_day'] for x in daily),3),
        'eto_max_mm_day':round(max(x['eto_mm_day'] for x in daily),3),
        'flags_by_type':dict(flags),'elevation_assumption_m':elevation_m,
        'observed_climate_source':'NASA POWER daily point, source metadata preserved',
        'limitations':['ET0 reference grass not crop ETc or irrigation demand',
            'Using NASA daily mean RH2M to estimate actual vapour pressure via FAO56 Eq.19; less preferred than RHmin/RHmax or dewpoint',
            'FAO daily Tmean=(Tmax+Tmin)/2 can differ from NASA T2M',
            'Elevation used in clear-sky radiation is assumed, not observed; supply --elevation-m when known',
            'NASA gridded climate estimates are not on-farm measurements',
            'Cloudiness Rs/Rso bounded to [0.3,1.0] for FAO longwave formula; warnings counted']}
    (output_dir/'annual_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    method={'primary_reference':'FAO Irrigation and Drainage Paper 56 (1998)',
        'reference_urls':['https://www.fao.org/4/X0490E/x0490e06.htm',
                          'https://www.fao.org/4/X0490E/x0490e07.htm',
                          'https://www.fao.org/4/X0490E/x0490e08.htm'],
        'equation':'FAO Penman-Monteith daily Eq6',
        'shortwave_rs':'NASA ALLSKY_SFC_SW_DWN MJ/m^2/day',
        'fao_tmean':'(NASA T2M_MAX + NASA T2M_MIN) / 2, by FAO-56 convention',
        'ea':'es*(NASA RH2M/100), FAO-56 Eq19 approximation',
        'es':'(esat(Tmax)+esat(Tmin))/2',
        'pressure':'NASA PS (kPa) used for psychrometric gamma',
        'wind':'NASA WS2M already at 2m; no height conversion required',
        'albedo':0.23,'ground_heat_flux':0.0,
        'clear_sky_radiation_elevation_m':elevation_m,
        'elevation_source':'explicit user-specified' if elevation_m!=0 else 'zero-meter default assumption; not independently verified',
        'inputs_stage1_verified':verification,'research_level':'reference ET0 calculation, not field-calibrated irrigation model'}
    (output_dir/'science_method.json').write_text(json.dumps(method,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('AgriShift STAGE 2a — FAO-56 ET0')
    print(f'Validated {len(daily)} daily rows from NASA data, {lat}N {lon}E')
    print(f"ET0 annual sum: {summary['eto_total_mm']:.3f} mm, mean: {summary['eto_mean_mm_day']:.3f} mm/day")
    print('Quality flags:',dict(flags))
    print('Saved to:',str(output_dir.resolve()))
    print('CAUTION: ET0 is reference evapotranspiration, not crop irrigation requirement.')
    return summary


def main():
    ap=argparse.ArgumentParser(description='AgriShift Stage2a - FAO-56 reference ET0')
    ap.add_argument('--source-dir',default='outputs/nile_delta_2025',help='Folder holding all six Stage1 output files')
    ap.add_argument('--out',default='outputs/fao_eto_2025',help='Results folder')
    ap.add_argument('--elevation-m',type=float,default=0.0,help='Site elevation meters; DEFAULT ZERO IS AN ASSUMPTION')
    a=ap.parse_args();run(a.source_dir,a.out,a.elevation_m)

if __name__=='__main__':main()
