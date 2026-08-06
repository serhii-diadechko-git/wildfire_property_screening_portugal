# Repository cleanup and active-state inventory

**Status:** cleanup implemented and awaiting user review. No commit or push was performed.

## Active analytical contract

- Canonical geometry: `data/processed/reference/canonical_mainland_grid_1km.gpkg`, layer `canonical_mainland_grid_1km`; 89,112 unique valid EPSG:3763 cells with `cell_id` and geometry only.
- Canonical national table: `data/processed/national_panel_2015_2024.parquet`; seven documented base predictors and continuous `burned_share_next_year`.
- Final model contract: the seven predictors plus maximum monthly JJAS temperature and minimum monthly JJAS layer-1 soil water.
- Historical evaluation: fit `T=2010-2019`, validate `T=2020-2021`, frozen final test `T=2022-2024`.
- Operational state: fixed nine-feature hurdle refit through `T=2024` / observed outcome 2025; target-free 2026 comparative estimate published.
- Historical spatial state: separate 2016-2025 recurrence screening and official ICNF comparison.

## Cleanup phases completed

1. Extracted stable climate, geospatial, evaluation, baseline, and hurdle-model helpers into focused modules.
2. Reduced `src/model_v2_experiments.py` and `src/model_selection.py` to compatibility imports required by immutable historical joblib artefacts.
3. Removed superseded representative-pilot, 2023-to-2024 enrichment, initial seven-feature model-selection, exploratory V2 execution, and duplicate final-refit code/tests/scripts.
4. Consolidated one-off ERA5 request scripts into `scripts/download_era5_land_year.py`, which dry-runs by default and refuses raw overwrite.
5. Replaced the duplicate CLC 2018 interim record with the governed prepared CLC registry.
6. Moved the reusable grid role out of the pilot directory and removed legacy pilot attributes from the canonical geometry layer.
7. Updated collection/preparation notebooks to be thin read-only inspection layers.
8. Changed the presentation model-comparison figure to use the frozen final-test baseline and nine-feature results rather than retired seven-feature selection evidence.
9. Rebuilt the 2026 QGIS project after detecting absolute personal paths; the validated project now resolves relative repository paths.
10. Corrected the retained capstone PPTX/PDF after detecting superseded seven-feature/no-model wording and an embedded obsolete comparison chart. The refreshed deck uses the frozen nine-feature final-test evidence and keeps annual estimates separate from historical screening.

## Removed derived artifacts

Removed duplicate or superseded ignored data under the old pilot, `model_v2`, initial model-selection, and duplicate fixed-refit directories, plus the duplicate interim CLC GeoPackage and pilot figures. Immutable files under `data/raw/` were not changed. Active national batches, panels, extended nine-feature evaluation artifacts, operational model/score outputs, spatial outputs, and final presentation assets were retained.

Tracked deletions remain recoverable from Git history until the user chooses to commit. Ignored derived outputs can be regenerated from the retained immutable sources and maintained scripts.

## Validation gate

The cleanup is acceptable only when:

- source, panel, model, operational, QGIS, presentation, and notebook tests pass;
- all Python files compile;
- maintained imports contain no reference to deleted implementations;
- Markdown local links resolve;
- the national panel and operational artifacts retain their validated checksums/row contracts;
- `git diff --check` passes.

## Completed integrity validation

- Maintained automated tests: 56 passed. The memory-intensive CLC spatial-read test was run separately; the other 55 tests passed as a bounded group. A monolithic buffered discovery run exceeded the external 15-minute wrapper, so the same complete test set was executed in bounded groups.
- Python compilation: `src/`, `scripts/`, and `tests/` passed `compileall`.
- Notebook execution: `notebooks/01_data_collection.ipynb` and `notebooks/02_data_preparation.ipynb` passed from fresh kernels.
- Documentation links: all local Markdown links in 29 Markdown files resolved; no absolute personal Markdown link remains.
- QGIS: presentation and operational projects passed relative-path/layer-resolution tests; the operational QGIS file contains no absolute personal path.
- Presentation: corrected 13-slide PPTX passed the official overflow test; its regenerated 13-page PDF was rasterised and visually inspected.
- National panel: 891,120 rows, 89,112 cells, ten years per cell, zero duplicate keys and zero missing canonical values; checksum remained `AB5E684BCC670F5BD3A91967CBD1459CE3D4BB11E4AED75DE5C2E7244779C993`.
- Operational model: immutable final model checksum remained `F66BAC0F9D4FEAE0AE2657A7006B7C8DB51F08A9DB44728FE3BF0771CDF8E46A`.
- Raw data: no file under `data/raw/` was modified or removed.
- Whitespace validation: `git diff --check` passed; Git emitted only line-ending conversion warnings.
