"""FAO-56 reference-grass Penman-Monteith daily ET0.

Primary reference: FAO Irrigation and Drainage Paper No. 56, chapters 2–4:
https://www.fao.org/4/X0490E/x0490e06.htm
https://www.fao.org/4/X0490E/x0490e07.htm
https://www.fao.org/4/X0490E/x0490e08.htm

N.B.: This is REFERENCE evapotranspiration (ET0), not crop ETc, irrigation
need, soil moisture, or yield prediction.
"""
import math
from datetime import date as date_type

SIGMA = 4.903e-9  # MJ K^-4 m^-2 day^-1
SOLAR_CONSTANT = 0.0820  # MJ m^-2 min^-1
ALBEDO = 0.23  # standard FAO grass reference


def saturation_vapour_pressure(temp_c: float) -> float:
    """Saturated vapour pressure (kPa), FAO-56 Eq. 11."""
    if temp_c <= -237.3:
        raise ValueError("Invalid temperature for vapour-pressure equation")
    return 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))


def extraterrestrial_radiation(latitude_deg: float, day_of_year: int) -> float:
    """Daily extraterrestrial radiation Ra in MJ m^-2 day^-1, Eq. 21–25."""
    if not -90 <= latitude_deg <= 90 or not 1 <= day_of_year <= 366:
        raise ValueError("Invalid latitude or Julian day")
    phi = math.radians(latitude_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
    decl = 0.409 * math.sin(2 * math.pi * day_of_year / 365 - 1.39)
    acos_arg = min(1, max(-1, -math.tan(phi) * math.tan(decl)))
    ws = math.acos(acos_arg)
    return 24 * 60 / math.pi * SOLAR_CONSTANT * dr * (
        ws * math.sin(phi) * math.sin(decl)
        + math.cos(phi) * math.cos(decl) * math.sin(ws)
    )


def fao_pm(*, tmean_c: float, u2_m_s: float, es_kpa: float, ea_kpa: float,
           delta_kpa_c: float, gamma_kpa_c: float, net_radiation_mj_m2_day: float,
           ground_heat_flux_mj_m2_day: float = 0.0) -> float:
    """FAO-56 Eq. 6, reference evapotranspiration in mm/day."""
    vpd = es_kpa - ea_kpa
    numerator = (0.408 * delta_kpa_c *
                 (net_radiation_mj_m2_day - ground_heat_flux_mj_m2_day)
                 + gamma_kpa_c * (900 / (tmean_c + 273)) * u2_m_s * vpd)
    denominator = delta_kpa_c + gamma_kpa_c * (1 + 0.34 * u2_m_s)
    if denominator <= 0 or tmean_c <= -273:
        raise ValueError("Invalid parameters for FAO-56 Eq. 6")
    return numerator / denominator


def calculate_daily_eto(rec: dict, latitude_deg: float, elevation_m: float = 0.0) -> dict:
    """Compute daily grass-reference ET0, input keys as Stage 1 CSV.

    FAO mean temperature is (Tmax+Tmin)/2, not NASA T2M. Because Stage 1 only
    has RH2M (mean daily relative humidity), actual vapour pressure is derived
    with FAO-56 Eq. 19 (less desirable than use of RHmax/RHmin or dewpoint).
    Measured NASA PS (kPa) is used for psychrometric gamma. Altitude is used
    only for the clear-sky radiation estimate; default elevation=0 m is a
    conspicuous ASSUMPTION, not an observed site elevation.
    """
    d = date_type.fromisoformat(str(rec['date']))
    tm_nasa = float(rec['T2M'])
    tmax = float(rec['T2M_MAX'])
    tmin = float(rec['T2M_MIN'])
    rh = float(rec['RH2M'])
    u2 = float(rec['WS2M'])
    rs = float(rec['ALLSKY_SFC_SW_DWN'])
    p = float(rec['PS'])
    values = [tm_nasa,tmax,tmin,rh,u2,rs,p,latitude_deg,elevation_m]
    if not all(math.isfinite(x) for x in values):
        raise ValueError(f"Non-finite weather input for {d}")
    if tmin > tmax or not 0 <= rh <= 100 or u2 < 0 or rs < 0 or not 70 <= p <= 115:
        raise ValueError(f"Invalid daily weather input for {d}")
    if not -500 <= elevation_m <= 6000:
        raise ValueError("Elevation must be between -500 and 6000 m")
    tmean = (tmax+tmin)/2.0
    es = (saturation_vapour_pressure(tmax) + saturation_vapour_pressure(tmin))/2
    ea = es * rh / 100  # FAO-56 Eq. 19, less preferred RHmean approach
    delta = 4098 * saturation_vapour_pressure(tmean) / (tmean+237.3)**2
    gamma = 0.000665 * p  # kPa/C, using observed NASA daily surface pressure
    ra = extraterrestrial_radiation(latitude_deg, d.timetuple().tm_yday)
    rso = (0.75 + 2e-5 * elevation_m) * ra  # FAO-56 Eq. 37
    if rso <= 0:
        raise ValueError(f"Clear-sky radiation non-positive for {d}")
    ratio_raw = rs / rso
    # FAO longwave cloudiness expression is calibrated for 0.3 <= Rs/Rso <= 1.
    # Bound ONLY cloudiness term; retain original Rs in net shortwave radiation.
    ratio = min(1.0, max(0.3, ratio_raw))
    rns = (1 - ALBEDO) * rs
    rnl = (SIGMA * ((tmax+273.16)**4 + (tmin+273.16)**4) / 2
           * (0.34 - 0.14 * math.sqrt(ea)) * (1.35 * ratio - 0.35))
    rn = rns-rnl
    eto_unclipped = fao_pm(tmean_c=tmean,u2_m_s=u2,es_kpa=es,ea_kpa=ea,
                            delta_kpa_c=delta,gamma_kpa_c=gamma,
                            net_radiation_mj_m2_day=rn)
    # An annual sequence should not be silently distorted by negative ET0.
    # Warn and report raw values, set negative physical ET0 to 0 for aggregates.
    flags=[]
    if ratio_raw > 1:flags.append('RS_GT_RSO_CLOUD_FACTOR_CAPPED')
    if ratio_raw < 0.3:flags.append('RS_LT_0_3_RSO_CLOUD_FACTOR_FLOORED')
    if eto_unclipped < 0: flags.append('NEGATIVE_ETO_CLIPPED_TO_ZERO')
    if abs(tm_nasa-tmean)>3:flags.append('NASA_T2M_DIFFERS_FROM_FAO_TMEAN_GT3C')
    return {
      'date': d.isoformat(), 'eto_mm_day':round(max(0,eto_unclipped),5),
      'eto_unclipped_mm_day':round(eto_unclipped,5),
      'nasa_t2m_c':tm_nasa,'fao_tmean_c':round(tmean,3),
      'es_kpa':round(es,5),'ea_kpa':round(ea,5),
      'vapour_pressure_deficit_kpa':round(es-ea,5),
      'ra_mj_m2_day':round(ra,5),'rso_mj_m2_day':round(rso,5),
      'rn_mj_m2_day':round(rn,5),'rs_over_rso_raw':round(ratio_raw,5),
      'quality_flags':';'.join(flags)
    }
