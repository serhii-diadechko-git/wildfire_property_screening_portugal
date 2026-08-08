# Wildfire exposure screening — QGIS presentation project

Open `wildfire_exposure_screening_portugal.qgz` in QGIS 3.44 or later for the
historical/official comparison. Open
`wildfire_exposure_screening_portugal_2026.qgz` for the same presentation with
the separate target-free 2026 comparative-estimate layer. Both projects use
EPSG:3763 and store project-relative paths where QGIS can resolve them from
the repository root. They read existing GeoPackages only; they do not
duplicate or alter them.

After `python scripts/run_project.py --mode reproduce --confirm-rebuild`, both
projects have their required derived QA inputs: `ERA5 coastal fallback QA` and
`National 2024 snapshot — retrospective EDA only`. The snapshot is recreated
by `scripts/build_spatial_qa_outputs.py`; it is a QGIS inspection layer, not a
second analytical panel or a model result.

For a read-only package/layer/layout-path check, run `python -m unittest tests.test_presentation_outputs -v` from the repository root. On Windows, use `scripts\run_qgis_presentation_project.bat --validate-existing` for the historical project and `scripts\run_qgis_presentation_project.bat --validate-operational` for the 2026 project. On Linux/macOS, open the projects directly or invoke the build scripts from a PyQGIS-enabled environment. Regeneration creates only the project, annotation assets, and presentation exports; it does not rebuild the screening layer.

## Layer tree

The standard project `wildfire_exposure_screening_portugal.qgz` contains these
groups and layers:

- **01 Historical exposure screening** — **Historical exposure bands — 1 km
  cells**: observed 2016–2025 recurrence measured in a 2 km context.
- **02 Official ICNF comparison** — **ICNF structural hazard class —
  predominant class per 1 km cell**: predominant valid class from the official
  25 m SRUP-CPIR 2020–2030 source. The 2020–2030 label identifies the source,
  version, or planning period; it is not a prediction of fires in those years.
- **03 Context** — **Mainland Portugal boundary**: CAOP 2025 reference
  boundary.
- **04 QA reference — off by default** — **ERA5 coastal fallback QA** and
  **National 2024 snapshot — retrospective EDA only**.

The 2026 project `wildfire_exposure_screening_portugal_2026.qgz` contains the
same four groups and layers, plus this additional group at the top:

- **00 Annual comparative estimate — 2026**
  - **2026 estimated comparative wildfire exposure — 1 km cells**: target-free
    comparative estimates from 2025 predictor inputs, displayed as lower
    (0–50%), intermediate (50–80%), and higher (80–100%) estimated percentiles.

Both projects are presentation views of validated GeoPackages, not separate
analytical workflows. The 2026 estimate is not a calibrated probability,
property-level forecast, safety guarantee, insurance estimate, or purchase
recommendation.

The 2026 project adds a separate top-level group, **00 Annual comparative
estimate — 2026**, above the shared historical and official comparison groups.
The two projects are presentation views of validated GeoPackages, not separate
analytical workflows.

- **01 Historical exposure screening** — `Historical exposure bands — 1 km cells` is the validated descriptive layer. It represents **1 km mainland grid cells with fire recurrence measured in a 2 km context** for 2016–2025. Lower historical exposure does not mean safe.
- **02 Official ICNF comparison** — `ICNF structural hazard class — predominant class per 1 km cell` is a second styled view of the same screening GeoPackage. It displays the predominant valid class from the official ICNF 25 m SRUP-CPIR 2020-2030 structural-hazard source. The 2020-2030 label identifies the official source/version or planning period; it is not a prediction of fires in those years and is not this project’s prediction.
- **03 Context** — CAOP 2025 mainland Portugal boundary.
- **04 QA reference — off by default** — ERA5 coastal-fallback QA and the national 2024 snapshot. The latter is explicitly retrospective EDA only.

The historical palette progresses from sand through orange to dark red. It deliberately avoids representing lower historical exposure as “safe”. Official ICNF class colours are ordered separately and should not be interpreted as a project forecast.

## Layouts

- `Historical Wildfire Exposure Screening — Mainland Portugal`
- `Historical Exposure and Official ICNF Structural Hazard — Comparison`

Both layouts include a scale bar, north arrow, source note, EPSG:3763, the 1 km / 2 km context statement, and the mandatory limitations statement. PNG and PDF exports are stored in `reports/figures/`.

The two map exports and four validated chart/table visuals are indexed and checked by `notebooks/06_final_charts.ipynb`. That notebook verifies their stable paths and source artefacts without duplicating or rewriting the images.

## Provenance and limitations

The screening GeoPackage is `data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg`, layer `historical_exposure_screening` (89,112 features). It combines annual ICNF burned-area evidence for 2016–2025 with the separate official ICNF structural-hazard class, summarized from valid 25 m pixels to the predominant class in the canonical 1 km cell. This aggregation is a comparison/preparation step; it does not recalculate the official hazard or create a forecast. See `reports/validation/historical_exposure_screening_and_icnf_comparison.md` and `reports/validation/qgis_presentation_project_validation.md`.

This output is historical comparative exposure only. It is not a next-year forecast, property-level safety guarantee, or purchase recommendation. Use it for broad comparison and shortlisting, alongside site-specific and official information.

## Annual forecast layer status

The validated QGIS-ready 2026 estimate is `data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg`, layer `estimated_comparative_exposure_2026` (89,112 EPSG:3763 features). Add it as a separate layer; do not replace or relabel the historical layer, which remains supporting 2016-2025 evidence. Its key fields are `forecast_year`, `prediction_input_year`, `predicted_burned_share_next_year`, `predicted_exposure_percentile`, `model_sha256`, and `score_status`.

Use the 2026 layer to compare broad cells by a year-specific estimated burned share and percentile. It is not a probability, property-level forecast, safety guarantee, insurance estimate, or purchase recommendation. See `reports/validation/operational_forecast_2026_validation.md` before presentation or interpretation.

For a ready-to-open combined view, use `wildfire_exposure_screening_portugal_2026.qgz`. It preserves the historical presentation project and adds the separate **00 Annual comparative estimate — 2026** group. Its display-only percentile bands do not alter the validated model score or make a safety claim. Regenerate that portable project, only when the validated forecast GeoPackage exists and QGIS is installed, with `scripts\run_qgis_presentation_project.bat scripts\build_operational_forecast_qgis_project.py`.
