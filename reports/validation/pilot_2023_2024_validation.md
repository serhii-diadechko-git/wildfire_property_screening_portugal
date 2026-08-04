# Enriched 2023 → 2024 pilot validation

The map shows the observed 2024 ICNF burned-share target, not a model prediction. ICNF 2023 was not used. CLC is generalized 2018 landscape context; ERA5-Land is coarse regional context with no downscaling.

```json
{
  "created_utc": "2026-08-04T10:48:53.870466+00:00",
  "rows": 89112,
  "expected_rows": 89112,
  "unique_cell_id": true,
  "output_crs": "EPSG:3763",
  "output_geometry_type": "Polygon",
  "target_range": [
    0.0,
    1.0
  ],
  "icnf_history_years": [
    2013,
    2014,
    2015,
    2016,
    2017,
    2018,
    2019,
    2020,
    2021,
    2022
  ],
  "icnf_2023_used": false,
  "clc_method": "EPSG:3035 generalized landscape-area shares; current bounded pipeline uses per-tile GeoPackage bbox reads",
  "era5_method": "containing 0.1-degree ERA5-Land cell at grid-cell centroid; no interpolation or downscaling",
  "units": {
    "warm_season_mean_2m_temperature_c": "degrees_celsius",
    "warm_season_total_precipitation_mm": "millimetres",
    "warm_season_mean_soil_water_layer1": "m3_per_m3"
  },
  "missingness": {
    "cell_id": 0,
    "observation_year": 0,
    "fire_years_previous_10y_2km": 0,
    "built_up_share": 0,
    "forest_shrub_share": 0,
    "agricultural_share": 0,
    "warm_season_mean_2m_temperature_c": 1506,
    "warm_season_total_precipitation_mm": 0,
    "warm_season_mean_soil_water_layer1": 1506,
    "burned_share_next_year": 0
  },
  "era5_land_mask_note": "Coastal grid-cell centroids whose containing ERA5-Land cell is masked as water retain missing temperature/soil-water context; precipitation is present."
}
```
