# Reproducible Wildfire Exposure Screening for Residential Location Selection in Mainland Portugal

## Project overview

This capstone project will help a prospective homebuyer compare residential areas in mainland Portugal from a **wildfire-exposure perspective**.

The project will combine public geospatial data on historical burned areas, land cover, terrain, and climate. The result will be a reproducible screening process that identifies residential areas with comparatively lower or higher wildfire exposure and can be updated when new annual data becomes available.

> The project supports **area shortlisting only**. It does not determine whether a specific house is safe or whether it is the best property to buy.

## Business problem

Buying a home is a long-term and expensive decision. Wildfire exposure varies significantly across mainland Portugal, but relevant information is distributed across historical fire maps, land-cover datasets, climate data, and official hazard products.

A property buyer needs a clear and consistent way to compare locations before spending time and money on individual properties.

## Decision supported

**Decision-maker:** a prospective homebuyer choosing a location in mainland Portugal.

**Decision:** which residential areas should be:

- shortlisted for further property search;
- reviewed with caution;
- deprioritised because of higher wildfire exposure;
- marked as insufficient evidence when the available data is incomplete or uncertain.

## Project goal

Build a reproducible geospatial data-science and machine-learning workflow that:

1. estimates relative wildfire exposure across mainland Portugal;
2. applies the results only to locations that meet a validated residential-eligibility rule;
3. compares structural exposure with the latest annual conditions;
4. identifies areas with consistently lower or higher exposure;
5. produces understandable maps, rankings, and uncertainty flags;
6. supports annual rescoring when new public data becomes available.

## Planned outputs

- a national wildfire-exposure map;
- a residential-location screening map;
- ranked results by grid cell and administrative area;
- recommendation categories with uncertainty information;
- model evaluation against a historical-fire-frequency baseline;
- a reproducible data-preparation and scoring pipeline;
- a documented annual update procedure.

## Analytical and spatial output layers

- `data/processed/national_panel_2015_2024.parquet` is the canonical machine-learning table: one `cell_id` x `observation_year` row, with no repeated geometry.
- `data/processed/pilot_2023_to_2024/pilot_2023_to_2024_icnf_caop.gpkg` remains the reusable EPSG:3763 canonical grid-geometry lookup.
- `data/processed/spatial_qa/era5_land_coastal_fallback_qa.gpkg`, layer `era5_coastal_fallback_qa`, is a 1,506-feature QA/presentation layer documenting the systematic ERA5-Land coastal fallback.
- `data/processed/spatial_qa/national_panel_snapshot_2024.gpkg`, layer `national_panel_snapshot_2024`, is an 89,112-feature GIS/EDA snapshot containing the seven predictors, observed 2025 target and climate-assignment method for `T=2024`. It is not the canonical ML table.

Later model prediction/exposure and residential-screening/recommendation GeoPackages are planned outputs. They must not be created or documented as results until validated models and recommendation rules exist.

## Spatial design

- **1 km × 1 km grid cell:** the analytical and prediction unit.
- **2 km surrounding buffer:** an initial distance used for selected vegetation, slope, and previous-fire features.

The 2 km value is not a second resolution. It is a modelling assumption that will be tested during sensitivity analysis.

## Temporal methodology and data scope

> Canonical gate: train T=2015–2019; validate T=2020–2021; final temporal test T=2022–2024 (outcomes 2023–2025). The 1 km EPSG:3763 cell is the only analytical unit; 2 km is an outward context buffer. The 2023→2024 artifact is a feasibility pilot, not a final test.

Each analytical record is one 1 km x 1 km grid cell for predictor reference year `T`. Predictor information available at `T` is used to estimate the observed wildfire outcome in `T+1`.

- **Continuous target:** `burned_share_next_year`, the share of the cell burned in `T+1`.
- **Classification target:** `burned_next_year`, derived later from `burned_share_next_year` after inspecting the continuous-target distribution.
- **Historical-fire feature:** `fire_years_previous_10y_2km`, counting years from `T-10` through `T-1` inclusive in which the 2 km context buffer intersects burned area.

The approved predictor-reference panel is `T = 2015` through `2024`: training years `2015-2019`, validation years `2020-2021`, and final temporal test years `2022-2024`. This requires ICNF annual burned-area archives for `2005-2025` inclusive. ICNF supplies only strictly pre-`T` historical-fire context and observed `T+1` outcome labels; it is never a same-year predictor. No temporal gap is required because the historical-fire window is `T-10` through `T-1`.

CLC is broad land-cover context rather than annual parcel-level land cover. Its retrospective assignment is CLC 2006 for `T=2015`, CLC 2012 for `T=2016-2018`, and CLC 2018 for `T=2019-2024`. Every assigned reference year is no later than `T`, and the current official revised `V2020_20u1` package is used for each historical reference layer. Package-version metadata documents reproducibility; it is not evidence that the revised package was operationally available at `T`. ERA5-Land is coarse regional climate context, not 1 km weather: June–September (`JJAS`) values from `T` only provide mean 2 m temperature, total precipitation, and mean layer-1 soil water. Use the centroid-containing ERA5-Land cell when valid. For a mainland cell whose containing coarse cell is water-masked, use the deterministic nearest valid ERA5-Land land cell established by the coastal QA analysis. This preserves the product and `T`-only aggregation and is neither interpolation nor downscaling. This is retrospective covariate reconstruction, not an exact historical operational forecast.

## Data sources

The initial project uses four public source groups:

- ICNF annual burned-area cartography;
- Copernicus CLC broad land-cover context and CAOP administrative boundaries;
- Copernicus DEM GLO-30 terrain data;
- ERA5-Land temperature and precipitation data.

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

The first notebook cell prints the active Python executable. It should point to:

```text
...\wildfire_property_screening_portugal\.venv\Scripts\python.exe
```

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

1. [`00_environment_test.ipynb`](notebooks/00_environment_test.ipynb) — validate the environment, imports, coordinate transformation, modelling library, and output paths.
2. [`01_data_collection.ipynb`](notebooks/01_data_collection.ipynb) — collect or import public raw data and record source metadata.
3. [`02_data_preparation.ipynb`](notebooks/02_data_preparation.ipynb) — clean, validate, standardise, and integrate the geospatial data.
4. [`03_eda.ipynb`](notebooks/03_eda.ipynb) — analyse coverage, missing values, distributions, and historical wildfire patterns.
5. [`04_modelling.ipynb`](notebooks/04_modelling.ipynb) — create the approved MVP features, historical baseline, and machine-learning models.
6. [`05_evaluation_recommendations.ipynb`](notebooks/05_evaluation_recommendations.ipynb) — evaluate the models and produce recommendations only when the evidence is strong enough.
7. [`06_final_charts.ipynb`](notebooks/06_final_charts.ipynb) — export final maps, figures, and tables for the report and README.

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
│   ├── tables/               # Exported ranked tables
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
- assigns recommendations only when mandatory inputs are available;
- produces clear maps, ranked tables, uncertainty flags, and limitations;
- compares the machine-learning model with a transparent historical baseline;
- reports honestly whether the model is strong enough to support predictive recommendations.

The initial technical targets include scoring or documenting an exclusion for at least **95% of eligible cells** and testing whether the highest-risk **20%** of predictions captures at least **40%** of affected cells. These are evaluation targets, not guaranteed results.

Detailed definitions are available in the [success criteria](docs/success_criteria.md).

## Current status and findings

The canonical 891,120-row national panel is validated and model-readiness EDA is complete. The systematic ERA5-Land coastal mask was resolved with a validated nearest-valid-land fallback; all seven predictors and the continuous target are complete. Modelling has not started.

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
