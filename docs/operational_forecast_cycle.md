# Annual operational forecast cycle

## The simple idea

The project has two separate jobs:

1. **Learn from completed years.** For predictor year `T`, the observed target exists only after ICNF publishes burned areas for `T+1`. Those completed rows are used for training, validation, testing, and later refitting.
2. **Estimate the next year.** For forecast year `Y`, use inputs from completed year `T=Y-1` and create an unlabelled score. The target for `Y` is intentionally unknown.

This is not a change to the scientific model. It is the normal deployment step after historical model selection: evaluate a fixed method on years with known outcomes, use it for the next year, then evaluate that new score when the outcome becomes available.

## What has already been evaluated

| Stage | Predictor years `T` | Observed targets | Purpose |
|---|---:|---:|---|
| Development fit | 2010-2019 | 2011-2020 | Fit candidate methods. |
| Validation | 2020-2021 | 2021-2022 | Compare frozen candidates. |
| Final temporal test | 2022-2024 | 2023-2025 | One untouched evidence check. |

The final evaluation used continuous-regression diagnostics, not classification accuracy: all-row MAE/RMSE, positive-target MAE/RMSE, mean predicted versus observed burned share, and ranking capture@20%. See [`reports/validation/model_final_decision.md`](../reports/validation/model_final_decision.md).

## Current 2026 estimate

The published 2026 output is forward-looking, so it does **not** have an observed target or error metric yet:

| Item | Value |
|---|---|
| Forecast year `Y` | 2026 |
| Predictor/input year `T` | 2025 |
| ICNF history used | 2015-2024 only (`T-10` through `T-1`) |
| Climate used | JJAS 2025 ERA5-Land only |
| Target in scoring matrix | Absent by design |
| Result | One continuous comparative estimate for each 1 km mainland cell |

After final evaluation was recorded, the model was refit with all labelled rows through `T=2024` / observed outcome 2025. This uses more completed training evidence without revisiting candidate selection, model settings, or the held-out-test decision.

Current outputs:

- `data/processed/operational_forecasts/forecast_2026_nine_feature_matrix.parquet`
- `data/processed/operational_forecasts/forecast_2026_scores.parquet`
- `data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg`
- `qgis/wildfire_exposure_screening_portugal_2026.qgz`

They are comparative estimated burned shares, not probabilities, property-level safety assessments, insurance estimates, or purchase decisions.

## What happens when the next annual data arrive

When ICNF publishes complete 2026 burned-area data, it becomes the observed target for the already published `T=2025` / forecast-2026 score.

The controlled 2027 cycle is:

1. Validate/register ICNF 2026 and compare the published 2026 scores with observed per-cell burned share using the predefined regression metrics.
2. Validate/register ERA5-Land JJAS 2026, which supplies climate predictors for `T=2026`.
3. Build/validate the new labelled `T=2025 -> outcome 2026` row using unchanged feature definitions and source-year rules.
4. Refit the **same frozen nine-feature specification** using labelled rows through `T=2025` / outcome 2026. Do not search new settings merely because a new outcome arrived.
5. Derive the target-free `T=2026` matrix and score 2027.
6. Publish a versioned Parquet table, GeoPackage, checksum, validation report, and QGIS layer.

The pattern repeats annually. It is a rolling update, not a new model-selection experiment.

## Reproducible implementation and notebook roles

The code fails closed: it refuses scoring if a required T-only input is absent, and the scoring matrix rejects an observed target column.

For the current 2026 cycle, run from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_operational_forecast.py
.\.venv\Scripts\python.exe scripts\score_operational_forecast.py
```

The second command safely revalidates existing published artifacts rather than overwriting them. Current scripts are intentionally pinned to the validated 2026 cutoff. Before a future-year run, first add/validate the new annual source records and labelled row, then update the controlled annual extension step; do not simply change a year number.

Notebooks are review layers:

- `04_modelling.ipynb` verifies the saved nine-feature model contract, two-part regression components, temporal safeguards, and annual scoring lifecycle; it does not refit or retune the model.
- `05_evaluation_recommendations.ipynb` audits the validated historical GeoPackage and its QGIS handoff.
- `06_final_charts.ipynb` is the single final narrative for EDA, held-out model evidence, the historical/official comparison, and the separate 2026 comparative estimate.
- Open `qgis/wildfire_exposure_screening_portugal_2026.qgz` for the current annual output.

After an intentional annual update, run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_operational_forecast tests.test_era5_land_validation -v
```
