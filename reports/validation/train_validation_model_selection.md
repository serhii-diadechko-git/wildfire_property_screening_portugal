# Train/validation regression model selection

> **Historical record — superseded for the final modelling decision.** This report records the original seven-feature, `T=2015–2019` / `T=2020–2021` gate. The later, frozen expanded-training evaluation and its one authorised final temporal test are recorded in `extended_training_model_refit.md`, `final_temporal_test_protocol.md`, `final_temporal_test_2022_2024.md`, and `model_final_decision.md`. This report is retained unchanged as pre-extension evidence.

**No candidate passed the predeclared validation gate.** Final temporal testing must not begin until the model design is reconsidered without consulting final-test outcomes.

No records from final-test years `T=2022-2024` were opened, fitted, tuned, scored, or reported. This report covers training `T=2015-2019` and validation `T=2020-2021` only.

## Data and guardrails

- Canonical panel: `data/processed/national_panel_2015_2024.parquet`; validated SHA-256 `AB5E684BCC670F5BD3A91967CBD1459CE3D4BB11E4AED75DE5C2E7244779C993`.
- Training rows: 445,560.
- Validation rows: 178,224.
- Features, in recorded order: `built_up_share`, `forest_shrub_share_2km`, `mean_slope_2km`, `fire_years_previous_10y_2km`, `warm_season_mean_2m_temperature_c`, `warm_season_total_precipitation_mm`, `warm_season_mean_soil_water_layer1`.
- Target: `burned_share_next_year`; model output: `predicted_burned_share_next_year`, never a probability.
- Final-test rows read: 0; unopened final-test row groups: [7, 8, 9].
- Climate missingness is forbidden after the validated coastal fallback; train/validation missing predictor values: 0.

## Intentionally limited models

- Zero prediction: reference error only, not an acceptable model.
- Historical-fire baseline: training-period empirical mean target for each integer `fire_years_previous_10y_2km` value.
- Random Forest: 60 trees, depth 14, minimum leaf 20, 80% features per split, seed 20260805.
- Tweedie: power 1.5, log link, alpha 0.1; seven predictors standardized using training-fitted parameters only.

No broad hyperparameter search was performed. Physically valid predictor values, including precipitation outside the training distribution, were neither clipped nor removed.

## Overall validation metrics

| Model | MAE all | RMSE all | MAE positive | RMSE positive | Mean predicted | Mean observed | Positive-cell capture@20% |
|---|---:|---:|---:|---:|---:|---:|---:|
| Zero reference | 0.00762597 | 0.06964488 | 0.21791416 | 0.37229261 | 0.00000000 | 0.00762597 | 11.38% |
| Historical-fire baseline | 0.02635544 | 0.07023837 | 0.20462411 | 0.35880641 | 0.02010901 | 0.00762597 | 55.88% |
| Random Forest | 0.02386889 | 0.07630401 | 0.20789846 | 0.36008116 | 0.01739208 | 0.00762597 | 28.62% |
| Tweedie (power 1.5) | 0.02511074 | 0.07045075 | 0.20198220 | 0.35248888 | 0.01921718 | 0.00762597 | 49.46% |

Capture@20% is the fraction of rows with target greater than zero found within the highest-ranked 20% of regression predictions; ties use stable `cell_id`, then year ordering.

## Metrics by validation year

| T | Model | MAE all | RMSE all | MAE positive | RMSE positive | Capture@20% |
|---:|---|---:|---:|---:|---:|---:|
| 2020 | Zero reference | 0.00307435 | 0.03848975 | 0.14276276 | 0.26228638 | 11.20% |
| 2020 | Historical-fire baseline | 0.02232110 | 0.04236590 | 0.12928159 | 0.25099172 | 58.00% |
| 2020 | Random Forest | 0.01717483 | 0.05070835 | 0.13357747 | 0.25433315 | 34.18% |
| 2020 | Tweedie (power 1.5) | 0.01956156 | 0.04295077 | 0.12889863 | 0.24839986 | 52.01% |
| 2021 | Zero reference | 0.01217758 | 0.09066067 | 0.25131285 | 0.41185629 | 11.49% |
| 2021 | Historical-fire baseline | 0.03038978 | 0.08984425 | 0.23810773 | 0.39744236 | 53.66% |
| 2021 | Random Forest | 0.03056295 | 0.09525369 | 0.24092810 | 0.39816291 | 23.25% |
| 2021 | Tweedie (power 1.5) | 0.03065993 | 0.08989910 | 0.23446191 | 0.38992946 | 44.93% |

## Provisional-selection rule

At least 2% lower validation MAE and RMSE than the historical-fire baseline, with capture@20% no lower; choose the qualifying candidate with lowest RMSE.

```json
{
  "random_forest_regressor": {
    "relative_mae_improvement": 0.09434684911116209,
    "relative_rmse_improvement": -0.0863577857652087,
    "capture_not_lower_than_historical_baseline": false,
    "passes_predeclared_gate": false
  },
  "tweedie_regressor": {
    "relative_mae_improvement": 0.04722752491983084,
    "relative_rmse_improvement": -0.0030236926990541146,
    "capture_not_lower_than_historical_baseline": false,
    "passes_predeclared_gate": false
  }
}
```

## Reproducibility checks

- Seed: 20260805.
- Every fitted model produced analytically identical validation predictions on a second fit with the same seed/settings.
- Every saved and reloaded model produced byte-identical validation predictions.
- Source-year checks confirmed outcome `T+1`, climate `T`, fire history `T-10..T-1`, and governed CLC assignment.
- Machine-readable metrics: `reports/validation/train_validation_model_selection.json`.
- Validation predictions: `data/processed/model_selection_2015_2021/validation_predictions.parquet`.
- Model and feature-order metadata: `data/processed/model_selection_2015_2021/artifact_metadata.json`.

This is a model-selection gate, not final-test evaluation, model acceptance, classification, probability calibration, or a predictive recommendation.
