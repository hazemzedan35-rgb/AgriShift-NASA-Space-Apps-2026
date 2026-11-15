"""Single place for settings that used to be hard-coded numbers scattered across the backend.

Nothing here imports other AgriShift modules, so every module can import it safely.
"""
from calendar import isleap
from datetime import date

# The NASA POWER year reused as a historical seasonal ANALOGUE for every planned season.
# The bundled pilot dataset (outputs/nile_delta_2025, outputs/fao_eto_2025) is for this year.
REFERENCE_YEAR = 2025
REFERENCE_DAYS = 366 if isleap(REFERENCE_YEAR) else 365

# Request coordinates are rounded to this many decimals (0.01 degree is about 1.1 km).
# NASA POWER's grids are far coarser (about 0.5 x 0.625 degrees for meteorology and
# 1 x 1 degree for solar radiation, per NASA's POWER FAQ), so finer precision adds nothing
# except an unbounded number of cache files.
COORDINATE_DECIMALS = 2
COORDINATE_PRECISION_DEG = 10 ** -COORDINATE_DECIMALS

# Beyond about 66.5 degrees the sun does not rise on some days of the year (polar night), so
# extraterrestrial radiation is zero and the FAO-56 daily ET0 method used here does not apply.
MAX_SUPPORTED_ABS_LATITUDE = 66.5

# Physical plausibility limits for daily NASA POWER values (generous: real records fit easily).
# They exist to catch a corrupted or mis-scaled response, not to second-guess real weather.
PLAUSIBLE_DAILY_RANGES = {
    'T2M': (-90.0, 60.0), 'T2M_MAX': (-90.0, 60.0), 'T2M_MIN': (-90.0, 60.0),   # deg C (world records -89.2 / 56.7)
    'PRECTOTCORR': (0.0, 2000.0),                                                # mm/day (record about 1825)
    'WS2M': (0.0, 50.0),                                                         # m/s daily mean at 2 m
    'ALLSKY_SFC_SW_DWN': (0.0, 50.0),                                            # MJ/m2/day (cannot exceed top-of-atmosphere)
}

# Illustrative sowing dates (month, day). NOT a recommended crop calendar.
WINTER_SOWING = (11, 10)
SUMMER_SOWING = (5, 15)

# Allowed range for the optional first_winter_year request field.
MIN_FIRST_WINTER_YEAR = 2000
MAX_FIRST_WINTER_YEAR = 2100

# Candidate plans whose modeled water differs by less than this (percent) are "nearly tied".
CLOSE_WATER_DIFFERENCE_PCT = 10.0


def default_first_winter_year(today=None):
    """Year of the next winter sowing date that has not already passed.

    On the sowing day itself the season is still plannable. After it, the default moves
    to next year, so a plan never silently starts in a season that is already under way.
    """
    today = today or date.today()
    this_year_sowing = date(today.year, *WINTER_SOWING)
    return today.year if today <= this_year_sowing else today.year + 1
