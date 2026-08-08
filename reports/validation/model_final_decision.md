# Final model decision

## Decision

The frozen nine-feature two-part burned-share regression model (technical term:
hurdle model) is retained as the project's
reproducible **continuous comparative burned-share model**. The historical
recurrence baseline remains the required transparent comparator.

The model is **not accepted for a safety classification or purchase
recommendation**. In particular, it substantially underpredicted the high
observed mean burned share for predictor year T=2024 (outcome year 2025). A
continuous estimated burned share is not a probability and must not be
presented as one. It may be published only as a cautious, year-specific
comparative estimate after its annual scoring inputs pass validation.

## Method rationale

The retained `HurdleHistGradientRegressor` is the project's two-part
scikit-learn regression model:
`HistGradientBoostingClassifier` estimates whether any burning occurs, and
`HistGradientBoostingRegressor` estimates burned share among positive outcomes.
The final estimate is their product. Histogram gradient boosting uses many
small decision trees and is suitable for the large tabular panel because it can
represent non-linear relationships and interactions among the nine approved
fire-history, landscape, terrain, and climate predictors without assuming a
fixed linear relationship. The two-part structure is appropriate because the
continuous target has many exact zeros alongside positive burned shares. This
selection establishes an associative predictive method, not a causal claim.

## Held-out evidence

On the one frozen final temporal test (T=2022-2024), the nine-feature two-part
regression model
had lower all-row MAE than the historical baseline (0.02140 vs 0.02919) and
higher tie-aware top-20% burned-share-mass capture (0.6003 vs 0.4017). Its RMSE
was effectively tied but marginally higher (0.11070 vs 0.11059), and its
positive-row MAE was also marginally higher (0.31318 vs 0.31036).

The high-burned outcome associated with predictor year T=2024 illustrates the
main limitation: the hurdle's mean prediction was 0.00622 while observed mean
burned share was 0.03053. This
temporal non-stationarity means the model may support methodological comparison
and further research, but it is not calibrated enough for a residential
decision claim.

## Reusable artefact

After the final evaluation was recorded, the unchanged nine-feature
specification was refitted on all labelled predictor years T=2010-2024, whose
observed outcomes span 2011-2025. The saved annual-scoring artifact is
`data/processed/final_model_2010_2024/nine_feature_hurdle.joblib`; its feature
order, training cutoff, and checksum are in the adjacent `model_metadata.json`.
The previous T=2010-2021 refit remains an archived reproducibility artifact.

The final-test evidence is in `final_temporal_test_2022_2024.md` and the
machine-readable metrics are in
`data/processed/extended_model_selection_2010_2021/final_temporal_test_metrics.json`.

## Output policy

Keep the validated historical recurrence screening GeoPackage and QGIS project
as supporting evidence. When T-only inputs are complete, publish a separate,
clearly named annual comparative-estimate layer with its forecast year, model
checksum, and source cutoff. Do not label locations as safe, low-risk,
predicted-safe, or suitable to buy; accompany every model layer with the
calibration and temporal-stability limitation above.
