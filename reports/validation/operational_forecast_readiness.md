# Operational annual forecast readiness

## Fixed model

This is a two-part burned-share regression model. The implementation and saved
artefact retain the technical name **hurdle model**: one component estimates
whether burning occurs, and the other estimates the positive burned share.

- Model: fixed nine-feature two-part burned-share regression model (technical term: hurdle model), refit on predictor years T=2010-2024, with observed ICNF outcomes 2011-2025.
- Artifact: `data/processed/final_model_2010_2024/nine_feature_hurdle.joblib` (SHA-256 `3923A98D8921401435976530041B89F2DE128006815AA8B6607841C66EED3B0F`).
- Model selection remains the completed frozen T=2022-2024 final temporal test; no post-test tuning occurred.

## 2026 scoring contract

- Predictor year: T=2025; estimated outcome year: 2026.
- ICNF historical-fire years: 2015-2024 only.
- The scoring matrix has all nine predictors and intentionally has no `burned_share_next_year` value.
- ERA5-Land remains coarse containing-cell context, with the accepted nearest-valid-land fallback where required; it is not interpolated or downscaled.

## Current readiness

**Status: `scored_and_validated`.**
All sources passed validation and the 2026 matrix, score table, and QGIS-ready GeoPackage were published. See `operational_forecast_2026_validation.md`.

## Annual rebuild rule

For forecast year Y, freeze the selected specification, refit only through labelled predictor year Y-2 (whose observed target is Y-1), derive predictors from Y-1, then score Y. Record every source checksum and do not calculate or use the unknown target for Y.

## Annual score artifacts

- `data/processed/operational_forecasts/forecast_2026_nine_feature_matrix.parquet`: one unlabelled row per 1 km cell, with all nine predictors and source metadata.
- `data/processed/operational_forecasts/forecast_2026_scores.parquet`: `cell_id`, forecast/input years, continuous estimate, rank metadata, model checksum, and score status.
- `data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg`: one EPSG:3763 geometry per canonical cell joined to the score table; it does not repeat the complete cell-year panel.

## Buyer-facing interpretation

A published score may compare broad 1 km mainland cells by estimated wildfire exposure for the stated year. It is not a property-level forecast, probability, safety guarantee, insurance quote, or buy/do-not-buy recommendation. Historical recurrence remains contextual evidence alongside, not a substitute for, the forecast layer.
