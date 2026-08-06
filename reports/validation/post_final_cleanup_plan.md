# Post-final cleanup plan

This plan follows the completed final temporal evaluation. It does not authorise
deletion, raw-data modification, model retuning, or a model map before the
annual source-input preflight passes.

## Keep and preserve

- Immutable raw archives under `data/raw/`, their checksums, and source-registry
  records.
- The canonical seven-feature panel, the backward training extension, final-test
  metrics, and the versioned nine-feature operational model/panel through
  observed outcome 2025.
- Historical reports as traceable records. Mark them superseded where necessary;
  do not rewrite them to erase their original decision context.
- The historical recurrence screening GeoPackage and QGIS project. They remain
  the presentation output and are not model predictions.

## Safe code cleanup, in order

1. Extract `HurdleHistGradientRegressor` from `src/model_v2_experiments.py` to a
   small stable estimator module while keeping an import-compatible re-export so
   existing joblib artifacts can still load.
2. Extract the duplicated ERA5 monthly-extreme assignment logic from
   `src/extended_model_refit.py` and `src/extended_final_test.py` into one
   tested helper. Preserve the containing-cell/nearest-valid-land fallback and
   corrected-precipitation selection rules.
3. Add one command that verifies, but does not rebuild, each registered output:
   panel, extension, final-test predictions, fixed model, screening GeoPackage,
   and QGIS project paths.
4. Move archival first-round model reports under a clearly named
   `reports/validation/archive/` directory only after references are updated and
   checksums are recorded. Do not delete them.
5. Keep notebooks as concise readers of the reports and source artifacts;
   migrate any remaining calculation logic into `src/` before modifying cells.

## Documentation and presentation cleanup

1. Regenerate the presentation's model-performance figure from
   `final_temporal_test_metrics.json`; retain the historical-screening visuals
   unchanged.
2. Add the final-model finding and its 2024 underprediction limitation to the
   presentation narrative. Do not present the model as a probability or a
   location recommendation.
3. Update the presentation-validation report after the deck is regenerated.
4. When annual source validation passes, create one separate forecast GeoPackage
   and QGIS layer from the versioned score table. Preserve the historical layer
   separately; never relabel it as a forecast or duplicate the full panel geometry.

## Remaining scientific work before any stronger claim

- Assess regional stability and calibration/underprediction by year.
- Decide whether a calibrated two-stage or year-aware approach is scientifically
  justified using a new, independently governed evaluation design; do not tune
  against the completed final test.
- Obtain a later independent period before claiming deployment or annual
  operational usefulness.
- Keep `burned_next_year` and classification metrics deferred unless a threshold
  and responsible-use decision are separately documented.
