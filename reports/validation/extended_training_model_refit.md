# Model v2 training-only refit

This controlled refit uses Model v2, selected from the complete T=2020-2021 validation comparison. It fits T=2010-2019 and validates T=2020-2021. T=2022-2024 were not opened or used.

## Candidate comparison

| Model | Validation MAE | Validation RMSE | Positive-row MAE | Positive-cell capture at 20% | Burned-share mass capture at 20% |
|---|---:|---:|---:|---:|---:|
| Historical recurrence baseline | 0.02142102 | 0.06954565 | 0.20598098 | 0.5594 | 0.4090 |
| Nine-feature two-part regression | 0.01402701 | 0.06944214 | 0.20765697 | 0.5822 | 0.6082 |

## Validation by year

| Validation T | Model | MAE | RMSE | Positive-row MAE | Positive-cell capture at 20% |
|---:|---|---:|---:|---:|---:|
| 2020 | Historical recurrence baseline | 0.01736166 | 0.04071446 | 0.13017133 | 0.6107 |
| 2020 | Nine-feature two-part regression | 0.00915584 | 0.04045082 | 0.13330761 | 0.5862 |
| 2021 | Historical recurrence baseline | 0.02548037 | 0.08952947 | 0.23967220 | 0.5352 |
| 2021 | Nine-feature two-part regression | 0.01889817 | 0.08948829 | 0.24069921 | 0.5424 |

## Guardrails

- The historical baseline is a training-only empirical mapping from the strict T-10 through T-1 recurrence count to expected next-year burned share.
- The two-part regression output is a continuous expected burned share, not a buyer-facing probability or decision threshold.
- This report is validation evidence only; it contains no final-temporal-test result.
