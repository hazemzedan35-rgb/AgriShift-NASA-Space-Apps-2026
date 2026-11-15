"""Location-specific NASA POWER historical climate, with a bounded point-level disk cache.

This stage deliberately does NOT forecast future seasons, infer field soil, or
supply location-specific agronomic crop calendars. It replaces the fixed point
only. Cache values are always associated with the (rounded) requested coordinates.
"""
from __future__ import annotations

from collections import defaultdict
from contextlib import suppress
from datetime import date, timedelta
from pathlib import Path
import json
import math
import os
import tempfile
import threading
import time
from statistics import mean
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from agrishift_fao.fao56 import calculate_daily_eto
from .config import (COORDINATE_DECIMALS, COORDINATE_PRECISION_DEG, MAX_SUPPORTED_ABS_LATITUDE, PLAUSIBLE_DAILY_RANGES,
                     REFERENCE_DAYS, REFERENCE_YEAR)
from .engine import ROOT, load_reference_data

POWER_URL = 'https://power.larc.nasa.gov/api/temporal/daily/point'
PARAMETERS = ('T2M', 'T2M_MAX', 'T2M_MIN', 'PRECTOTCORR', 'RH2M', 'WS2M', 'ALLSKY_SFC_SW_DWN', 'PS')
EXPECTED_UNITS = {'T2M': 'C', 'T2M_MAX':'C', 'T2M_MIN':'C', 'PRECTOTCORR':'mm/day',
                  'RH2M':'%', 'WS2M':'m/s', 'ALLSKY_SFC_SW_DWN':'MJ/m^2/day', 'PS':'kPa'}

CACHE_ROOT = (
    Path("/tmp/agrishift/location_cache")
    if os.getenv("VERCEL")
    else ROOT / "outputs" / "location_cache"
)

# Network behaviour: a few polite retries for temporary problems only.
FETCH_ATTEMPTS = 3
RETRY_BASE_SECONDS = 1.0           # waits 1 s, then 2 s between attempts
RETRY_MAX_SECONDS = 30.0           # also caps any Retry-After value sent by NASA
RETRYABLE_HTTP_CODES = frozenset({408, 429, 500, 502, 503, 504})
FETCH_TIMEOUT_SECONDS = 45

# The cache folder never grows without limit: least recently used files are removed first.
MAX_CACHE_FILES = 500
STALE_TMP_SECONDS = 3600

# Elevation sanity range (metres), the same range the FAO-56 module accepts.
ELEVATION_RANGE_M = (-500.0, 6000.0)

_LOCK_STRIPES = [threading.Lock() for _ in range(64)]

class ClimateDataError(RuntimeError):
    """No trustworthy data can be provided for these coordinates."""


def normalize_coordinates(latitude, longitude):
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError) as ex:
        raise ValueError('Latitude/longitude must be numbers') from ex
    if not all(map(math.isfinite,(lat,lon))) or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ValueError('Latitude must be -90..90 and longitude -180..180')
    # ~1 km request precision (see config.COORDINATE_DECIMALS). Adding 0.0 turns -0.0 into 0.0,
    # so the same place can never produce two different cache keys.
    return round(lat,COORDINATE_DECIMALS)+0.0,round(lon,COORDINATE_DECIMALS)+0.0


def nasa_power_url(lat,lon):
    return POWER_URL+'?'+urlencode({
        'parameters':','.join(PARAMETERS),'community':'AG','longitude':lon,'latitude':lat,
        'start':f'{REFERENCE_YEAR}0101','end':f'{REFERENCE_YEAR}1231','format':'JSON','time-standard':'LST'})


def _retry_delay(attempt, error=None):
    """Exponential back-off (1 s, 2 s, ...), honouring a numeric Retry-After header, capped."""
    delay = RETRY_BASE_SECONDS * (2 ** (attempt - 1))
    headers = getattr(error, 'headers', None)
    retry_after = headers.get('Retry-After') if hasattr(headers, 'get') else None
    with suppress(TypeError, ValueError):
        delay = max(delay, float(retry_after))
    return min(delay, RETRY_MAX_SECONDS)


def _fetch_json(url):
    """GET a NASA POWER URL. Retries only temporary failures; never invents data."""
    last_error = None
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        try:
            with urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as stream:  # fixed NASA hostname, no user-selected URLs
                return json.loads(stream.read().decode('utf-8'))
        except HTTPError as ex:                       # must come before URLError (its parent class)
            last_error = ex
            if ex.code not in RETRYABLE_HTTP_CODES:
                break
        except (URLError, TimeoutError, OSError) as ex:
            last_error = ex
        except (json.JSONDecodeError, UnicodeDecodeError) as ex:
            last_error = ex                           # a garbled answer will not improve by asking again
            break
        if attempt < FETCH_ATTEMPTS:
            time.sleep(_retry_delay(attempt, last_error))
    raise ClimateDataError('NASA POWER is unreachable or returned invalid data; try later. No fallback data were fabricated.') from last_error


def _validated_rows(response):
    try:
        params=response['properties']['parameter']
        units={key:response['parameters'][key]['units'] for key in PARAMETERS}
        if units!=EXPECTED_UNITS:
            raise ClimateDataError(f'Unexpected NASA units: {units}')
        dates=[(date(REFERENCE_YEAR,1,1)+timedelta(days=i)).strftime('%Y%m%d') for i in range(REFERENCE_DAYS)]
        rows=[]
        for day in dates:
            row={'date':f'{day[:4]}-{day[4:6]}-{day[6:]}'}
            for p in PARAMETERS:
                value=float(params[p][day])
                if not math.isfinite(value) or value == -999:
                    raise ClimateDataError(f'Missing/invalid NASA value: {day} / {p}')
                row[p]=value
            if row['T2M_MIN']>row['T2M_MAX'] or not 0<=row['RH2M']<=100 or row['WS2M']<0 or row['ALLSKY_SFC_SW_DWN']<0 or row['PRECTOTCORR']<0 or not 70<=row['PS']<=115:
                raise ClimateDataError(f'Out-of-range NASA record: {day}')
            for name,(low,high) in PLAUSIBLE_DAILY_RANGES.items():
                if not low<=row[name]<=high:
                    raise ClimateDataError(f'Physically implausible NASA value: {day} / {name} = {row[name]}')
            rows.append(row)
        if set(params)!=set(PARAMETERS):
            # Additional product variables are acceptable; the requested eight must all exist.
            if not set(PARAMETERS).issubset(params):raise ClimateDataError('NASA omitted a parameter')
        return rows
    except ClimateDataError:
        raise
    except (KeyError,TypeError,ValueError,OverflowError) as ex:
        raise ClimateDataError('Unexpected/missing fields in NASA POWER response') from ex


def _elevation_from_response(response):
    """(metres, source). NASA returns the point elevation as the 3rd geometry coordinate.

    The value is NASA's MERRA-2 grid-cell average, not the farm's own elevation. If it is
    missing or implausible we fall back to 0 m and SAY so, instead of silently assuming it.
    """
    try:
        value = float(response['geometry']['coordinates'][2])
    except (KeyError, IndexError, TypeError, ValueError):
        return 0.0, 'assumed_zero'
    low, high = ELEVATION_RANGE_M
    if not math.isfinite(value) or not low <= value <= high:
        return 0.0, 'assumed_zero'
    return value, 'nasa_power_response'


def _make_reference(response,lat,lon):
    rows=_validated_rows(response)
    header=response.get('header',{})
    if not isinstance(header,dict) or header.get('time_standard') not in (None,'LST'):
        raise ClimateDataError('NASA response has an unexpected time standard')
    if header.get('start') not in (None, f'{REFERENCE_YEAR}0101') or header.get('end') not in (None, f'{REFERENCE_YEAR}1231'):
        raise ClimateDataError('NASA response period does not match requested year')
    geom=response.get('geometry',{})
    coords=geom.get('coordinates') if isinstance(geom,dict) else None
    is_real_power_header = str(header.get('title','')).startswith('NASA/POWER')
    if is_real_power_header and coords is None:
        raise ClimateDataError('NASA POWER response has no reported location geometry')
    if coords is not None:
        if not isinstance(coords,list) or len(coords)<2:
            raise ClimateDataError('Malformed NASA response location geometry')
        try:
            returned_lon,returned_lat=float(coords[0]),float(coords[1])
        except (TypeError,ValueError) as exc:
            raise ClimateDataError('Invalid NASA geometry coordinates') from exc
        # POWER gridded data may have a nearby cell center, not exact farm coordinates.
        dlon=abs((returned_lon-lon+180)%360-180)
        if is_real_power_header and (not all(map(math.isfinite,(returned_lat,returned_lon))) or abs(returned_lat-lat)>1.0 or dlon>1.0):
            raise ClimateDataError('NASA response geometry is not near the requested location')
    # Not all NASA-shaped test fixtures expose geometry; flag missing provenance below.

    elevation,elevation_source=_elevation_from_response(response)
    try:
        eto=[calculate_daily_eto(r,lat,elevation) for r in rows]
    except ValueError as ex:
        raise ClimateDataError('FAO ET0 calculation rejected NASA data') from ex
    etos=[r['eto_mm_day'] for r in eto]
    summary={'days':REFERENCE_DAYS,'eto_total_mm':round(sum(etos),3),'eto_mean_mm_day':round(mean(etos),3),
             'elevation_m':elevation,'elevation_source':elevation_source}
    meta={'data_status':'LIVE_NASA_API','request':{'latitude':lat,'longitude':lon,'start':f'{REFERENCE_YEAR}-01-01','end':f'{REFERENCE_YEAR}-12-31','time_standard':'LST'},
          'nasa_header':response.get('header',{}),'data_quality':f'{REFERENCE_DAYS} checked daily rows with all eight required values',
          'coordinate_precision_deg':COORDINATE_PRECISION_DEG,
          'location_geometry_verified':is_real_power_header and coords is not None}
    return {'meta':meta,'summary':summary,'eto':eto,'climate':rows}


def _cache_path(lat,lon):
    return CACHE_ROOT/f'{lat:+08.2f}_{lon:+09.2f}_{REFERENCE_YEAR}.json'


def _read_cache(path,lat,lon):
    """Return (meta, summary, eto, climate), or None if absent or unusable.

    A damaged file (partial write, hand-edited, wrong shape) is deleted and treated as a
    cache miss, so one bad file can never turn into a permanent server error.
    """
    try:
        obj=json.loads(path.read_text(encoding='utf-8'))
        meta,summary,eto,climate=obj['meta'],obj['summary'],obj['eto'],obj['climate']
        request=meta['request']
        cached=(request['latitude'],request['longitude'])
        if not isinstance(eto,list) or not isinstance(climate,list) or len(eto)!=REFERENCE_DAYS or len(climate)!=REFERENCE_DAYS:
            raise ValueError('wrong cache shape')
        if not isinstance(summary,dict) or 'eto_total_mm' not in summary:
            raise ValueError('wrong cache shape')
    except FileNotFoundError:
        return None
    except (OSError,ValueError,KeyError,TypeError):
        with suppress(OSError):path.unlink()
        return None
    if cached!=(lat,lon):
        raise ClimateDataError('Cached climate coordinates do not match request')
    with suppress(OSError):os.utime(path)   # mark as recently used (for pruning)
    return meta,summary,eto,climate


def _write_cache_atomically(path,obj):
    """Write to a tmp file that is unique to this call, then rename into place."""
    path.parent.mkdir(parents=True,exist_ok=True)
    handle,tmp_name=tempfile.mkstemp(dir=path.parent,prefix=path.stem+'.',suffix='.tmp')
    try:
        with os.fdopen(handle,'w',encoding='utf-8') as stream:
            json.dump(obj,stream,ensure_ascii=False)
        os.replace(tmp_name,path)
    except BaseException:
        with suppress(OSError):os.unlink(tmp_name)
        raise


def _prune_cache(base,keep):
    """Keep at most MAX_CACHE_FILES cache files (least recently used go first); drop stale tmp files."""
    now=time.time()
    with suppress(OSError):
        for tmp in base.glob('*.tmp'):
            if now-tmp.stat().st_mtime>STALE_TMP_SECONDS:
                with suppress(OSError):tmp.unlink()
    try:
        files=sorted(base.glob('*.json'),key=lambda p:p.stat().st_mtime)
    except OSError:
        return
    excess=len(files)-MAX_CACHE_FILES
    for path in files:
        if excess<=0:break
        if path==keep:continue
        try:
            path.unlink()
            excess-=1
        except OSError:
            continue


def get_reference_data(lat,lon,fetch_json=None,cache_root=None):
    """Return compatible (crop DB, metadata, summary, ET0 rows, climate rows).

    For original pilot coordinates, bundled NASA data are used (offline-friendly).
    For all other points, a cached response or a live NASA request is required.
    Identical simultaneous requests share ONE NASA call.
    """
    lat,lon=normalize_coordinates(lat,lon)
    if abs(lat)>MAX_SUPPORTED_ABS_LATITUDE:
        raise ClimateDataError(f'Latitude beyond +/-{MAX_SUPPORTED_ABS_LATITUDE:g} degrees is not supported: the FAO-56 daily ET0 method does not apply in polar night.')
    if lat==30.5 and lon==31.5:
        return load_reference_data()
    base=Path(cache_root) if cache_root is not None else CACHE_ROOT
    cache=base/_cache_path(lat,lon).name
    from .engine import CROPS_DB
    db=json.loads(CROPS_DB.read_text(encoding='utf-8'))
    with _LOCK_STRIPES[hash(cache.name)%len(_LOCK_STRIPES)]:
        cached=_read_cache(cache,lat,lon)
        if cached is not None:
            return (db,)+cached
        source=fetch_json or _fetch_json
        obj=_make_reference(source(nasa_power_url(lat,lon)),lat,lon)
        # persist only validated responses; never populate cache with placeholders
        _write_cache_atomically(cache,obj)
        _prune_cache(base,cache)
    return db,obj['meta'],obj['summary'],obj['eto'],obj['climate']


def monthly_eto(eto_rows):
    groups=defaultdict(list)
    for r in eto_rows:
        groups[str(r['date'])[:7]].append(float(r['eto_mm_day']))
    return [{'month':month,'daily_mean_mm':round(mean(data),3),'eto_total_mm':round(sum(data),3)}
            for month,data in sorted(groups.items())]
