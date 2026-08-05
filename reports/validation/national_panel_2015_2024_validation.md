# National 2015-2024 cell-year panel validation

**National panel validated — panel EDA may begin.**

This decision authorises panel EDA only. It does not establish modelling readiness, which still requires missing-data treatment and target-distribution analysis.

## Identity and batching

- Canonical EPSG:3763 grid cells: 89,112.
- Expected and actual rows: 891,120.
- Deterministic 20 km spatial tiles, atomic Parquet batches, checksum manifests, completed-batch reuse, and overwrite protection were used.
- Schema: 19 ordered fields with validated Arrow types; identifiers and source metadata have no missing values.
- Panel SHA-256: `8B179BFF83CB42C8D3170FA0FBD85C0AD7884EC808DA06A17338A4FDB03E732E`.

## Target and climate completeness by year

| T | Outcome | Rows | Positive rows | Positive cells | Zero proportion | Mean | Q95 | Q99 | Max | Joint climate-missing rows |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015 | 2016 | 89,112 | 5,773 | 5,773 | 0.935216 | 0.01753729 | 0.007240 | 0.729508 | 1.000000 | 1,506 |
| 2016 | 2017 | 89,112 | 12,122 | 12,122 | 0.863969 | 0.06286468 | 0.696303 | 1.000000 | 1.000000 | 1,506 |
| 2017 | 2018 | 89,112 | 1,447 | 1,447 | 0.983762 | 0.00448297 | 0.000000 | 0.038782 | 1.000000 | 1,506 |
| 2018 | 2019 | 89,112 | 3,004 | 3,004 | 0.966290 | 0.00450926 | 0.000000 | 0.107231 | 1.000000 | 1,506 |
| 2019 | 2020 | 89,112 | 3,294 | 3,294 | 0.963035 | 0.00743708 | 0.000000 | 0.212034 | 1.000000 | 1,506 |
| 2020 | 2021 | 89,112 | 1,919 | 1,919 | 0.978465 | 0.00307435 | 0.000000 | 0.056824 | 1.000000 | 1,506 |
| 2021 | 2022 | 89,112 | 4,318 | 4,318 | 0.951544 | 0.01217758 | 0.000000 | 0.534079 | 1.000000 | 1,506 |
| 2022 | 2023 | 89,112 | 2,841 | 2,841 | 0.968119 | 0.00382940 | 0.000000 | 0.060155 | 1.000000 | 1,506 |
| 2023 | 2024 | 89,112 | 4,252 | 4,252 | 0.952285 | 0.01560742 | 0.000000 | 0.768506 | 1.000000 | 1,506 |
| 2024 | 2025 | 89,112 | 6,751 | 6,751 | 0.924241 | 0.03053283 | 0.045494 | 0.968040 | 1.000000 | 1,506 |

## Feature ranges and missingness

| Field | Minimum | Maximum | Missing rows |
|---|---:|---:|---:|
| `built_up_share` | 0.00000000 | 1.00000000 | 0 |
| `forest_shrub_share_2km` | 0.00000000 | 1.00000000 | 0 |
| `mean_slope_2km` | 0.00011163 | 26.64048958 | 0 |
| `fire_years_previous_10y_2km` | 0.00000000 | 10.00000000 | 0 |
| `warm_season_mean_2m_temperature_c` | 16.23439941 | 26.70394287 | 15,060 |
| `warm_season_total_precipitation_mm` | 2.72588873 | 380.67654264 | 15,060 |
| `warm_season_mean_soil_water_layer1` | 0.04098511 | 0.34236145 | 15,060 |
| `burned_share_next_year` | 0.00000000 | 1.00000000 | 0 |

ERA5-Land water-mask records were retained with all three climate fields missing; no zero substitution, imputation, exclusion, or nearest-cell substitution was applied. Affected cells: 1,506; affected rows: 15,060 (1.6900% of the panel). Of those cells, 300 are partial-land coastal cells and the remainder are full 1 km land cells whose containing coarse ERA5-Land cell is water-masked.

## Pilot regression and leakage

All 40 representative rows passed the pilot regression. CLC and ICNF areas permit only floating-roundoff tolerance; climate and historical counts require exact equality; slope permits 0.25 degrees solely for fixed national raster alignment. Corrected precipitation was used for 2022 and 2023. No outcome-year information entered predictors. Annual repaired ICNF polygons were locally unioned before intersection, preventing double counting.

Three representative national batches (`x00_y10`, `x06_y21`, `x10_y21`) were re-derived in memory. Every slope, CLC, ICNF, ERA5 and assembled batch value was exactly identical; no files were published by the rerun.

## Component duration evidence

These are minimum observed first-to-last atomic batch-publication spans, not CPU times; they exclude work before the first published batch.

| Component | Seconds |
|---|---:|
| grid | 42.56 |
| icnf_geometry_repair | 26.50 |
| slope | 129.76 |
| clc | 519.09 |
| era5 | 12.25 |
| icnf_components | 357.47 |
| panel_batches | 50.54 |

Final validation, including the three-batch deterministic rerun, took 75.31 seconds.

Full machine-readable metrics, ranges, missingness, quantiles, repair logs, and regression differences are stored at `data/processed/national_panel_2015_2024_validation.json`.
