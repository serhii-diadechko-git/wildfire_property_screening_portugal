# Frozen final temporal test — T=2022-2024

This is a single held-out evaluation under the committed protocol. No model fitting, tuning, feature selection, or threshold selection was performed on these years.

## Overall results

| Model | MAE | RMSE | Positive-row MAE | Positive-cell capture at 20% | Burned-share mass capture at 20% |
|---|---:|---:|---:|---:|---:|
| Historical recurrence baseline | 0.02918638 | 0.11059461 | 0.31035855 | 0.4930 | 0.4017 |
| Nine-feature two-part regression | 0.02140124 | 0.11069745 | 0.31318128 | 0.5004 | 0.6003 |

## Results by predictor year

| T | Model | MAE | RMSE | Positive-row MAE | Positive-cell capture at 20% |
|---:|---|---:|---:|---:|---:|
| 2022 | Nine-feature two-part regression | 0.00822522 | 0.04596327 | 0.11472921 | 0.4921 |
| 2023 | Nine-feature two-part regression | 0.02079218 | 0.10548191 | 0.31655982 | 0.5461 |
| 2024 | Nine-feature two-part regression | 0.03518633 | 0.15337119 | 0.39456727 | 0.4488 |

## Mean-prediction check

| T | Observed mean burned share | Baseline mean prediction | Two-part regression mean prediction |
|---:|---:|---:|---:|
| 2022 | 0.00382940 | 0.01440818 | 0.00488099 |
| 2023 | 0.01560742 | 0.01421810 | 0.00641105 |
| 2024 | 0.03053283 | 0.01402081 | 0.00621745 |

## Scope limitation

The two-part regression model (technical term: hurdle model) has lower overall MAE and stronger burned-share-mass ranking than the baseline, but it materially underpredicts the high-burned T=2024 outcome. The model estimates comparative next-year burned share for 1 km mainland cells; it is not a probability, safety guarantee, property-level forecast, or purchase recommendation.
