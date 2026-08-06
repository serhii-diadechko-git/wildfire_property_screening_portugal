# Reproducible Wildfire Exposure Screening for Residential Location Selection in Mainland Portugal

## Project overview

This capstone project helps a prospective homebuyer compare residential areas in mainland Portugal from a **wildfire-exposure perspective**.

The project combines public geospatial data on historical burned areas, land cover, terrain, and climate. It uses historical records to train and test a reproducible annual, next-calendar-year comparative exposure model, and preserves a separate historical screening layer for context.

> The project supports **area shortlisting only**. It does not determine whether a specific house is safe or whether it is the best property to buy.

## Business problem

Buying a home is a long-term and expensive decision. Wildfire exposure varies significantly across mainland Portugal, but relevant information is distributed across historical fire maps, land-cover datasets, climate data, and official hazard products.

A property buyer needs a clear and consistent way to compare locations before spending time and money on individual properties.

## Decision supported

**Decision-maker:** a prospective homebuyer choosing a location in mainland Portugal.

**Decision support:** which broad areas warrant further local investigation when comparing residential locations. When the annual source-input gate is complete, the model provides a relative estimate for the stated next calendar year; the historical layer provides supporting evidence. The screening distinguishes:

- lower, moderate, or higher historical recurrence context;
- agreement or disagreement with the official ICNF structural-hazard class;
- insufficient official comparison evidence where the hazard layer has no valid class.

## Project goal

Build a reproducible geospatial data-science workflow that:

1. summarizes ten years of observed ICNF burned-area recurrence around every mainland 1 km cell;
2. creates transparent recurrence-only historical exposure bands;
3. compares those bands descriptively with the official ICNF structural-hazard map;
4. produces a QGIS-ready screening layer and machine-readable summaries;
5. records limitations and unmatched official evidence explicitly;
6. supports a reproducible update when a later complete burned-area year becomes available.

## Completed outputs

- a national historical wildfire-exposure screening GeoPackage;
- a portable QGIS presentation project with two print layouts;
- recurrence-band and official ICNF hazard comparison tables;
- six validated presentation maps, charts, and summary visuals;
- a reproducible data-preparation and screening pipeline;
- a frozen final-temporal evaluation of the historical baseline and nine-feature hurdle model;
- a reusable fixed-specification nine-feature continuous burned-share model trained on T=2010-2024, with outcomes through 2025;
- an explicit annual rebuild/scoring contract and source preflight;
- a documented limitations and update procedure.

## Analytical and spatial output layers

- `data/processed/national_panel_2015_2024.parquet` is the canonical machine-learning table: one `cell_id` x `observation_year` row, with no repeated geometry.
- `data/processed/pilot_2023_to_2024/pilot_2023_to_2024_icnf_caop.gpkg` remains the reusable EPSG:3763 canonical grid-geometry lookup.
- `data/processed/spatial_qa/era5_land_coastal_fallback_qa.gpkg`, layer `era5_coastal_fallback_qa`, is a 1,506-feature QA/presentation layer documenting the systematic ERA5-Land coastal fallback.
- `data/processed/spatial_qa/national_panel_snapshot_2024.gpkg`, layer `national_panel_snapshot_2024`, is an 89,112-feature GIS/EDA snapshot containing the seven predictors, observed 2025 target and climate-assignment method for `T=2024`. It is not the canonical ML table.
- `data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg`, layer `historical_exposure_screening`, is the final 89,112-feature historical/descriptive screening layer. It represents **1 km mainland grid cells with fire recurrence measured in a 2 km context**, using 2016-2025 evidence, CLC 2018 landscape context, static slope, and a predominant-class comparison with the official 25 m ICNF structural-hazard raster.

The 2026 model-based GeoPackage now exists at `data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg`, layer `estimated_comparative_exposure_2026`. It contains one EPSG:3763 geometry per canonical cell, the continuous comparative estimate, percentile, model checksum, input year, and score status. It is not a probability, safety score, forecast guarantee, or buy/do-not-buy recommendation.

## Spatial design

- **1 km x 1 km grid cell:** the sole analytical unit.
- **2 km surrounding buffer:** the outward context used for vegetation, slope, and previous-fire features.

The 2 km value is not a second analytical resolution. The final descriptive screening represents **1 km mainland grid cells with fire recurrence measured in a 2 km context**.

## Temporal methodology and data scope

> Final model-evaluation design: fit T=2010-2019; validate T=2020-2021; one frozen final temporal test T=2022-2024 (outcomes 2023-2025). The 1 km EPSG:3763 cell is the only analytical unit; 2 km is an outward context buffer. The 2023->2024 artifact is a feasibility pilot, not the final test.

Each analytical record is one 1 km x 1 km grid cell for predictor reference year `T`. Predictor information available at `T` is used to estimate the observed wildfire outcome in `T+1`.

- **Continuous target:** `burned_share_next_year`, the share of the cell burned in `T+1`.
- **Classification target:** `burned_next_year`, derived later from `burned_share_next_year` after inspecting the continuous-target distribution.
- **Historical-fire feature:** `fire_years_previous_10y_2km`, counting years from `T-10` through `T-1` inclusive in which the 2 km context buffer intersects burned area.

The canonical national seven-feature panel covers `T=2015-2024`. A separately validated backward extension provides `T=2010-2021` for model development: fitting uses `T=2010-2019`, validation uses `T=2020-2021`, and the final temporal test uses `T=2022-2024`. This requires ICNF annual burned-area archives for `2000-2025` inclusive. ICNF supplies only strictly pre-`T` historical-fire context and observed `T+1` outcome labels; it is never a same-year predictor. No temporal gap is required because the historical-fire window is `T-10` through `T-1`.

CLC is broad land-cover context rather than annual parcel-level land cover. Its retrospective assignment is CLC 2006 for `T=2010-2015`, CLC 2012 for `T=2016-2018`, and CLC 2018 for `T=2019-2025`. Every assigned reference year is no later than `T`, and the current official revised `V2020_20u1` package is used for each historical reference layer. Package-version metadata documents reproducibility; it is not evidence that the revised package was operationally available at `T`. ERA5-Land is coarse regional climate context, not 1 km weather: June-September (`JJAS`) values from `T` only provide mean 2 m temperature, total precipitation, and mean layer-1 soil water. Use the centroid-containing ERA5-Land cell when valid. For a mainland cell whose containing coarse cell is water-masked, use the deterministic nearest valid ERA5-Land land cell established by the coastal QA analysis. This preserves the product and `T`-only aggregation and is neither interpolation nor downscaling. This is retrospective covariate reconstruction, not an exact historical operational forecast.

## Annual operational forecast cycle

For an estimate of calendar year `Y`, the model uses all nine predictor values from the completed prior year `Y-1`. It may be refit only through labelled predictor year `Y-2`, whose observed ICNF outcome is `Y-1`. The scoring matrix intentionally has no target for `Y`.

- Current artefact: `data/processed/final_model_2010_2024/nine_feature_hurdle.joblib`, refit through observed outcome 2025.
- Current published score: `Y=2026`, using validated ERA5-Land JJAS `T=2025`, ICNF history 2015-2024, governed CLC 2018, and static terrain.
- Current status: scored and validated; see `reports/validation/operational_forecast_readiness.md` and `reports/validation/operational_forecast_2026_validation.md`.
- Run `scripts/prepare_operational_forecast.py` to rebuild the fixed model and validate readiness, then `scripts/score_operational_forecast.py` to derive the separate Parquet table and QGIS-ready GeoPackage. Both enforce the `forecast_year`, model version, source cutoff, and no-target rules.

## Data sources

The initial project uses four public source groups:

- ICNF annual burned-area cartography and the official structural wildfire-hazard raster;
- Copernicus CLC broad land-cover context and CAOP administrative boundaries;
- Copernicus DEM GLO-30 terrain data;
- ERA5-Land temperature, precipitation, and layer-1 soil-water data.

Access methods, expected fields, and known limitations are documented in the [source plan](docs/source_plan.md).

## Windows and Visual Studio Code setup

### 1. Install the prerequisites

Install:

- Python 3.13, 64-bit;
- Visual Studio Code;
- the VS Code **Python** extension;
- the VS Code **Jupyter** extension;
- Git, when the repository will be cloned from GitHub.

### 2. Open the project root

Open the following folder in Visual Studio Code, not only the `notebooks` folder:

```text
wildfire_property_screening_portugal/
```

### 3. Create the virtual environment and install dependencies

Open a PowerShell terminal in VS Code and run:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The project uses the full `.venv` Python path deliberately. This installs every package into the correct environment without requiring PowerShell environment activation.

If `py -3.13` is unavailable but Python 3.13 is already your default Python, use:

```powershell
py -m venv .venv
```

### 4. Select the notebook kernel

Open [`notebooks/00_environment_test.ipynb`](notebooks/00_environment_test.ipynb), then:

1. select the kernel in the upper-right corner;
2. choose **Python Environments**;
3. select `.venv\Scripts\python.exe`;
4. restart the kernel if another interpreter was previously selected;
5. choose **Run All**.

If an import such as `matplotlib` cannot be found, the notebook is almost certainly using a different kernel. Re-select the `.venv` kernel and run the notebook again.

### 5. Run the repository validation

From the project root, run:

```powershell
.\.venv\Scripts\python.exe tests\validate_environment.py
```

The validation script checks:

- exact package versions from `requirements.txt`;
- required imports;
- required project files;
- execution of `00_environment_test.ipynb`.

### CDS / ERA5-Land setup

To retrieve ERA5-Land data, create a CDS account and accept the terms for the required dataset in the CDS download form. Create `%USERPROFILE%\.cdsapirc` with the structure below, replacing the placeholder locally:

```text
url: https://cds.climate.copernicus.eu/api
key: TOKEN_PLACEHOLDER
```

Never commit, share, print, or copy the token into this repository. After dependencies are installed, retrieve the approved 2023 JJAS pilot GRIB with:

```powershell
.\.venv\Scripts\python.exe scripts\request_era5_land_pilot.py --download
```

## Notebook execution order

Run the notebooks in this order:

1. [`00_environment_test.ipynb`](notebooks/00_environment_test.ipynb) — validate the environment, imports, coordinate transformation, and output paths.
2. [`01_data_collection.ipynb`](notebooks/01_data_collection.ipynb) — inspect the immutable source inventory and provenance records.
3. [`02_data_preparation.ipynb`](notebooks/02_data_preparation.ipynb) — inspect preparation and validation evidence for canonical inputs.
4. [`03_eda.ipynb`](notebooks/03_eda.ipynb) — analyse coverage, missing values, distributions, and historical wildfire patterns.
5. [`04_modelling.ipynb`](notebooks/04_modelling.ipynb) — inspect the frozen train/validation and final-temporal model evidence; it does not tune or retrain models.
6. [`05_evaluation_recommendations.ipynb`](notebooks/05_evaluation_recommendations.ipynb) — inspect the historical/descriptive screening and official ICNF comparison.
7. [`06_final_charts.ipynb`](notebooks/06_final_charts.ipynb) — verify the six final presentation visuals against their real source artefacts without creating duplicate versions.

## Reviewer quick start

After installing the environment, run the notebooks in the order above from fresh kernels. The notebooks are inspection and orchestration layers: they use the existing validated artefacts and do not require a national rebuild for routine review.

Open [`qgis/wildfire_exposure_screening_portugal.qgz`](qgis/wildfire_exposure_screening_portugal.qgz) in QGIS for the interactive presentation. Its layers use repository-relative paths. See [`qgis/README.md`](qgis/README.md) for layer meanings, layout names, provenance, and limitations.

Key reviewer outputs are:

- screening GeoPackage: `data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg`, layer `historical_exposure_screening`;
- final maps and charts: `reports/figures/`;
- comparison tables: `reports/tables/`;
- validated analytical and presentation reports: `reports/validation/`.

Run full processing scripts only when regeneration is explicitly required. Read-only verification is available with:

```powershell
.\.venv\Scripts\python.exe scripts\build_historical_exposure_screening.py --validate-existing
.\.venv\Scripts\python.exe -m unittest tests.test_presentation_outputs -v
scripts\run_qgis_presentation_project.bat --validate-existing
```

Regenerating the QGIS project or presentation figures is a deliberate maintenance action; it is not part of the normal notebook review path.

## Project structure

```text
wildfire_property_screening_portugal/
├── .vscode/                  # Shared Visual Studio Code settings
├── data/
│   ├── raw/                  # Original source files; never modified
│   ├── external/             # External reference data
│   ├── interim/              # Temporary transformed data
│   └── processed/            # Analysis-ready datasets
├── notebooks/                # Numbered notebooks executed in order
├── src/                      # Reusable Python configuration and functions
├── tests/                    # Environment and notebook validation
├── reports/
│   ├── figures/              # Exported maps and charts
│   ├── tables/               # Exported summary and comparison tables
│   ├── bi_exports/           # Optional Power BI or Tableau files
│   └── validation/           # Validation reports
├── docs/                     # Project documentation
├── requirements.txt          # Exactly pinned initial dependencies
└── README.md
```

## Success criteria

The project will be considered complete when it:

- uses documented public data sources;
- covers mainland Portugal and explains any exclusions;
- produces a complete historical recurrence layer while reporting unmatched official evidence;
- produces clear maps/tables and limitations without purchase recommendations;
- reports final-temporal model evidence honestly, including its calibration limitation;
- compares historical recurrence with official ICNF hazard without treating either as validation of the other.

The historical screening output remains descriptive. The retained model is not used to label a location safe or to issue a purchase recommendation.

Detailed definitions are available in the [success criteria](docs/success_criteria.md).

## Current status and findings

The canonical panel, backward training extension, and EDA are validated. The frozen nine-feature hurdle has lower final-test MAE and substantially higher top-20% burned-share-mass capture than the historical baseline, but underpredicts the high-burned outcome associated with `T=2024`. It was refit through observed outcome 2025 and used to publish the validated 2026 comparative estimate. The historical screening layer remains supporting context. See `reports/validation/model_final_decision.md`, `reports/validation/operational_forecast_readiness.md`, and `reports/validation/operational_forecast_2026_validation.md`.

## BI dashboard

No BI tool has been selected yet. If Power BI or Tableau is used:

- working files will be stored in `reports/bi_exports/`;
- exported PDF, SVG, or PNG outputs will be stored in `reports/figures/`.

## Project documentation

- [Completed Repository Documentation Lab](docs/Repository_Documentation_Lab_Completed.docx) — the completed course starter describing the repository, environment, notebooks, README plan, data dictionary, and figure-export rules.
- [Project brief](docs/project_brief.md) — business decision, project goal, scope, limitation, and spatial design.
- [Data dictionary](docs/data_dictionary.md) — approved MVP fields, data types, units, sources, examples, and missing-value rules.
- [Source plan](docs/source_plan.md) — public sources, access methods, collection rules, and limitations.
- [Success criteria](docs/success_criteria.md) — project-completion criteria and model-performance targets.
- [Task list](docs/task_list.md) — planned work for data collection, preparation, modelling, evaluation, and reporting.

## Important limitation

“Lower exposure” does not mean “safe” or “zero risk.” A specific property still requires local checks of:

- vegetation close to the building;
- building materials and condition;
- road and evacuation access;
- water availability;
- surrounding land management;
- insurance conditions.
