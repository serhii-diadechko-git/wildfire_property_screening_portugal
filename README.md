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

- A reproducible nine-feature two-part burned-share regression model (the
  technical term is hurdle model), selected using
  historical data and then refit through the latest labelled outcome.
- A target-free annual comparative estimate for 2026 using 2025 predictors.
- A separate historical recurrence screening layer: **1 km mainland grid cells
  with fire recurrence measured in a 2 km context**.
- A separate official ICNF structural-hazard comparison layer. It comes from
  the official 25 m SRUP-CPIR 2020-2030 source, is summarized to the
  predominant valid class in each 1 km cell, and is not an ICNF prediction or
  this project's model output.
- QGIS projects, figures, notebooks, source-validation code, and concise
  validation reports.

The nine model features are built-up share; forest/shrub share in the 2 km
context; mean slope in the 2 km context; number of previously burned years in
the prior ten years; JJAS mean temperature; JJAS total precipitation; JJAS mean
layer-1 soil water; JJAS maximum monthly temperature; and JJAS minimum monthly
soil water. Definitions and units are in [docs/data_dictionary.md](docs/data_dictionary.md).

The two-part regression model combines a histogram-gradient-boosting classifier for whether
any burning occurs with a histogram-gradient-boosting regressor for burned
share when burning occurs. Small decision-tree ensembles can represent
non-linear relationships and interactions among history, landscape, terrain,
and climate without imposing one fixed linear effect. The two components suit a
target with many zero values and continuous positive burned shares. This is an
associative predictive method, not causal evidence.

## Research hypothesis and conclusion

The project tests whether recent wildfire recurrence, landscape context,
terrain, and predictor-year climate conditions can estimate the comparative
next-year burned share of mainland Portugal 1 km cells better than a
transparent historical-recurrence baseline. The outcome is continuous
`burned_share_next_year`; it is not a property-level probability or a safety
classification.

The hypothesis received partial support on the frozen temporal evaluation.
The nine-feature two-part regression model achieved lower all-row MAE and
stronger burned-share-mass capture than the historical-recurrence baseline,
but did not improve every diagnostic: RMSE was effectively unchanged and
positive-target error was slightly worse. It also underpredicted the unusually
high-burn outcome associated with predictor year 2024 (outcome year 2025).

The defensible conclusion is therefore comparative and limited: the model can
help narrow broad-area location research, but it is not sufficiently stable or
calibrated to support a safety guarantee, an individual-property forecast, or
a buy/do-not-buy recommendation.

## Data access and licensing

Raw source files, credentials, and generated data are deliberately excluded
from Git. Obtain every input from its official provider and place untouched
files in the paths described by [data/README.md](data/README.md) and
[data/source_manifest.json](data/source_manifest.json). The manifest records
the official URLs, access requirements, terms links, and local path patterns.

The project-owned code, notebooks, documentation, and original figures are
released under the [MIT License](LICENSE). This permissive licence allows reuse,
modification, and redistribution with the copyright and licence notice. It
does not override the separate licences or access terms of the external data.

The source-specific rules are:

| Source | Access category | Licence / terms identified from official source |
|---|---|---|
| [ICNF burned areas and structural-hazard catalogue](https://geocatalogo.icnf.pt/) | Free/open by default; a layer-specific exception may apply | ICNF open-data conditions; ICNF retains intellectual property and requires `ICNF, [layer name], [download URL], [download date]`. No GPL/Creative Commons identifier is stated on the catalogue page. |
| [DGT CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop) | Open public access; redistribution status not established | DGT/SNIG identifies CAOP as an open/high-value public dataset, but the CAOP page does not state a project-specific permissive licence. Verify current DGT/SNIG metadata before redistribution. |
| [Copernicus CLC](https://land.copernicus.eu/en/products/corine-land-cover) | Free, full and open | Copernicus Land Monitoring data policy (not GPL): source attribution, adaptation disclosure, and no implication of EU endorsement. Commercial use is allowed under the CLC terms. |
| [Copernicus DEM GLO-30](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) | Free licence for GLO-30/GLO-90 | Copernicus DEM/ESA user-licence conditions; prescribed WorldDEM/Copernicus attribution is required when communicated or adapted. DOI: [10.5270/ESA-c5d3d65](https://doi.org/10.5270/ESA-c5d3d65). No GPL licence applies. |
| [ERA5-Land monthly means](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means) | Free with account and terms acceptance | The CDS dataset page identifies a [CC-BY licence](https://cds.climate.copernicus.eu/terms) and DOI [10.24381/cds.68d2bb30](https://doi.org/10.24381/cds.68d2bb30). Each user must accept CDS terms and retrieve files with their own account. |

These are data-access conditions, not software licences: GPL is not applicable
to these datasets unless a provider explicitly says so. The statements describe
access and attribution, not ownership transfer. A
provider may update a licence, access category, or required notice after this
repository is released, so review the linked official terms on every new
acquisition or redistribution. The project does not redistribute provider
downloads, does not publish a personal Google Drive mirror, and never commits a
CDS token.

For the complete source-by-source attribution, redistribution, and maintainer
checklist, see [docs/data_licensing_and_attribution.md](docs/data_licensing_and_attribution.md).

## Quick start (Windows, Linux, or macOS)

Use Python 3.13 and run commands from the cloned repository root. The project
uses relative paths, so it does not depend on a particular operating-system
folder or editor.

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

Then install pinned dependencies:

```text
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 1. Acquire raw inputs

Read `data/source_manifest.json`. Obtain the non-API files from their official
providers and copy each untouched file to its documented `data/raw/` path. For
ERA5-Land, accept the CDS terms and create the local credentials file in the
normal home-directory location (`%USERPROFILE%\\.cdsapirc` on Windows or
`~/.cdsapirc` on Linux/macOS). Never put credentials in the repository.

For CLC, download the three original Europe-wide ZIP packages into
`data/raw/clc/`. The 120–150 MB Portugal-clipped GeoPackages under
`data/processed/clc/` are generated automatically during reproduction; do not
copy manually clipped files from another machine.

The project can retrieve the approved API-backed ERA5-Land and ICNF
structural-hazard inputs for you:

```text
python scripts/run_project.py --mode acquire-api
```

This command validates existing immutable files and downloads only missing
API-backed files. It never overwrites raw data. If you prefer manual
acquisition, place the files first and skip this command.

#### If one ERA5-Land year fails

CDS jobs are submitted one year at a time. A temporary CDS failure can occur
after earlier years have already completed. Rerun the same command safely:

```text
python scripts/run_project.py --mode acquire-api
```

Existing files are preserved and validated; only missing years are retried. To
retry one standard annual GRIB directly, use its year:

```text
python scripts/download_era5_land_year.py 2013 --download
```

To retry one corrected precipitation-only request, add the explicit workaround
switch:

```text
python scripts/download_era5_land_year.py 2023 --corrected-precipitation --download
```

After a successful retry, run `python scripts/run_project.py --mode preflight`
again. Never delete or overwrite earlier successful raw downloads.

### 2. Check raw-data readiness

Run preflight after manual/API acquisition:

```text
python scripts/run_project.py --mode preflight
```

`preflight` does not download or alter data. It lists any missing official raw
files and writes a local, Git-ignored run summary under `reports/run_logs/`.
The launcher automatically switches to the repository `.venv` when it exists,
so the commands remain correct if VS Code or a terminal accidentally starts
them with a global Python installation.

### 3. Validate the environment and source contracts

After preflight reports `ready`:

```text
# Run reproducibility tests only
python scripts/run_project.py --mode validate
```

Before derived outputs exist, this runs the portable bootstrap/source tests and
does not require a generated model or forecast. After a successful reproduction
run has created the derived output inventory, the same command automatically
runs the full repository test suite.

### 4. Build the data, fit the model, and generate outputs

After validation passes, run the deliberate full workflow:

```text

# Deliberately regenerate derived outputs, reports, model artefacts and figures
python scripts/run_project.py --mode reproduce --confirm-rebuild
```

Within this workflow, the model-training step is the `model refit` stage. It
fits the retained nine-feature model on the labelled development data and
writes the versioned model artefact. The later stages score the operational
2026 estimate and build reports/figures; they do not silently retrain it.

If you need to run the core stages separately instead of using `reproduce`,
keep this order:

```text
python scripts/prepare_reference_layers.py            # CAOP references + canonical grid
python scripts/prepare_clc_portugal_layers.py         # Portugal CLC derivatives
python scripts/build_national_panel.py --stage all
python scripts/build_extended_training_panel.py --stage all
python scripts/refit_extended_training_models.py       # actual model fit
python scripts/run_extended_final_temporal_test.py
python scripts/prepare_operational_forecast.py
python scripts/score_operational_forecast.py
python scripts/build_final_visuals.py
```

The separate commands assume that acquisition, preflight, and source
validation have already passed. The first command creates/reuses the CAOP
boundary and canonical 1 km grid; the second creates/reuses the three CLC
derivatives. The national-panel command also checks these prerequisites, so it
is safe to call directly after a clean checkout. The next command builds
labelled data; the refit command fits and saves the model; the remaining
commands evaluate or apply that saved model and create presentation outputs.

The acquisition mode checks whether an ERA5 file is missing before requiring
the local CDS credentials file. If all requested ERA5 files already exist, it
validates/reuses them without requiring `.cdsapirc`. When a download is needed,
the credentials file is used without printing or copying its contents. The
mode also calls the registered ICNF WCS download. Run
`--mode preflight` again after acquisition; do not use `acquire-api` as an
implicit preflight.

The full rebuild can take substantial time and memory. It never modifies
`data/raw/`. Add `--with-qgis` only in a Python environment that has PyQGIS;
otherwise open the tracked QGIS projects directly.

## Important: first-run data preparation can be slow

> [!IMPORTANT]
> **The initial reproduction may take substantial time and temporary disk space.**
> It processes large geospatial datasets, including multi-gigabyte Copernicus
> CLC archives, ICNF burned-area layers, DEM tiles, and ERA5-Land grids. CLC
> preparation extracts each archive temporarily, clips it to mainland Portugal,
> and creates these three local GeoPackages of approximately 120–150 MB each:
>
> - `data/processed/clc/u2012_clc2006_v2020_20u1_pt.gpkg` from
>   `data/raw/clc/u2012_clc2006_v2020_20u1_geoPackage.zip`;
> - `data/processed/clc/u2018_clc2012_v2020_20u1_pt.gpkg` from
>   `data/raw/clc/u2018_clc2012_v2020_20u1_geoPackage.zip`;
> - `data/processed/clc/u2018_clc2018_v2020_20u1_pt.gpkg` from
>   `data/raw/clc/u2018_clc2018_v2020_20u1_geoPackage.zip`.
>
> This
> is expected GIS processing, not a stuck command.

If another project user can provide the already validated files, the setup can
be faster: copy untouched raw sources into the exact `data/raw/` paths listed
in `data/source_manifest.json`, and copy validated CLC derivatives into
`data/processed/clc/` using their exact registered filenames. Then run
`python scripts/run_project.py --mode preflight` and the relevant validation
tests. Raw files must remain unchanged, and copied processed artifacts must be
validated against the project contract before they are reused. Do not copy
credentials or use unverified files from an unknown source.

### Start from a clean derived-output state

Use this only when you deliberately want to remove locally generated artefacts
and reproduce them again from the untouched raw inputs:

```text
# List exactly what would be removed; deletes nothing.
python scripts/clean_project_outputs.py --dry-run

# Remove only derived data, generated figures/tables, and local run logs.
python scripts/clean_project_outputs.py --confirm-delete-derived

# Then rebuild the project.
python scripts/run_project.py --mode reproduce --confirm-rebuild
```

The cleanup command never removes `data/raw/`, credentials, source code,
notebooks, QGIS projects, or tracked validation documentation. It is
intentionally dry-run first and requires an explicit confirmation flag.

## Review path

Open notebooks in this order after the environment and raw inputs are ready:

1. `notebooks/00_environment_test.ipynb`
2. `notebooks/01_data_collection.ipynb`
3. `notebooks/02_data_preparation.ipynb`
4. `notebooks/03_eda.ipynb`
5. `notebooks/04_modelling.ipynb`
6. `notebooks/05_evaluation_recommendations.ipynb`
7. `notebooks/06_final_charts.ipynb`

Notebooks are reusable, controlled data-science walkthroughs: they run real
source checks, display artifacts/plots/tables, and can call the same reusable
functions as the scripts when an explicit rebuild switch is enabled. Production
calculations remain in `src/`; notebooks do not duplicate their implementation.
See [notebooks/README.md](notebooks/README.md). They can be opened in VS Code,
Jupyter Notebook, PyCharm, or another Jupyter-compatible tool. In VS Code,
install the Microsoft **Python** and **Jupyter** extensions, open the repository
folder, select the project's `.venv` interpreter, then select that same
environment as the notebook kernel. JupyterLab is not required.

### What the notebooks are for

Run the notebooks from a fresh kernel, in numeric order, after `preflight`
and—when reviewing derived/model outputs—after a successful reproduction run.
They are a transparent learning, review, and controlled-orchestration path:

- `00` checks the portable Python, GIS, and machine-learning environment using synthetic in-memory examples.
- `01` and `02` inspect immutable-source provenance, the grid, CLC governance, and the analytical contract.
- `03` shows validated data-quality, target-distribution, temporal-drift, and correlation evidence.
- `04` is the technical model-contract notebook: saved model metadata, feature order, two-part regression components, temporal safeguards, and the annual scoring lifecycle. It does not repeat held-out results or refit a model.
- `05` audits the validated historical GIS layer and hands it off to QGIS. `06` is the final capstone narrative and the single presentation of EDA, final-test regression diagnostics, and validated GIS/presentation visuals.

Use `scripts/run_project.py` for the one-command rebuild. Use notebooks when
you want to step through the same workflow, inspect intermediate evidence, and
see the calculations visually. Expensive/rewrite-capable notebook stages are
disabled by default with clearly named Boolean switches; no notebook performs a
hidden rebuild.

### Model diagnostic outputs

The frozen T=2022–2024 final temporal evaluation produces durable regression
diagnostics in addition to the interactive notebook views:

- `reports/figures/model_final_test_metric_comparison.png`
- `reports/figures/model_final_test_observed_vs_estimated.png`
- `reports/figures/model_final_test_binned_observed_vs_estimated.png`
- `reports/tables/model_final_test_metrics.csv`
- `reports/tables/model_final_test_metrics_by_year.csv`
- `reports/tables/model_final_test_binned_observed_vs_estimated.csv`

They are built by `python scripts/build_model_diagnostics.py` from saved
predictions/metrics only; that command does not fit a model or change a score.

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
| `reports/presentation/wildfire_exposure_screening_capstone_final.pptx` | Editable final capstone presentation built from the validated results. |

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
