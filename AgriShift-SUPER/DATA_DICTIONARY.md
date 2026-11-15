# NASA POWER Daily Data Dictionary (AgriShift Stage 1)

These are **expected** units under NASA POWER AG daily point response. The program preserves and checks actual units returned by NASA in `metadata.json`. Never silently assume units if the QA report flags a mismatch.

| Code | Meaning | Expected units | Stage 2 proposed role |
|---|---|---|---|
| T2M | Daily mean air temperature at 2 m | C | Temperature and ET0 |
| T2M_MAX | Daily maximum air temperature at 2 m | C | FAO-56 ET0, heat stress context |
| T2M_MIN | Daily minimum air temperature at 2 m | C | FAO-56 ET0, cold stress context |
| PRECTOTCORR | Corrected precipitation | mm/day | Precipitation input (not effective rainfall or irrigation) |
| RH2M | Daily mean relative humidity at 2 m | % | ET0 estimate; daily mean alone has approximations |
| WS2M | Daily mean wind speed at 2 m | m/s | FAO-56 wind input |
| ALLSKY_SFC_SW_DWN | Shortwave downward solar irradiation | MJ/m²/day | Radiation input; not identical to net radiation Rn |
| PS | Surface air pressure | kPa | Atmospheric pressure for psychrometric calculations |

### Output conventions

- `date`: `YYYY-MM-DD`, covering one daily sample. `time_standard=LST` by default.
- Unknown/missing readings: JSON `null`, blank CSV cell, never 0.
- NASA raw `fill_value` (usually -999) is not a measurement.
- `monthly_summary.csv` sums precipitation/radiation **only if every selected day of the month has a valid value**.
- `metadata.json` tracks point coordinates sent to API and NASA-reported location/source metadata. NASA point data may represent an underlying grid cell, not exact field sensors.
- The 8 requested variables have different native sources and spatial resolutions; do not characterize the entire response as field-scale.
