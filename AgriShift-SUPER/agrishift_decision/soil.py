"""FAO-56 soil-water capacity and ECe screening for AgriShift.

No crop yield, true field soil moisture, irrigation scheduling, or soil suitability
is inferred. Texture-class defaults are explicitly illustrative FAO Table 19
midpoints; if supplied, the farm user's AWC overrides the texture default.
"""
from __future__ import annotations

from typing import Optional

FAO_CH7 = 'https://www.fao.org/4/X0490E/x0490e0c.htm'
FAO_CH8 = 'https://www.fao.org/4/X0490E/x0490e0e.htm'

# Typical ranges of (theta_FC - theta_WP) (m3/m3), FAO-56 Table 19.
# We use midpoints only as SCREENING assumptions when laboratory data is missing.
TEXTURE_AWC = {
    'sand': {'min': 50., 'max': 110., 'default': 80.},
    'loam': {'min': 130., 'max': 180., 'default': 155.},
    'clay': {'min': 120., 'max': 200., 'default': 160.},
}

# FAO-56 Table 22: minimum of effective root-depth range, and tabulated p.
# These approximate mature crop root zones (NOT seedling rooting depth).
CROP_ROOT = {
    'wheat': {'root_depth_m': 1.5, 'p': 0.55},
    'faba': {'root_depth_m': 0.5, 'p': 0.45},
    'maize': {'root_depth_m': 1.0, 'p': 0.55},
    'sunflower': {'root_depth_m': 0.8, 'p': 0.45},
    'rice': {'root_depth_m': 0.5, 'p': 0.20},
    'cotton': {'root_depth_m': 1.0, 'p': 0.65},
    'potato': {'root_depth_m': 0.4, 'p': 0.35},
    'tomato': {'root_depth_m': 0.7, 'p': 0.40},
    'onion': {'root_depth_m': 0.3, 'p': 0.30},
    'sugarbeet': {'root_depth_m': 0.7, 'p': 0.55},
    'alfalfa': {'root_depth_m': 1.0, 'p': 0.55},
    'sorghum': {'root_depth_m': 1.0, 'p': 0.55},
}

# FAO-56 Table 23 salinity thresholds for ordinary wheat, faba bean and
# field maize. Sunflower lacks a numeric value in this table: explicitly unknown.
# FAO-56 Table 23. For tomato the published interval (0.9-2.5) is NOT replaced by an invented single threshold.
SALINITY_ECE_THRESHOLD = {'wheat': 6.0, 'faba': 1.6, 'maize': 1.7,
    'rice':3.0,'cotton':7.7,'potato':1.7,'onion':1.2,'sugarbeet':7.0,'alfalfa':2.0,'sorghum':6.8}
SALINITY_ECE_RANGE = {'tomato': (0.9,2.5)}


def awc_for_farm(soil_type: str, measured_awc_mm_per_m: Optional[float] = None):
    """Return a documented AWC assumption, not measured field moisture."""
    if measured_awc_mm_per_m is not None:
        return {'value_mm_per_m': float(measured_awc_mm_per_m),
                'source_kind': 'farmer_supplied_awc',
                'reference': 'User-provided plant-available water capacity; measurement method unverified',
                'typical_range_mm_per_m': None}
    if soil_type in TEXTURE_AWC:
        profile = TEXTURE_AWC[soil_type]
        return {'value_mm_per_m': profile['default'],
                'source_kind': 'fao56_texture_midpoint_assumption',
                'reference': 'FAO-56 Table 19 (range midpoint)',
                'typical_range_mm_per_m': [profile['min'],profile['max']]}
    return {'value_mm_per_m': None, 'source_kind': 'unknown',
            'reference': 'No soil texture or AWC supplied', 'typical_range_mm_per_m': None}


def soil_crop_screen(crop_id: str, awc, ece_ds_m: Optional[float], midseason_etc_mm_day: float):
    """TAW=AWC*Zr, RAW=p*TAW, buffer=RAW/mid-season ETc.

    Buffer days is only a notional at-field-capacity, no-rain/no-irrigation
    dry-down at constant midseason ETc; it is NOT a safe irrigation interval.
    """
    root = CROP_ROOT[crop_id]
    value = awc['value_mm_per_m']
    if value is None:
        taw = raw = buffer = None
    else:
        taw = round(value * root['root_depth_m'], 2)
        raw = round(root['p'] * taw, 2)
        buffer = round(raw / midseason_etc_mm_day, 2) if midseason_etc_mm_day > 0 else None
    threshold = SALINITY_ECE_THRESHOLD.get(crop_id)
    threshold_range = SALINITY_ECE_RANGE.get(crop_id)
    if ece_ds_m is None:
        salinity = 'not_tested'
    elif threshold_range is not None:
        if ece_ds_m <= threshold_range[0]: salinity = 'below_all_published_thresholds'
        elif ece_ds_m > threshold_range[1]: salinity = 'above_published_threshold'
        else: salinity = 'within_published_threshold_range_uncertain'
    elif threshold is None:
        salinity = 'no_numeric_threshold_in_fao56_table23'
    else:
        salinity = 'above_published_threshold' if ece_ds_m > threshold else 'at_or_below_published_threshold'
    return {
        'crop_id':crop_id,
        'awc_mm_per_m':value,
        'awc_source':awc['source_kind'],
        'root_depth_m':root['root_depth_m'],
        'root_depth_source':'FAO-56 Table 22 lower bound; mature-crop approximation',
        'depletion_fraction_p':root['p'],
        'total_available_water_taw_mm':taw,
        'readily_available_water_raw_mm':raw,
        'midseason_etc_reference_mm_day':round(midseason_etc_mm_day,2),
        'notional_buffer_days':buffer,
        'soil_ece_ds_m':ece_ds_m,
        'fao56_ece_threshold_ds_m':threshold,
        'fao56_ece_threshold_range_ds_m':list(threshold_range) if threshold_range else None,
        'salinity_flag':salinity,
        'notes':[
            'TAW and RAW are indicative root-zone storage capacity, NOT current soil moisture.',
            'Buffer days assume full field capacity, no irrigation/rain, constant midseason ETc and mature roots; not an irrigation schedule.',
            'Texture/default values and root-depth assumptions must be locally validated; ECe must be saturated-paste extract EC.',
            'A crop below its published ECe threshold is not proven suitable; other field risks remain.'
        ]
    }
