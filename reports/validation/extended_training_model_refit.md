# Extended training-only model refit

This controlled refit uses T=2010-2019 for fitting and T=2020-2021 for validation. T=2022-2024 were not opened or used.

## Candidate comparison

| Model | Validation MAE | Validation RMSE | Positive-row MAE | Positive-cell capture at 20% | Burned-share mass capture at 20% |
|---|---:|---:|---:|---:|---:|
| Historical recurrence baseline | 0.02142102 | 0.06954565 | 0.20598098 | 0.5594 | 0.4090 |
| Nine-feature hurdle | 0.01467356 | 0.06959817 | 0.20762409 | 0.5562 | 0.5623 |

## Validation by year

| Validation T | Model | MAE | RMSE | Positive-row MAE | Positive-cell capture at 20% |
|---:|---|---:|---:|---:|---:|
| 2020 | Historical recurrence baseline | 0.01736166 | 0.04071446 | 0.13017133 | 0.6107 |
| 2020 | Nine-feature hurdle | 0.00985070 | 0.04035254 | 0.13293975 | 0.5810 |
| 2021 | Historical recurrence baseline | 0.02548037 | 0.08952947 | 0.23967220 | 0.5352 |
| 2021 | Nine-feature hurdle | 0.01949641 | 0.08977462 | 0.24081521 | 0.5164 |

## Guardrails

- The historical baseline is a training-only empirical mapping from the strict T-10 through T-1 recurrence count to expected next-year burned share.
- The hurdle output is a continuous expected burned share, not a buyer-facing probability or decision threshold.
- This report is validation evidence only; it contains no final-temporal-test result.
