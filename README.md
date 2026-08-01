# Reproducible Wildfire Exposure Screening for Residential Location Selection in Mainland Portugal

## Overview

This capstone project will help a prospective homebuyer compare residential areas in mainland Portugal from a **wildfire-exposure perspective**.

The project will combine public data on historical burned areas, land cover, terrain, and climate. It will produce reproducible maps and rankings that can be updated when new annual data becomes available.

> The project supports area shortlisting only. It does not decide whether a specific house is safe or whether it is the best property to buy.

## Spatial design

- **1 km × 1 km grid cell:** the analytical and prediction unit.
- **2 km surrounding buffer:** an initial distance used for selected vegetation, slope, and previous-fire features.

The 2 km value is not a second resolution. It will be tested later as a modelling assumption.

## Data sources

The MVP uses four public source groups:

- ICNF annual burned-area cartography;
- DGT COS/COSc land cover and CAOP boundaries;
- Copernicus DEM GLO-30;
- ERA5-Land temperature and precipitation.

Source details and limitations are documented in [the source plan](docs/source_plan.md).

## Windows and VS Code setup

### 1. Prerequisites

Install:

- Python 3.13, 64-bit;
- Visual Studio Code;
- the VS Code **Python** and **Jupyter** extensions;
- Git, if the repository will be cloned from GitHub.

### 2. Open the repository

Open the project folder in Visual Studio Code.

### 3. Create and activate the virtual environment

Run these commands in a VS Code PowerShell terminal:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks environment activation, run this once for the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 4. Select the Python environment

In VS Code:

1. open the Command Palette;
2. choose **Python: Select Interpreter**;
3. select `.venv\Scripts\python.exe`;
4. open a notebook and select the same environment as its kernel.

### 5. Validate the environment

```powershell
python tests\alidate_environment.py
```

This validates exact package versions, imports, key project files, and executes `notebooks/00_environment_test.ipynb`.

## Notebook execution order

1. [`00_environment_test.ipynb`](notebooks/00_environment_test.ipynb) — validate the environment and project paths.
2. [`01_data_collection.ipynb`](notebooks/01_data_collection.ipynb) — collect or import public raw data.
3. [`02_data_preparation.ipynb`](notebooks/02_data_preparation.ipynb) — clean, validate, standardise, and integrate data.
4. [`03_eda.ipynb`](notebooks/03_eda.ipynb) — analyse coverage, missing values, distributions, and historical patterns.
5. [`04_modelling.ipynb`](notebooks/04_modelling.ipynb) — create the MVP features, baseline, and ML models.
6. [`05_evaluation_recommendations.ipynb`](notebooks/05_evaluation_recommendations.ipynb) — evaluate the models and create recommendations only when justified.
7. [`06_final_charts.ipynb`](notebooks/06_final_charts.ipynb) — export final maps, figures, and tables.

## Project structure

```text
wildfire_property_screening_portugal/
├── .vscode/                  # Shared VS Code settings
├── data/
│   ├── raw/                  # Original source files; read-only
│   ├── external/             # External reference data not modified by the pipeline
│   ├── interim/              # Temporary transformed data
│   └── processed/            # Analysis-ready data
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

## Current findings

No analytical findings are reported yet. The project is currently at the repository-setup and data-feasibility stage. Findings will be added only after real data has been collected and validated.

## BI dashboard

No BI tool has been selected yet. If Power BI or Tableau is used, working files will be stored in `reports/bi_exports/`, while exported PDF, SVG, or PNG outputs will be stored in `reports/figures/`.

## Project documentation

- [Project brief](docs/project_brief.md) — decision, goal, scope, and spatial design.
- [Data dictionary](docs/data_dictionary.md) — approved MVP columns, units, examples, and missing-value rules.
- [Source plan](docs/source_plan.md) — public sources, access methods, and limitations.
- [Success criteria](docs/success_criteria.md) — completion criteria and model-performance targets.
- [Task list](docs/task_list.md) — repository, pilot, modelling, and reporting tasks.

## Important limitation

“Lower exposure” does not mean “safe” or “zero risk.” An individual property still requires local checks of vegetation, building materials, road and evacuation access, water availability, land management, and insurance conditions.
