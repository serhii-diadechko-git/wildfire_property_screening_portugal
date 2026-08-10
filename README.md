# Reproducible Wildfire Exposure Screening — Mainland Portugal

This public data-science, machine-learning, and GIS capstone compares wildfire-exposure patterns across mainland Portugal. It supports the **broad-area location-research** stage: use consistent national evidence to narrow a large search area, then continue with local and property-specific investigation.

The project does **not** identify a safe area, certify a property, estimate insurance, predict an individual fire, or make a buy/do-not-buy recommendation.

## Project design

| Element | Definition |
|---|---|
| Analytical record | One mainland Portugal 1 km × 1 km cell in EPSG:3763 for one predictor year. |
| Spatial context | A mainland-masked 2 km outward buffer provides local context; it is not a second grid. |
| Model target | `burned_share_next_year`: the proportion of a cell's land area burned in the following year. |
| Current annual estimate | A target-free 2026 comparative estimated burned-share layer derived from 2025 predictor inputs. |
| Supporting GIS evidence | Observed 2016–2025 fire recurrence and an official ICNF structural-hazard reference layer. |

## Capstone purpose, scientific question, and conclusion

### Capstone purpose

How can a reproducible data-science, machine-learning, and GIS workflow help a prospective buyer **narrow broad mainland Portugal location-search areas** for further local research on wildfire exposure?

The capstone answer is a set of comparable 1 km evidence layers: a target-free annual comparative estimate, observed historical recurrence, and an official ICNF structural-hazard reference. They support an earlier, broad-area research step; they do not determine whether to buy a property.

### Scientific modelling question

Can recent wildfire recurrence, landscape context, terrain, and predictor-year climate estimate the comparative next-year burned share of mainland Portugal 1 km cells better than a transparent historical-recurrence baseline?

### Final temporal evaluation

The **final nine-feature model** was frozen after development validation on `T=2020–2021` and evaluated once on the untouched final period `T=2022–2024` (observed outcomes 2023–2025).

| Final temporal metric | Historical-recurrence baseline | Final nine-feature model |
|---|---:|---:|
| All-row MAE | 0.02919 | **0.02091** |
| RMSE | **0.11059** | 0.11100 |
| Burned-share mass Capture@20% | 40.17% | **57.16%** |

The final model improved average error and the comparative ranking of observed burned share, but larger/extreme outcomes remained difficult. Scientifically, this is partial support for a comparative predictive relationship—not causal proof and not a precise local forecast. For the capstone, the result is useful because it adds a transparent, reproducible annual layer to the broader location-screening workflow. Read the [model-selection record](docs/model_v2_validation_selection.md) and [final temporal evaluation report](reports/validation/final_temporal_test_2022_2024.md).

### Temporal coverage and current estimate

The registered ICNF annual burned-area records cover calendar years **2000–2025**. They are not all outcome labels: the earlier years supply the ten-year historical-fire context required for the first labelled predictor year.

| Stage | Predictor years `T` | Observed outcome years `T+1` | Purpose |
|---|---:|---:|---|
| Development fitting | 2010–2019 | 2011–2020 | Fit the predeclared candidate methods. |
| Development validation | 2020–2021 | 2021–2022 | Select the final nine-feature model. |
| Held-out final test | 2022–2024 | 2023–2025 | Evaluate the frozen final nine-feature model once. |
| Operational refit | 2010–2024 | 2011–2025 | Refit the unchanged selected specification using all completed labelled rows. |
| Current annual estimate | 2025 | 2026: not yet observed | Produce the target-free 2026 comparative estimate. |

For example, the 2026 layer uses predictor-year `T=2025` inputs and historical fire years 2015–2024 only. It can be independently evaluated only after ICNF publishes the observed 2026 burned-area outcome. See the detailed [annual operational cycle](docs/operational_forecast_cycle.md).

## How the method works

### Data sources and feature roles

| Source | Role in the analysis |
|---|---|
| [ICNF burned areas and structural-hazard catalogue](https://geocatalogo.icnf.pt/) | Historical-fire context from `T−10` through `T−1`; observed outcome in `T+1`. Never a same-year predictor. The structural-hazard layer is an external reference, not this model's output. |
| [Copernicus CLC](https://land.copernicus.eu/en/products/corine-land-cover) | Broad built-up and forest/shrub landscape context. It is not annual parcel-level land cover. |
| [Copernicus DEM GLO-30](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) | Static terrain context used for mean slope. |
| [ERA5-Land monthly means](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means) | June–September (`JJAS`) temperature, precipitation, and shallow soil-water context from predictor year `T` only. It is coarse regional context, not 1 km weather. |
| [DGT CAOP](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop) | Mainland boundary, canonical grid, and reporting geography. |

The nine predictors are defined, including their units, ranges, and source-year rules, in [docs/data_dictionary.md](docs/data_dictionary.md).

### Why the final model

The final model is a **nine-feature two-stage histogram-gradient-boosting regression**:

1. a [`HistGradientBoostingClassifier`](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html) estimates whether any burning is expected; and
2. a [`HistGradientBoostingRegressor`](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html) estimates burned share when burning is expected.

Their product is one continuous next-year estimated burned share. This approach suits a large numeric tabular panel with nonlinear relationships and many zero outcomes alongside positive burned shares. It is an associative predictive method, not causal evidence, and it was retained because of the time-aware comparison above—not because it is claimed to be universally best.

For technical detail, parameter choices, safeguards, and limitations, see [docs/model_v2_validation_selection.md](docs/model_v2_validation_selection.md) and [docs/project_brief.md](docs/project_brief.md).

## Use the outputs responsibly

Use the QGIS layers in this order:

1. Compare broad areas with the 2026 estimated comparative exposure layer.
2. Read the separate 2016–2025 observed recurrence and official ICNF structural-hazard layers alongside it.
3. Shortlist broad areas for further research; do not combine the three layers into a single score.
4. Verify planning, access, insurance, terrain, vegetation management, and property-specific conditions locally before making any decision.

The official ICNF structural-hazard layer is a separate official 25 m landscape classification summarized to the predominant class per 1 km cell. It is neither this project's prediction nor an observed burned-area map for one year. See [qgis/README.md](qgis/README.md).

## Local web map and exposure lookup API

After the documented reproduction workflow has published the 2026 spatial
outputs, the project provides two local presentation interfaces over the same
validated results: a simple browser map for broad-area exploration and a
read-only REST API for coordinate lookup. Neither interface retrains the model
or exposes the separately governed ICNF structural-hazard comparison layer.

```text
python scripts/build_web_map_assets.py --overwrite
python scripts/run_exposure_api.py
```

Open `http://127.0.0.1:8000` for the interactive map. It displays the 2026
estimate as three comparative percentile bands and lets a user click a 1 km
cell for its estimate and descriptive 1/3/5 km context summaries. The
The OpenStreetMap Standard/Humanitarian, terrain, and satellite background
selector needs an internet connection; the exposure layer and API remain local.
Use it to narrow broad research areas, not to assess a specific property or
make a purchase decision.

Open `http://127.0.0.1:8000/docs` for the interactive API documentation. The
API accepts coordinates, not addresses, by design: address geocoding would
require a separately governed provider and privacy terms. See the complete
[local web-map guide](web/README.md) and [local exposure API guide](docs/exposure_api_guide.md).

## Quick start

Use Python 3.13 and run commands from the cloned repository root. The project uses relative paths and works from Windows, Linux, or macOS.

### 1. Create the environment

```text
python -m venv .venv
```

Activate it:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux/macOS
source .venv/bin/activate
```

Install the pinned dependencies:

```text
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Obtain the data

Raw provider files, credentials, and derived outputs are intentionally excluded from Git. Follow [data/README.md](data/README.md) and [data/source_manifest.json](data/source_manifest.json): obtain every original file from its official provider and place it untouched at the documented `data/raw/` path.

ERA5-Land requires a CDS account, accepted terms, and a local credential file (`%USERPROFILE%\.cdsapirc` on Windows or `~/.cdsapirc` on Linux/macOS). Never put credentials in this repository.

To retrieve only missing API-backed ERA5-Land and ICNF structural-hazard inputs:

```text
python scripts/run_project.py --mode acquire-api
```

This command validates/reuses existing raw files, downloads only missing API-backed inputs, and never overwrites raw data. If one ERA5-Land request fails temporarily, rerun the same command; completed years are preserved. Detailed acquisition and retry guidance is in [data/README.md](data/README.md).

### 3. Check readiness and validate

```text
python scripts/run_project.py --mode preflight
python scripts/run_project.py --mode validate
```

`preflight` reports missing raw inputs without modifying them. `validate` runs the essential environment, source-contract, temporal, notebook-structure, and portability checks; it does not rebuild the panel, refit the model, or require optional QGIS layout exports.

### 4. Deliberately reproduce the workflow

After preflight reports ready:

```text
python scripts/run_project.py --mode reproduce --confirm-rebuild
```

This builds/reuses reference layers and CLC derivatives, derives the panel, refits the fixed nine-feature model on completed labelled data, creates the 2026 comparative estimate, and writes reproducible local outputs. It never modifies `data/raw/`.


The three Portugal-clipped CLC derivatives are created under
`data/processed/clc/`. They are approximately 120-150 MB each and are reused
on later runs. Exact validated derivatives may be copied into these registered
paths; see [data/README.md](data/README.md) before reuse.

### Troubleshooting and first-run processing

> [!IMPORTANT]
> **The first full reproduction can take substantial time and temporary disk space.**
> Processing the large CLC, ICNF, DEM, and ERA5-Land spatial inputs may appear
> quiet for several minutes. This is expected unless the command reports an
> error.

For CLC raw-to-processed file mapping, safe rerun instructions, CDS retry
guidance, interrupted-build recovery, and QGIS checks, see
[docs/troubleshooting.md](docs/troubleshooting.md).


### 5. Review the results

Open notebooks from fresh kernels in this order:

1. `notebooks/00_environment_test.ipynb`
2. `notebooks/01_data_collection.ipynb`
3. `notebooks/02_data_preparation.ipynb`
4. `notebooks/03_eda.ipynb`
5. `notebooks/04_modelling.ipynb`
6. `notebooks/05_evaluation_recommendations.ipynb`
7. `notebooks/06_final_charts.ipynb`

Notebooks are review and learning walkthroughs. They display real artifacts, tables, and plots, and are read-only by default. Production calculations live in `src/`; notebooks do not contain a second competing implementation. See [notebooks/README.md](notebooks/README.md) for notebook roles, rebuild switches, and VS Code setup.

Open the QGIS projects after a successful reproduction:

- `qgis/wildfire_exposure_screening_portugal.qgz` — observed historical recurrence and official ICNF comparison.
- `qgis/wildfire_exposure_screening_portugal_2026.qgz` — target-free 2026 comparative estimate.

For an optional QGIS layout rebuild/validation on Windows with QGIS installed:

```text
scripts\run_qgis_presentation_project.bat --validate-existing
scripts\run_qgis_presentation_project.bat --validate-operational
```

## Main local outputs

| Output | Purpose |
|---|---|
| `data/processed/final_model_2010_2024/nine_feature_hurdle.joblib` | Saved final nine-feature model used for the current annual estimate. `nine_feature_hurdle` is a legacy internal artifact filename, not the public model name. |
| `data/processed/final_model_2010_2024/model_metadata.json` | Model feature order, training cutoff, version, and reproducibility metadata. |
| `data/processed/operational_forecasts/forecast_2026_scores.parquet` | Canonical tabular 2026 comparative estimates. |
| `data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg` | QGIS-ready annual comparative layer. |
| `data/processed/web_map/estimated_comparative_wildfire_exposure_2026.geojson` | Derived, browser-ready 2026 map layer; generated locally and not the analytical source of truth. |
| `data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg` | Observed 2016–2025 recurrence evidence plus official ICNF comparison attributes. |
| `reports/figures/` and `reports/tables/` | Reproducible visual and tabular presentation outputs. |
| `reports/validation/` | Stable analytical validation evidence. |
| `reports/presentation/wildfire_exposure_screening_capstone_final.pptx` | Editable eight-slide capstone presentation. |
| `reports/run_logs/` | Local, Git-ignored command logs and timings. |

Parquet is the canonical analytical table format. GeoPackages provide reusable geometry and QGIS/presentation layers; they are not duplicate full cell-year panels.

## Annual update cycle

For forecast year `Y`, use completed predictor-year inputs from `T=Y−1` to publish a target-free comparative estimate. When ICNF later publishes the observed outcome for `Y`, evaluate that already-published estimate, add the new labelled year, refit the unchanged nine-feature specification, and score `Y+1`.

The current 2026 estimate uses 2025 inputs and can be independently evaluated only after ICNF publishes 2026 burned-area data. The detailed controlled process is in [docs/operational_forecast_cycle.md](docs/operational_forecast_cycle.md).

## Data access and licensing

This is a code-and-methods repository, not a data mirror. The project code,
notebooks, documentation, and original figures are released under the
[MIT License](LICENSE). Every external dataset keeps its provider's own access,
licence, attribution, and redistribution conditions.

This repository documents an educational data-science capstone. It is not
offered by the author as a commercial wildfire-risk, insurance, valuation, or
property-decision service. Its outputs support broad-area location research;
they must not be presented as a safety guarantee, a property-level assessment,
or a buy/do-not-buy recommendation. The MIT License applies only to this
repository's original code and authored materials; it does not grant rights to
sell, redistribute, or relicense provider data or restricted derivatives.

In particular, the separate official ICNF structural-hazard comparison layer
is not the project's ML output. Its official layer metadata restricts
commercialisation and may require express DGT authorisation for other uses.
Do not include that layer or its derived classes in a commercial product unless
the required written permission has been obtained.

Obtain provider files from their official sources using your own account where
required; do not commit credentials or assume that a public dataset may be
redistributed without checking its terms. The full source-by-source licence,
attribution, and redistribution guidance is in
[docs/data_licensing_and_attribution.md](docs/data_licensing_and_attribution.md).

## Documentation map

| Need | Read |
|---|---|
| Feature definitions, units, and temporal rules | [docs/data_dictionary.md](docs/data_dictionary.md) |
| Research scope, methods, and limits | [docs/project_brief.md](docs/project_brief.md) |
| Sources, paths, access, and acquisition | [data/README.md](data/README.md) and [data/source_manifest.json](data/source_manifest.json) |
| Model-selection design and parameters | [docs/model_v2_validation_selection.md](docs/model_v2_validation_selection.md) |
| Annual scoring/refitting process | [docs/operational_forecast_cycle.md](docs/operational_forecast_cycle.md) |
| Notebook roles and VS Code use | [notebooks/README.md](notebooks/README.md) |
| QGIS layers, projects, and limitations | [qgis/README.md](qgis/README.md) |
| Local interactive web map | [web/README.md](web/README.md) |
| Data licences and attribution | [docs/data_licensing_and_attribution.md](docs/data_licensing_and_attribution.md) |

## Clean local rebuild

To remove only local derived outputs, figures/tables, and run logs while preserving raw data, source code, notebooks, QGIS projects, and tracked validation evidence:

```text
python scripts/clean_project_outputs.py --dry-run
python scripts/clean_project_outputs.py --confirm-delete-derived
```

Then run the deliberate reproduction command again. For a release or maintenance review, see [docs/release_checklist.md](docs/release_checklist.md).
