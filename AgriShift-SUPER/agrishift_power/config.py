"""Validated NASA POWER daily point request configuration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from urllib.parse import urlencode

BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = (
    "T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR",
    "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PS",
)

# Expected units for the AG community. The live response's own units are
# persisted and checked; never silently convert if NASA changes them.
EXPECTED_UNITS = {
    "T2M": "C",
    "T2M_MAX": "C",
    "T2M_MIN": "C",
    "PRECTOTCORR": "mm/day",
    "RH2M": "%",
    "WS2M": "m/s",
    "ALLSKY_SFC_SW_DWN": "MJ/m^2/day",
    "PS": "kPa",
}


@dataclass(frozen=True)
class PowerRequest:
    latitude: float = 30.5
    longitude: float = 31.5
    start: date = date(2025, 1, 1)
    end: date = date(2025, 12, 31)
    time_standard: str = "LST"

    def __post_init__(self) -> None:
        if not isfinite(self.latitude) or not -90 <= self.latitude <= 90:
            raise ValueError("Latitude must be a finite number between -90 and 90")
        if not isfinite(self.longitude) or not -180 <= self.longitude <= 180:
            raise ValueError("Longitude must be a finite number between -180 and 180")
        if self.start > self.end:
            raise ValueError("Start date must not be later than end date")
        if self.time_standard not in ("LST", "UTC"):
            raise ValueError("time_standard must be LST or UTC")

    def url(self) -> str:
        query = urlencode({
            "parameters": ",".join(PARAMETERS),
            "community": "AG",
            "longitude": str(self.longitude),
            "latitude": str(self.latitude),
            "start": self.start.strftime("%Y%m%d"),
            "end": self.end.strftime("%Y%m%d"),
            "format": "JSON",
            "time-standard": self.time_standard,
        })
        return f"{BASE_URL}?{query}"

    def as_dict(self) -> dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "time_standard": self.time_standard,
            "community": "AG",
            "parameters": list(PARAMETERS),
            "request_url": self.url(),
        }
