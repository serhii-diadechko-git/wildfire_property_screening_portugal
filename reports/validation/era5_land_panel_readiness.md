# ERA5-Land readiness — narrowed first-model scope

## Required predictor-year inputs

| Year | Raw status | Required role |
|---:|---|---|
| 2015–2021 | Missing | Training predictor climate context |
| 2023 | Present and registered | Untouched final-test predictor climate context |

The only local raw file is `data/raw/climate/era5_land/era5_land_monthly_jjas_2023_mainland_portugal.grib`.
It is the CDS `reanalysis-era5-land-monthly-means` product for June–September 2023, area `[42.2, -9.6, 36.8, -6.0]` (north, west, south, east).

## 2023 technical facts

- Format: GRIB edition 1, regular latitude/longitude grid, 0.1° spacing; 55 latitude × 37 longitude cells.
- Geographic CRS: regular WGS 84-style latitude/longitude coordinates; values are assigned as coarse context, not reprojected/downscaled weather.
- `2t` / `2m_temperature`: units K; monthly four-record grid.
- `tp` / `total_precipitation`: units m; GRIB `stepType=avgad`, interpreted as monthly average accumulation in m/day.
- `swvl1` / `volumetric_soil_water_layer_1`: units m³/m³; monthly four-record grid.
- Water-mask behaviour: 1,506 coastal 1 km cell centroids map to masked ERA5-Land water cells. Temperature and soil water are null; corrected processing also converts precipitation to null there rather than treating decoded zero as dry conditions.

## Consistent annual derivation

The reusable implementation can apply unchanged to each required year when the same four monthly records and variables are requested:

- mean temperature: `mean(Jun, Jul, Aug, Sep) - 273.15` °C;
- total precipitation: `1000 × (Jun×30 + Jul×31 + Aug×31 + Sep×30)` mm;
- mean soil water: `mean(Jun, Jul, Aug, Sep)` m³/m³.

It reads the small 4 × 55 × 37 climate grids once per year and assigns the containing ERA5-Land cell to bounded batches of the existing 89,112-cell grid. It does not interpolate or downscale values.

## Smallest safe acquisition plan

Make seven separate immutable CDS requests for **2015, 2016, 2017, 2018, 2019, 2020, and 2021**, each limited to June–September, `00:00`, the three required variables, and the existing mainland bounding box. Save one original GRIB per year under `data/raw/climate/era5_land/`; then checksum and validate before derived processing. Do not combine annual raw downloads.

## Readiness conclusion

2023 is ready for the untouched final test. Training-climate readiness is blocked only by the seven missing raw annual GRIB files. An older validation-note string in the bounded pipeline states that precipitation is present at water-mask cells; the corrected assignment code supersedes it by masking precipitation consistently, so that wording should be updated with the next pipeline validation run.
