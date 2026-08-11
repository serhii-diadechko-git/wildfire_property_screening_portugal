# Annual operational estimate runbook

This document is the controlled runbook for evaluating an existing annual
estimate, adding newly completed data, refitting the unchanged final model
specification, and publishing the next estimate. For the scientific learning
logic, target formula, model components, and temporal split, first read
[From historical evidence to the 2026 estimate](model_learning_and_2026_estimate.md).

## Operational rule

For forecast year `Y`:

1. the score uses predictor inputs from completed year `T=Y-1`;
2. the historical-fire feature uses `T-10` through `T-1` only;
3. `burned_share_next_year` is absent from the scoring matrix;
4. the saved final specification is refit only through the newest predictor
   year whose `T+1` ICNF outcome is available; and
5. the published score is evaluated only after ICNF releases the observed
   burned-area outcome for `Y`.

This is a rolling data update, not a new model-selection experiment. Changing
features, thresholds, algorithms, or model parameters requires a separately
versioned research and validation cycle.

## Current published cycle

| Item | Current value |
|---|---|
| Forecast year `Y` | 2026 |
| Predictor year `T` | 2025 |
| Historical ICNF window | 2015-2024 |
| Climate input | ERA5-Land JJAS 2025 |
| Operational refit evidence | `T=2010-2024`, observed outcomes 2011-2025 |
| Target in scoring matrix | Absent by design |
| Coverage | 89,112 mainland Portugal 1 km cells |
| Independent evaluation | Possible only after ICNF publishes the 2026 outcome |

## Current commands

Run from the repository root after required raw inputs have passed preflight:

```text
python scripts/prepare_operational_forecast.py
python scripts/score_operational_forecast.py
```

The scoring command validates and reuses matching published artifacts rather
than silently overwriting them. The current scripts are intentionally pinned to
the validated 2026 source cutoff. A future annual cycle must first register and
validate its new source years and update the controlled year configuration.

For a complete clean reproduction of all derived project outputs, use the root
workflow documented in the [project README](../README.md):

```text
python scripts/run_project.py --mode reproduce --confirm-rebuild
```

## Current outputs

| Path | Purpose |
|---|---|
| `data/processed/operational_forecasts/forecast_2026_nine_feature_matrix.parquet` | Target-free 2025 predictor matrix. |
| `data/processed/final_model_2010_2024/nine_feature_hurdle.joblib` | Saved operational model; the filename is retained for backward compatibility. |
| `data/processed/final_model_2010_2024/model_metadata.json` | Feature order, evidence cutoff, model version, and checksums. |
| `data/processed/operational_forecasts/forecast_2026_scores.parquet` | Canonical tabular 2026 estimates. |
| `data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg` | QGIS-ready 2026 layer. |
| `data/processed/web_map/estimated_comparative_wildfire_exposure_2026.geojson` | Browser-ready derivative of the spatial output. |
| `qgis/wildfire_exposure_screening_portugal_2026.qgz` | Portable QGIS presentation project. |

These outputs are continuous comparative estimated burned shares. They are not
observed 2026 outcomes, probabilities that whole cells will burn,
property-level assessments, insurance estimates, or purchase recommendations.

## Controlled 2027 update

After the required official 2026 data become available:

1. Register and validate ICNF 2026 without modifying the raw archive.
2. Compare the already published 2026 estimates with observed 2026 per-cell
   burned share using the predefined regression metrics.
3. Register and validate ERA5-Land JJAS 2026 for predictor year `T=2026`.
4. Build and validate the labelled `T=2025 -> outcome 2026` rows using the
   unchanged feature definitions and source-year rules.
5. Refit the unchanged final specification through `T=2025` / outcome 2026.
6. Build the target-free `T=2026` matrix and estimate 2027.
7. Publish versioned Parquet, metadata, validation report, GeoPackage, web-map,
   and QGIS outputs.

The same pattern repeats annually. Do not tune the model merely because a new
outcome has arrived.

## Fail-closed safeguards

The operational code must stop rather than publish when:

- a required predictor-year source is missing or fails validation;
- an observed target appears in the target-free scoring matrix;
- the feature names or order differ from saved model metadata;
- the model evidence cutoff is later than the newest observed outcome;
- required cell coverage, uniqueness, ranges, or climate assignments fail; or
- an existing artifact does not match its recorded configuration and checksum.

After an intentional annual update, run the focused checks:

```text
python -m unittest tests.test_operational_forecast tests.test_era5_land_validation -v
python scripts/run_project.py --mode validate
```

Notebooks are review and presentation layers, not the annual scoring engine.
Their roles and execution order are documented in
[notebooks/README.md](../notebooks/README.md).
