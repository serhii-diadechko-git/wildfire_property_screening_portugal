# Frozen final temporal test — T=2022-2024

This is a single held-out evaluation under the committed protocol. No model fitting, tuning, feature selection, or threshold selection was performed on these years.

## Overall results

| Model | MAE | RMSE | Positive-row MAE | Positive-cell capture at 20% | Burned-share mass capture at 20% |
|---|---:|---:|---:|---:|---:|
| Historical recurrence baseline | 0.02918638 | 0.11059461 | 0.31035855 | 0.4930 | 0.4017 |
| Accepted nine-feature Model V2 | 0.02091322 | 0.11099527 | 0.31437449 | 0.4843 | 0.5716 |

## Results by predictor year

| T | Model | MAE | RMSE | Positive-row MAE | Positive-cell capture at 20% |
|---:|---|---:|---:|---:|---:|
| 2022 | Accepted nine-feature Model V2 | 0.00785114 | 0.04599336 | 0.11520591 | 0.4910 |
| 2023 | Accepted nine-feature Model V2 | 0.02028635 | 0.10595707 | 0.31847112 | 0.5118 |
| 2024 | Accepted nine-feature Model V2 | 0.03460216 | 0.15368006 | 0.39560972 | 0.4502 |

## Mean-prediction check

| T | Observed mean burned share | Baseline mean prediction | Model V2 mean prediction |
|---:|---:|---:|---:|
| 2022 | 0.00382940 | 0.01440818 | 0.00445096 |
| 2023 | 0.01560742 | 0.01421810 | 0.00569917 |
| 2024 | 0.03053283 | 0.01402081 | 0.00543579 |

## Scope limitation

The accepted nine-feature Model V2 has lower overall MAE and stronger burned-share-mass ranking than the baseline, but it materially underpredicts the high-burned T=2024 outcome. The model estimates comparative next-year burned share for 1 km mainland cells; it is not a probability, safety guarantee, property-level forecast, or purchase recommendation.
