# National panel model-readiness EDA

**Model-design gate passed — modelling may begin.**

This report is descriptive. Final-test years are shown only for temporal-drift assessment; no model was trained, selected or evaluated.

## Target distribution

Overall zero proportion: 94.8693%.

| T | Split | Zero proportion | Positive rows | Mean | P95 | P99 | Positive median |
|---:|---|---:|---:|---:|---:|---:|---:|
| 2015 | train | 93.5216% | 5,773 | 0.01753729 | 0.007240 | 0.729508 | 0.094914 |
| 2016 | train | 86.3969% | 12,122 | 0.06286468 | 0.696303 | 1.000000 | 0.378976 |
| 2017 | train | 98.3762% | 1,447 | 0.00448297 | 0.000000 | 0.038782 | 0.091705 |
| 2018 | train | 96.6290% | 3,004 | 0.00450926 | 0.000000 | 0.107231 | 0.027202 |
| 2019 | train | 96.3035% | 3,294 | 0.00743708 | 0.000000 | 0.212034 | 0.038604 |
| 2020 | validation | 97.8465% | 1,919 | 0.00307435 | 0.000000 | 0.056824 | 0.049114 |
| 2021 | validation | 95.1544% | 4,318 | 0.01217758 | 0.000000 | 0.534079 | 0.075544 |
| 2022 | final_test | 96.8119% | 2,841 | 0.00382940 | 0.000000 | 0.060155 | 0.019840 |
| 2023 | final_test | 95.2285% | 4,252 | 0.01560742 | 0.000000 | 0.768506 | 0.129671 |
| 2024 | final_test | 92.4241% | 6,751 | 0.03053283 | 0.045494 | 0.968040 | 0.237473 |

The continuous target remains scientifically meaningful, but aggregate MAE/RMSE alone could reward near-zero predictions. The model design therefore retains continuous regression and adds a zero-prediction baseline, positive-row error reporting, and a compound/Tweedie candidate without defining the deferred classification threshold.

## Predictor completeness, drift and redundancy

All nine predictors and the target have zero missing values. Standardized mean differences below compare each later split with training:

| Split | Predictor | Standardized mean difference |
|---|---|---:|
| validation | `built_up_share` | 0.004 |
| validation | `forest_shrub_share_2km` | -0.023 |
| validation | `mean_slope_2km` | 0.000 |
| validation | `fire_years_previous_10y_2km` | 0.090 |
| validation | `warm_season_mean_2m_temperature_c` | -0.188 |
| validation | `warm_season_total_precipitation_mm` | 0.678 |
| validation | `warm_season_mean_soil_water_layer1` | 0.214 |
| validation | `warm_season_max_monthly_2m_temperature_c` | 0.147 |
| validation | `warm_season_min_monthly_soil_water_layer1` | -0.064 |
| final_test | `built_up_share` | 0.004 |
| final_test | `forest_shrub_share_2km` | -0.023 |
| final_test | `mean_slope_2km` | 0.000 |
| final_test | `fire_years_previous_10y_2km` | -0.002 |
| final_test | `warm_season_mean_2m_temperature_c` | 0.089 |
| final_test | `warm_season_total_precipitation_mm` | 0.849 |
| final_test | `warm_season_mean_soil_water_layer1` | 0.289 |
| final_test | `warm_season_max_monthly_2m_temperature_c` | 0.409 |
| final_test | `warm_season_min_monthly_soil_water_layer1` | -0.126 |

High predictor redundancy: `warm_season_mean_2m_temperature_c` / `warm_season_max_monthly_2m_temperature_c`: 0.920; `warm_season_mean_soil_water_layer1` / `warm_season_min_monthly_soil_water_layer1`: 0.850

The largest split drift is JJAS precipitation: validation is +0.678 and final test +0.849 training standard deviations. Final-test years contain 9,332 precipitation rows above the training 3-IQR upper fence, but all remain inside the physical feature contract. The built-up-share training IQR is zero because most cells have zero mapped built-up area, so its 3-IQR flag counts non-zero values rather than implausible extremes.

Exact distributions, annual means, correlations and 3-IQR outlier-screen counts are stored in `reports/validation/national_panel_model_readiness_eda.json`. Extreme values remain within the feature contract.
