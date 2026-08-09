# Final model decision

## Decision

The frozen Model V2 nine-feature two-stage burned-share regression is retained as the project's
reproducible **continuous comparative burned-share model**. The historical
recurrence baseline remains the required transparent comparator.

The model is **not accepted for a safety classification or purchase
recommendation**. In particular, it substantially underpredicted the high
observed mean burned share for predictor year T=2024 (outcome year 2025). A
continuous estimated burned share is not a probability and must not be
presented as one. It may be published only as a cautious, year-specific
comparative estimate after its annual scoring inputs pass validation.

## Method rationale

Model V2 is implemented as a two-stage scikit-learn regression model. The
internal class identifier is `HurdleHistGradientRegressor`; this legacy
technical name is not the public model name:
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

On the one frozen final temporal test (T=2022-2024), the Model V2 nine-feature
two-stage regression had lower all-row MAE than the historical baseline
(0.02091 vs 0.02919) and higher tie-aware top-20% burned-share-mass capture
(0.5716 vs 0.4017). Its RMSE was marginally higher (0.11100 vs 0.11059), and
its positive-row MAE was also marginally higher (0.31437 vs 0.31036).

The high-burned outcome associated with predictor year T=2024 illustrates the
main limitation: Model V2's mean prediction for that year was 0.00544 while
observed mean burned share was 0.03053. This
temporal non-stationarity means the model may support methodological comparison
and further research, but it is not calibrated enough for a residential
decision claim.

## Reusable artefact

After the final evaluation was recorded, the unchanged Model V2 nine-feature
specification was refitted on all labelled predictor years T=2010-2024, whose
observed outcomes span 2011-2025. The saved annual-scoring artifact is
`data/processed/final_model_2010_2024/nine_feature_hurdle.joblib`; this is a
legacy internal artifact filename for Model V2. Its feature order, training
cutoff, and checksum are in the adjacent `model_metadata.json`.
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
