# Wildfire exposure screening — QGIS presentation project

Open `wildfire_exposure_screening_portugal.qgz` in QGIS 3.44 or later. The project uses EPSG:3763 and stores project-relative paths where QGIS can resolve them from the repository root. It reads existing GeoPackages only; it does not duplicate or alter them.

For a read-only package/layer/layout-path check, run `python -m unittest tests.test_presentation_outputs -v` from the repository root. On Windows, `scripts\run_qgis_presentation_project.bat --validate-existing` provides an optional QGIS helper. On Linux/macOS, open the project directly or invoke the build script from a PyQGIS-enabled environment. Regeneration creates only the project, annotation assets, and presentation exports; it does not rebuild the screening layer.

## Layer tree

- **01 Historical exposure screening** — `Historical exposure bands — 1 km cells` is the validated descriptive layer. It represents **1 km mainland grid cells with fire recurrence measured in a 2 km context** for 2016–2025. Lower historical exposure does not mean safe.
- **02 Official ICNF comparison** — `ICNF structural hazard class — predominant class per 1 km cell` is a second styled view of the same screening GeoPackage. It displays the predominant valid class from the official ICNF 25 m structural wildfire-hazard map; it is not this project’s prediction.
- **03 Context** — CAOP 2025 mainland Portugal boundary.
- **04 QA reference — off by default** — ERA5 coastal-fallback QA and the national 2024 snapshot. The latter is explicitly retrospective EDA only.

The historical palette progresses from sand through orange to dark red. It deliberately avoids representing lower historical exposure as “safe”. Official ICNF class colours are ordered separately and should not be interpreted as a project forecast.

## Layouts

- `Historical Wildfire Exposure Screening — Mainland Portugal`
- `Historical Exposure and Official ICNF Structural Hazard — Comparison`

Both layouts include a scale bar, north arrow, source note, EPSG:3763, the 1 km / 2 km context statement, and the mandatory limitations statement. PNG and PDF exports are stored in `reports/figures/`.

The two map exports and four validated chart/table visuals are indexed and checked by `notebooks/06_final_charts.ipynb`. That notebook verifies their stable paths and source artefacts without duplicating or rewriting the images.

## Provenance and limitations

The screening GeoPackage is `data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg`, layer `historical_exposure_screening` (89,112 features). It combines annual ICNF burned-area evidence for 2016–2025 with the separate official ICNF structural-hazard class, summarized to the canonical 1 km cell by predominant valid 25 m class. See `reports/validation/historical_exposure_screening_and_icnf_comparison.md` and `reports/validation/qgis_presentation_project_validation.md`.

This output is historical comparative exposure only. It is not a next-year forecast, property-level safety guarantee, or purchase recommendation. Use it for broad comparison and shortlisting, alongside site-specific and official information.

## Annual forecast layer status

The validated QGIS-ready 2026 estimate is `data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg`, layer `estimated_comparative_exposure_2026` (89,112 EPSG:3763 features). Add it as a separate layer; do not replace or relabel the historical layer, which remains supporting 2016-2025 evidence. Its key fields are `forecast_year`, `prediction_input_year`, `predicted_burned_share_next_year`, `predicted_exposure_percentile`, `model_sha256`, and `score_status`.

Use the 2026 layer to compare broad cells by a year-specific estimated burned share and percentile. It is not a probability, property-level forecast, safety guarantee, insurance estimate, or purchase recommendation. See `reports/validation/operational_forecast_2026_validation.md` before presentation or interpretation.

For a ready-to-open combined view, use `wildfire_exposure_screening_portugal_2026.qgz`. It preserves the historical presentation project and adds the separate **00 Annual comparative estimate — 2026** group. Its display-only percentile bands do not alter the validated model score or make a safety claim. Regenerate that portable project, only when the validated forecast GeoPackage exists and QGIS is installed, with `scripts\run_qgis_presentation_project.bat scripts\build_operational_forecast_qgis_project.py`.
