# Final temporal-test protocol — frozen before execution

**Frozen on 2026-08-05, before any T=2022-2024 row is opened for modelling evaluation.**

## Purpose

Perform one retrospective temporal evaluation of two already-frozen continuous
burned-share candidates. This is not tuning, feature selection, threshold
selection, or property-level decision support.

## Data split

| Role | Predictor years T | Observed outcome years |
|---|---:|---:|
| Model fitting | 2010-2019 | 2011-2020 |
| Prior validation | 2020-2021 | 2021-2022 |
| Final temporal test | 2022-2024 | 2023-2025 |

The final test uses only the already validated canonical panel rows. No test
result may change the feature set, hyperparameters, seed, target definition, or
training period for this comparison.

## Frozen candidates

1. **Historical recurrence baseline** — training-period empirical mean of
   `burned_share_next_year` by `fire_years_previous_10y_2km`.
2. **Nine-feature hurdle regressor** — all nine canonical predictors, including
   `warm_season_max_monthly_2m_temperature_c` and
   `warm_season_min_monthly_soil_water_layer1`. Its fixed output is expected
   next-year burned share, not a probability.

Both candidates use the existing fitted artefacts trained only on T=2010-2019.

## Predeclared reporting

Report MAE and RMSE over all rows and positive-target rows, mean observed versus
mean predicted burned share, and tie-aware top-10%/top-20% positive-cell and
burned-share-mass capture. Report overall and separately for each final-test
year. Capture diagnostics describe geographic prioritisation only; they are not
buyer thresholds.

## Interpretation rule

The final report will describe comparative performance and temporal stability.
It will not make a “safe area”, forecast, purchase, or buy/do-not-buy claim.
If the nine-feature model remains suitable, a subsequent fixed-specification
refit may use T=2010-2021 for future use; it must not use T=2022-2024 to change
the model specification.
