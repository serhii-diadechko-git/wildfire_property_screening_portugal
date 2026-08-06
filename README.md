# Reproducible Wildfire Exposure Screening — Mainland Portugal

This public capstone project combines data science and GIS to create a
transparent, broad-area wildfire-exposure screen for mainland Portugal.  It
uses one 1 km × 1 km cell as the analytical unit; fire recurrence is measured
in a mainland-masked 2 km outward context buffer.

The model estimates a **comparative next-year burned share**. It is not a
probability, property-level safety assessment, insurance estimate, forecast of
an individual fire, or buy/do-not-buy recommendation. GIS is used because the
inputs, the evidence, and the final inspection layers are spatial: it makes the
method visible and lets a reviewer examine patterns in QGIS.

## What the project contains

- A reproducible nine-feature continuous hurdle model, selected using
  historical data and then refit through the latest labelled outcome.
- A target-free annual comparative estimate for 2026 using 2025 predictors.
- A separate historical recurrence screening layer: **1 km mainland grid cells
  with fire recurrence measured in a 2 km context**.
- QGIS projects, figures, notebooks, source-validation code, and concise
  validation reports.

The nine model features are built-up share; forest/shrub share in the 2 km
context; mean slope in the 2 km context; number of previously burned years in
the prior ten years; JJAS mean temperature; JJAS total precipitation; JJAS mean
layer-1 soil water; JJAS maximum monthly temperature; and JJAS minimum monthly
soil water. Definitions and units are in [docs/data_dictionary.md](docs/data_dictionary.md).

## Data access and licensing

Raw source files, credentials, and generated data are deliberately excluded
from Git. Obtain every input from its official provider and place untouched
files in the paths described by [data/README.md](data/README.md) and
[data/source_manifest.json](data/source_manifest.json). The manifest records
the official URLs, access requirements, terms links, and local path patterns.

Do not publish a personal Google Drive copy of the raw data as a project mirror.
Some providers require accounts or acceptance of terms. Review each provider's
current terms before redistributing any source file; never commit a CDS token.

## Quick start (Windows, Linux, or macOS)

Use Python 3.13 and run commands from the cloned repository root.

```text
python -m venv .venv
```

Activate it with one of the following commands:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux/macOS
source .venv/bin/activate
```

Then install pinned dependencies and inspect the required local inputs:

```text
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/run_project.py --mode preflight
```

`preflight` does not download or alter data. It lists any missing official raw
files and writes a local, Git-ignored run summary under `reports/run_logs/`.

After preflight passes:

```text
# Run reproducibility tests only
python scripts/run_project.py --mode validate

# Deliberately regenerate derived outputs, reports, model artefacts and figures
python scripts/run_project.py --mode reproduce --confirm-rebuild
```

The full rebuild can take substantial time and memory. It never modifies
`data/raw/`. Add `--with-qgis` only in a Python environment that has PyQGIS;
otherwise open the tracked QGIS projects directly.

## Review path

Open notebooks in this order after the environment and raw inputs are ready:

1. `notebooks/00_environment_test.ipynb`
2. `notebooks/01_data_collection.ipynb`
3. `notebooks/02_data_preparation.ipynb`
4. `notebooks/03_eda.ipynb`
5. `notebooks/04_modelling.ipynb`
6. `notebooks/05_evaluation_recommendations.ipynb`
7. `notebooks/06_final_charts.ipynb`

Notebooks inspect and explain the reusable pipeline. Production calculations
live in `src/` and `scripts/`; see [notebooks/README.md](notebooks/README.md).
Launch the installed notebook interface with `python -m jupyter lab`.

For spatial inspection, open these portable projects in QGIS after cloning the
whole repository:

- `qgis/wildfire_exposure_screening_portugal.qgz` — observed historical
  recurrence screening and official ICNF comparison.
- `qgis/wildfire_exposure_screening_portugal_2026.qgz` — target-free 2026
  comparative estimate.

Their layers use relative paths where feasible. See [qgis/README.md](qgis/README.md).

## Main generated outputs

The reproducible run writes local outputs outside `data/raw/`:

| Output | Purpose |
|---|---|
| `data/processed/final_model_2010_2024/nine_feature_hurdle.joblib` | Versioned nine-feature model artefact. |
| `data/processed/operational_forecasts/forecast_2026_scores.parquet` | Canonical tabular 2026 comparative estimates. |
| `data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg` | QGIS-ready annual estimate. |
| `data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg` | Observed 2016–2025 recurrence evidence. |
| `reports/figures/` and `reports/tables/` | Presentation-ready visuals and summaries. |
| `reports/validation/` | Reproducible validation and interpretation reports. |

Parquet is the canonical analytical format. GeoPackages provide reusable
geometry and presentation/QA layers; they are not a duplicate cell-year panel.

## Annual update cycle

The model is not left static forever. For forecast year `Y`, derive unlabelled
predictors from `T=Y−1` and score the fixed model. When ICNF publishes the
observed outcome for `Y`, validate that score, add the newly labelled row, and
refit the unchanged nine-feature specification before scoring `Y+1`. This keeps
training data and forecast inputs temporally valid. The exact procedure is in
[docs/operational_forecast_cycle.md](docs/operational_forecast_cycle.md).

## Repository scope and release notes

Files intended for Git are source code, pinned dependencies, notebooks,
documentation, QGIS projects/styles, lightweight validation reports, and small
presentation assets. Large raw data, credentials, local run logs, and derived
data are ignored. Before publishing a fork or release, complete
[docs/release_checklist.md](docs/release_checklist.md), including the code
licence decision and a fresh review of each provider's redistribution terms.
