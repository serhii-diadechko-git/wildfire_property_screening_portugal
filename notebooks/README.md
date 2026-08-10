# Notebook guide

The notebooks are reusable data-science walkthroughs. They load real project
artefacts, run compact validations, show tables/plots/maps, and explain the
choices behind the result. Reusable calculations live in `src/`; scripts and
notebooks call those same calculations; validation evidence lives in
`reports/validation/`.

Notebooks intentionally do not copy national geospatial or model logic into
cell bodies. Instead, they expose carefully named Boolean switches that call
the tested reusable functions. This gives a reviewer a step-by-step workflow
without hidden notebook state or a competing implementation.

## Setup

Create the pinned environment described in the root [README](../README.md),
then run the preflight check:

```text
python scripts/run_project.py --mode preflight
```

If the preflight report lists missing API-backed inputs, acquire them before
opening the notebooks:

```text
python scripts/run_project.py --mode acquire-api
python scripts/run_project.py --mode preflight
```

The acquisition mode uses only the local CDS credential file for ERA5-Land and
never prints or copies its token. It also retrieves the registered ICNF WCS
raster. Existing raw files remain immutable.

In VS Code, install the Microsoft **Python** and **Jupyter** extensions, open
the repository folder, choose **Python: Select Interpreter**, and select the
project environment: `.venv\Scripts\python.exe` on Windows or
`.venv/bin/python` on Linux/macOS. Open an `.ipynb` file, choose **Select
Kernel**, and select that same environment. The project requires a notebook
kernel (`ipykernel`), not the separate JupyterLab application.

## Execution order

1. `00_environment_test.ipynb` — portable environment, pinned-package, EPSG:3763, and in-memory ML/GIS smoke checks; writes no project output.
2. `01_data_collection.ipynb` — immutable source inventory, provenance ledger, and representative archive checks; no download.
3. `02_data_preparation.ipynb` — canonical grid, nine-predictor contract, CLC assignment, and panel-validation evidence.
4. `03_eda.ipynb` — validated panel completeness, zero inflation, target behaviour, predictor correlations, temporal drift, and extreme-value screening.
5. `04_modelling.ipynb` — technical final-model contract: saved nine-feature two-stage regression metadata, fixed feature order, occurrence/positive-share components, temporal safeguards, and annual scoring lifecycle; no tuning or retraining.
6. `05_evaluation_recommendations.ipynb` — historical GIS evidence audit: GeoPackage contract, independently recomputed summary checks, and QGIS hand-off; no prediction or recommendation category.
7. `06_final_charts.ipynb` — final capstone narrative: project design, nine-predictor contract, EDA, final-model validation-selection evidence, and validated GIS/presentation outputs; it reads real artefacts without duplicate analysis.

Run each notebook from a fresh kernel. They read and check validated artefacts;
they render real tables/plots from them. By default, costly/rewrite-capable
stages are disabled. Turn on a switch only when deliberately regenerating the
corresponding derived output after raw-input preflight has passed.

### Git and run-record boundary

Ordinary notebook review should not create a Git change. Tracked
`reports/validation/` files contain stable analytical evidence; per-run UTC
times, elapsed durations, commands, and terminal output are written only to
Git-ignored `reports/run_logs/`. A deliberate rebuild may change a tracked
validation report only when the underlying analytical evidence changes.

Notebook `04` explains the governed model and its annual update mechanism.
Notebook `06` is the single presentation of final-model validation-selection
metrics and diagnostics, including all-row and positive-target error and
Capture@20% as a technical ranking diagnostic. This avoids presenting the
same model-version evidence twice. Neither notebook claims direct feature importance from correlated
spatial predictors.

## Temporal scope

The notebook story distinguishes completed evidence from the current unlabelled
annual estimate: final-model fitting uses `T=2010–2019`, selection uses
`T=2020–2021`, and the one held-out final test uses `T=2022–2024` with observed
outcomes through 2025. The 2026 layer instead uses `T=2025` inputs and has no
observed target yet. The root [README](../README.md#temporal-coverage-and-current-estimate)
and the [annual operational cycle](../docs/operational_forecast_cycle.md)
contain the full year-by-year table and annual update rules.

## Controlled rebuild switches

| Notebook | Default behavior | Explicit opt-in behavior |
|---|---|---|
| `00` | Runs environment and raw-input preflight. | No rebuild switch. |
| `01` | Reads provenance and runs representative archive validation. | No download or raw-data write. |
| `02` | Inspects grid, CLC, feature contract, and panel validation. | `REBUILD_NATIONAL_PANEL` / `REBUILD_EXTENDED_TRAINING_PANEL` call the bounded reusable builders. |
| `03` | Reads saved EDA evidence and plots it. | `REGENERATE_EDA` regenerates EDA reports/figures. |
| `04` | Verifies saved model metadata, feature order, split boundary, two-part regression components, and operational lifecycle. | No notebook rebuild switch; use the project runner for a deliberate refit/reproduction. |
| `05` | Audits the published historical GeoPackage and recorded metrics. | `VALIDATE_HISTORICAL_SCREENING` recomputes and compares bounded screening attributes. |
| `06` | Reads and presents validated EDA, final-model selection diagnostics, GIS, and final-screening artefacts. | No output-writing rebuild switch; it renders live review figures from validated artefacts. |

For a complete automated rebuild, use the root command rather than enabling
several switches manually:

```text
python scripts/run_project.py --mode reproduce --confirm-rebuild
```

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
generated figures/tables, and local run logs. Then run the full
reproduction command above.
