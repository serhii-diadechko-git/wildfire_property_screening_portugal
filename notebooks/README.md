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

1. `00_environment_test.ipynb` — environment, import, CRS, and output-path checks.
2. `01_data_collection.ipynb` — immutable source inventory, provenance, and representative archive checks; no download.
3. `02_data_preparation.ipynb` — canonical grid, CLC, and panel-contract evidence.
4. `03_eda.ipynb` — live summaries of validated panel completeness, zero inflation, temporal target behaviour, and correlations.
5. `04_modelling.ipynb` — nine-feature contract, held-out metrics, and annual scoring logic; no tuning or retraining.
6. `05_evaluation_recommendations.ipynb` — observed historical screening and official ICNF comparison; no prediction or recommendation category.
7. `06_final_charts.ipynb` — verifies the six presentation visuals, stable paths, and real source artefacts without duplicate images.

Run each notebook from a fresh kernel. They read and check validated artefacts;
they do not rebuild the national panel, screening GeoPackage, QGIS projects, or
presentation figures.

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
