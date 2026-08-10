# Final nine-feature model selection record

## Decision

The **final nine-feature model** is the validation-selected two-stage regression
configuration used by the operational 2026 estimate. It replaced the prior
candidate parameter configuration after a predeclared comparison on the full
development validation period only: predictor years `T=2020-2021`.

The selection decision did **not** read, fit, tune, score, or report rows from
`T=2022-2024`. Only after the final model was frozen was it evaluated once on that held-out
period; that separate evidence is recorded below and in
`reports/validation/final_temporal_test_2022_2024.md`.

## Fixed inputs and comparison

- Training rows: `T=2010-2019` (891,120 cell-year rows).
- Validation rows: `T=2020-2021` (178,224 cell-year rows).
- Features: the fixed nine-predictor contract in `docs/data_dictionary.md`.
- Target: continuous `burned_share_next_year` in `T+1`.
- Seed: `20260805`.
- Five predeclared modest histogram-gradient-boosting configurations; no broad
  search and no feature changes.
- Evidence: `data/processed/extended_model_selection_2010_2021/hyperparameter_experiments/full_training_all_candidates/validation_metrics.json`.

## Result

| Configuration | All-row MAE | All-row RMSE | Positive-row MAE | Positive-cell capture@20% | Burned-share-mass capture@20% |
|---|---:|---:|---:|---:|---:|
| Prior candidate reference | 0.014674 | 0.069598 | 0.207624 | 55.62% | 56.23% |
| **Final nine-feature model selected** | **0.014027** | **0.069442** | 0.207657 | **58.22%** | **60.82%** |

The final nine-feature model was selected because it has the lowest primary all-row MAE and the
strongest two ranking diagnostics among the tested configurations, while also
slightly lowering RMSE. Its positive-row MAE is essentially unchanged
(0.000033 higher), so this is a practical comparative-screening improvement,
not proof of a universally best wildfire model.

## Post-selection held-out test

After the validation decision was fixed, the final nine-feature model was evaluated once on
`T=2022-2024` (267,336 rows). It improved all-row MAE over the historical
recurrence baseline, but its RMSE was marginally higher and high-burn outcomes
remained difficult. The tie-aware top-20% burned-share-mass capture was 57.16%
for V2 versus 40.17% for the baseline. This supports comparative screening, not
precise local forecasting. These final-test results were not used to alter V2
parameters.

## Final-model parameters

The model combines two histogram-gradient-boosting tree ensembles. One estimates
whether a cell is likely to have any burned share; the other estimates the
burned share for positive cases. Their product is the continuous comparative
estimated burned share.

| Component | Learning rate | Iterations | Maximum leaves | Minimum samples per leaf | L2 regularization |
|---|---:|---:|---:|---:|---:|
| Occurrence classifier | 0.07 | 160 | 31 | 80 | 0.02 |
| Positive-share regressor | 0.06 | 210 | 31 | 55 | 0.02 |

Implementation identifier: `v2_validation_selected_20260809`.

## Reproduction and future evaluation

Reproduce the evidence from the repository root after building the labelled
development matrix:

```text
python scripts/run_hyperparameter_experiments.py --full-training --run-name full_training_all_candidates
python scripts/build_model_v2_validation_figures.py
```

The first independent evaluation of the published final-model operational score is
possible only after ICNF publishes the observed 2026 burned-area outcome. Until
then, the 2026 layer is a target-free comparative estimate, not validated
future performance.
