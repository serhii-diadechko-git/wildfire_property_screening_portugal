# National 2015-2024 cell-year panel validation

**National panel validated — panel EDA may begin.**

This decision authorises panel EDA only. It does not establish modelling readiness, which still requires missing-data treatment and target-distribution analysis.

## Identity and batching

- Canonical EPSG:3763 grid cells: 89,112.
- Expected and actual rows: 891,120.
- Deterministic 20 km spatial tiles, atomic Parquet batches, checksum manifests, completed-batch reuse, and overwrite protection were used.
- Schema: 21 ordered fields with validated Arrow types; identifiers and source metadata have no missing values.
- Panel SHA-256: `96C24EE6A4F5F6F5E06963CE97434AE22742AA6190A17DA2A161C933A5941183`.

## Target and climate completeness by year

| T | Outcome | Rows | Positive rows | Positive cells | Zero proportion | Mean | Q95 | Q99 | Max | Joint climate-missing rows |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015 | 2016 | 89,112 | 5,773 | 5,773 | 0.935216 | 0.01753729 | 0.007240 | 0.729508 | 1.000000 | 0 |
| 2016 | 2017 | 89,112 | 12,122 | 12,122 | 0.863969 | 0.06286468 | 0.696303 | 1.000000 | 1.000000 | 0 |
| 2017 | 2018 | 89,112 | 1,447 | 1,447 | 0.983762 | 0.00448297 | 0.000000 | 0.038782 | 1.000000 | 0 |
| 2018 | 2019 | 89,112 | 3,004 | 3,004 | 0.966290 | 0.00450926 | 0.000000 | 0.107231 | 1.000000 | 0 |
| 2019 | 2020 | 89,112 | 3,294 | 3,294 | 0.963035 | 0.00743708 | 0.000000 | 0.212034 | 1.000000 | 0 |
| 2020 | 2021 | 89,112 | 1,919 | 1,919 | 0.978465 | 0.00307435 | 0.000000 | 0.056824 | 1.000000 | 0 |
| 2021 | 2022 | 89,112 | 4,318 | 4,318 | 0.951544 | 0.01217758 | 0.000000 | 0.534079 | 1.000000 | 0 |
| 2022 | 2023 | 89,112 | 2,841 | 2,841 | 0.968119 | 0.00382940 | 0.000000 | 0.060155 | 1.000000 | 0 |
| 2023 | 2024 | 89,112 | 4,252 | 4,252 | 0.952285 | 0.01560742 | 0.000000 | 0.768506 | 1.000000 | 0 |
| 2024 | 2025 | 89,112 | 6,751 | 6,751 | 0.924241 | 0.03053283 | 0.045494 | 0.968040 | 1.000000 | 0 |

## Feature ranges and missingness

| Field | Minimum | Maximum | Missing rows |
|---|---:|---:|---:|
| `built_up_share` | 0.00000000 | 1.00000000 | 0 |
| `forest_shrub_share_2km` | 0.00000000 | 1.00000000 | 0 |
| `mean_slope_2km` | 0.00011163 | 26.64048958 | 0 |
| `fire_years_previous_10y_2km` | 0.00000000 | 10.00000000 | 0 |
| `warm_season_mean_2m_temperature_c` | 16.23439941 | 26.70394287 | 0 |
| `warm_season_total_precipitation_mm` | 2.72588873 | 380.67654264 | 0 |
| `warm_season_mean_soil_water_layer1` | 0.04098511 | 0.34236145 | 0 |
| `warm_season_max_monthly_2m_temperature_c` | 18.34780273 | 30.90981445 | 0 |
| `warm_season_min_monthly_soil_water_layer1` | 0.02383423 | 0.34114075 | 0 |
| `burned_share_next_year` | 0.00000000 | 1.00000000 | 0 |

The validated nearest-valid-land fallback resolved all 1,506 systematic coastal cells without new acquisition. Climate missingness is now zero; maximum fallback distance was 13.962 km. No interpolation, downscaling, zero substitution, cell exclusion, or T+1 information was used.

## Determinism and leakage

Corrected precipitation was used for 2022 and 2023. No outcome-year information entered predictors. Annual repaired ICNF polygons were locally unioned before intersection, preventing double counting.

Three representative national batches (`x00_y10`, `x06_y21`, `x10_y21`) were re-derived in memory. Every slope, CLC, ICNF, ERA5 and assembled batch value was exactly identical; no files were published by the rerun.

## Component duration evidence

These are minimum observed first-to-last atomic batch-publication spans, not CPU times; they exclude work before the first published batch.

| Component | Seconds |
|---|---:|
| grid | 42.56 |
| icnf_geometry_repair | 26.50 |
| slope | 129.76 |
| clc | 519.09 |
| era5 | 22.91 |
| icnf_components | 357.47 |
| panel_batches | 45.04 |

Final validation, including the three-batch deterministic rerun, took 46.58 seconds.

Full machine-readable metrics, ranges, missingness, quantiles, and repair logs are stored at `data/processed/national_panel_2015_2024_validation.json`.
