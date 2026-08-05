# Wildfire exposure screening — QGIS presentation project

Open `wildfire_exposure_screening_portugal.qgz` in QGIS 3.44 or later. The project uses EPSG:3763 and stores project-relative paths where QGIS can resolve them from the repository root. It reads existing GeoPackages only; it does not duplicate or alter them.

To regenerate the project and its layout exports on this workstation, run `scripts\run_qgis_presentation_project.bat` from the repository root. It uses the installed QGIS runtime and creates only the project, annotation assets, and presentation exports; it does not rebuild the screening layer.

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

## Provenance and limitations

The screening GeoPackage is `data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg`, layer `historical_exposure_screening` (89,112 features). It combines annual ICNF burned-area evidence for 2016–2025 with the separate official ICNF structural-hazard class, summarized to the canonical 1 km cell by predominant valid 25 m class. See `reports/validation/historical_exposure_screening_and_icnf_comparison.md` and `reports/validation/qgis_presentation_project_validation.md`.

This output is historical comparative exposure only. It is not a next-year forecast, property-level safety guarantee, or purchase recommendation. Use it for broad comparison and shortlisting, alongside site-specific and official information.
