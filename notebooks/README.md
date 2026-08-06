# Notebook guide

The notebooks are reusable data-science review chapters. They load real project
artefacts, run compact validations, show tables/plots, and explain the choices
behind the result. Reusable calculations live in `src/`; the controlled full
pipeline lives in `scripts/`; validation evidence lives in `reports/validation/`.

Notebooks are intentionally not a second implementation of national geospatial
processing. This avoids hidden notebook state, accidental partial rebuilds, and
inconsistent outputs while still giving a reviewer an understandable,
executable analysis narrative.

## Setup

Create the pinned environment described in the root [README](../README.md),
then run:

```text
python scripts/run_project.py --mode preflight
python -m jupyter lab
```

Select the environment's Python kernel: `.venv\Scripts\python.exe` on Windows
or `.venv/bin/python` on Linux/macOS.

## Execution order

1. `00_environment_test.ipynb` — portable environment, pinned-package, EPSG:3763, and in-memory ML/GIS smoke checks; writes no project output.
2. `01_data_collection.ipynb` — immutable source inventory, provenance ledger, and representative archive checks; no download.
3. `02_data_preparation.ipynb` — canonical grid, seven-predictor contract, CLC assignment, and panel-validation evidence.
4. `03_eda.ipynb` — validated panel completeness, zero inflation, target behaviour, predictor correlations, temporal drift, and extreme-value screening.
5. `04_modelling.ipynb` — saved nine-feature hurdle metadata, model components, MAE/RMSE/capture tables, final-test prediction/residual plots, and annual scoring logic; no tuning or retraining.
6. `05_evaluation_recommendations.ipynb` — observed historical screening and official ICNF comparison, including verified spatial-output previews; no prediction or recommendation category.
7. `06_final_charts.ipynb` — verifies and displays the six presentation visuals from their real source artefacts without duplicate images.

Run each notebook from a fresh kernel. They read and check validated artefacts;
they do not rebuild the national panel, screening GeoPackage, QGIS projects, or
presentation figures.

Notebook `04` reports regression diagnostics for the already completed frozen
final temporal test. It distinguishes all-row MAE/RMSE, positive-target error,
and capture@20% as a ranking diagnostic. The binned comparison is descriptive
regression evidence, not probability calibration. It intentionally does not
claim direct feature importance from correlated spatial predictors.

## Controlled regeneration

To deliberately rebuild derived data, model artefacts, reports, and figures,
run this terminal command from the project root:

```text
python scripts/run_project.py --mode reproduce --confirm-rebuild
```

The notebook sequence is a review path, not the annual scoring engine. The
annual lifecycle is documented in
[docs/operational_forecast_cycle.md](../docs/operational_forecast_cycle.md).

## QGIS and final outputs

- QGIS projects and layer instructions: [`qgis/README.md`](../qgis/README.md)
- Historical screening layer: `data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg`
- Annual 2026 comparative layer: `data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg`
- Final figures: `reports/figures/`
- Final tables: `reports/tables/`
- Validation evidence: `reports/validation/`

The historical result represents **1 km mainland grid cells with fire
recurrence measured in a 2 km context**. It is historical evidence, not a
next-year prediction or purchase recommendation.

## Clean local rebuild

To return to a raw-input-only local state, first inspect:

```text
python scripts/clean_project_outputs.py --dry-run
```

Only after reviewing the list, run:

```text
python scripts/clean_project_outputs.py --confirm-delete-derived
```

This command preserves `data/raw/`, source code, notebooks, QGIS projects, and
tracked validation documents. It removes only reproducible derived data,
generated figures/tables, BI exports, and local run logs. Then run the full
reproduction command above.
