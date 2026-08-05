# Final model decision

## Decision

The frozen nine-feature hurdle regressor is retained as the project's
reproducible **continuous comparative burned-share model**. The historical
recurrence baseline remains the required transparent comparator.

The model is **not accepted for buyer-facing prediction, safety classification,
or purchase recommendation**. In particular, it substantially underpredicted
the high observed mean burned share for predictor year T=2024. A continuous
estimated burned share is not a probability and must not be presented as one.

## Held-out evidence

On the one frozen final temporal test (T=2022-2024), the nine-feature hurdle
had lower all-row MAE than the historical baseline (0.02140 vs 0.02919) and
higher tie-aware top-20% burned-share-mass capture (0.6003 vs 0.4017). Its RMSE
was effectively tied but marginally higher (0.11070 vs 0.11059), and its
positive-row MAE was also marginally higher (0.31318 vs 0.31036).

The high-burned 2024 outcome illustrates the main limitation: the hurdle's mean
prediction was 0.00622 while observed mean burned share was 0.03053. This
temporal non-stationarity means the model may support methodological comparison
and further research, but it is not calibrated enough for a residential
decision claim.

## Reusable artefact

After the final evaluation, the unchanged nine-feature specification was
refitted on development years T=2010-2021 only. The held-out final-test years
were excluded. The saved artifact is
`data/processed/final_fixed_spec_model_2010_2021/nine_feature_hurdle.joblib`;
its feature order and training years are recorded in the adjacent
`model_metadata.json`.

The final-test evidence is in `final_temporal_test_2022_2024.md` and the
machine-readable metrics are in
`data/processed/extended_model_selection_2010_2021/final_temporal_test_metrics.json`.

## Output policy

Keep the validated historical recurrence screening GeoPackage and QGIS project
as the buyer-facing capstone output. Do not generate a model-based recommendation
layer or label locations as safe, low-risk, predicted-safe, or suitable to buy.
Any future model map must be clearly named a research/EDA layer and accompanied
by the calibration and temporal-stability limitation above.
