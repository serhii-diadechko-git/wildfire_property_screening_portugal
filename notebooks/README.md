# Notebook responsibilities and execution order

Notebooks are thin orchestration and inspection layers. Reusable calculations live in `src/`, executable runners live in `scripts/`, and validated results live in `reports/validation/`.

## Standalone reviewer setup

From the repository root on Windows, install the pinned environment and select `.venv\Scripts\python.exe` as the Jupyter kernel:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run each notebook from a fresh kernel in the order below. Routine notebook review reads the validated project artefacts; it does not rebuild the national panel, screening GeoPackage, QGIS project, or final figures.

1. `00_environment_test.ipynb` — environment, import, CRS and output-path checks only.
2. `01_data_collection.ipynb` — immutable source inventory and provenance only; no new collection.
3. `02_data_preparation.ipynb` — preparation and validation evidence for canonical inputs.
4. `03_eda.ipynb` — descriptive EDA and spatial/temporal evidence.
5. `04_modelling.ipynb` — inspects the frozen train/validation and final-temporal model evidence; it does not tune or retrain models.
6. `05_evaluation_recommendations.ipynb` — inspects the historical/descriptive exposure screening and official ICNF comparison created by `scripts/build_historical_exposure_screening.py`.
7. `06_final_charts.ipynb` — verifies the six presentation-ready visuals, their stable paths, and their real source artefacts; it does not create duplicate figure versions.

The final temporal evaluation is complete. The retained nine-feature hurdle is refit through observed outcome 2025 for an annual operational cycle. The validated `2026` estimate uses an unlabelled T=2025 matrix; see `reports/validation/operational_forecast_readiness.md` and `reports/validation/operational_forecast_2026_validation.md`. Any forecast layer is a continuous comparative estimate, not a probability, property-level safety assessment, or purchase recommendation. The historical wildfire-exposure screening layer remains supporting context for broad location comparison.

The validated result represents **1 km mainland grid cells with fire recurrence measured in a 2 km context**, using observed ICNF evidence from 2016–2025.

## Presentation outputs

- Interactive project: `qgis/wildfire_exposure_screening_portugal.qgz`
- QGIS instructions and layer meanings: `qgis/README.md`
- Screening data: `data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg`, layer `historical_exposure_screening`
- Final maps and charts: `reports/figures/`
- Summary and comparison tables: `reports/tables/`
- Validation evidence: `reports/validation/`

Open the `.qgz` project in QGIS after cloning or moving the whole repository so its relative layer paths remain intact.

## Regeneration versus verification

Full processing scripts should be run only when regeneration is required. For normal review, execute notebooks 05 and 06 and use these read-only checks:

```powershell
.\.venv\Scripts\python.exe scripts\build_historical_exposure_screening.py --validate-existing
.\.venv\Scripts\python.exe -m unittest tests.test_presentation_outputs -v
scripts\run_qgis_presentation_project.bat --validate-existing
```

The chart-building functions in `src/final_visuals.py` and QGIS build scripts remain the reproducible sources for deliberate regeneration. The consolidated notebooks verify the already validated deliverables by default.
