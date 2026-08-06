# Operational forecast 2026 validation

## Contract

- Forecast year: 2026; predictor/input year: 2025.
- The scoring matrix contains the nine fixed predictors and intentionally contains no observed `burned_share_next_year` target.
- ICNF history is 2015-2024 only; no ICNF 2026 or 2027 record was read for scoring.
- ERA5-Land context is validated JJAS 2025, assigned by containing valid coarse cell or the existing nearest-valid-land fallback. It is not downscaled or interpolated.

## Published artifacts

- Feature matrix: `data/processed/operational_forecasts/forecast_2026_nine_feature_matrix.parquet` (89,112 rows; SHA-256 `1C131D00DA3CA70C9B6559BC1D5A98984A3F3FB254EA8B727D5DBA36A17BAD48`).
- Score table: `data/processed/operational_forecasts/forecast_2026_scores.parquet` (89,112 rows; SHA-256 `B9BDA6213B2DDC94FAB3587AEA303DD15CFF2F337ACD864F150E25C77F34AA03`).
- QGIS-ready layer: `data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg`, layer `estimated_comparative_exposure_2026`, 89,112 EPSG:3763 features.

## Validation

- Unique cells/rows: 89,112; target present: False; matrix missing values: 0; score missing values: 0.
- Reloaded model predictions identical to published scores: True.
- Model-provenance checksum reconciled after exact prediction equivalence: False.
- Climate assignment counts: {'containing_valid_era5_land_cell': 87606, 'nearest_valid_era5_land_cell': 1506}.
- Estimated burned-share summary: min 0.000000; median 0.003207; mean 0.010615; max 0.386156; exact-zero estimates 1,598.

## Interpretation and limitation

This is a year-specific comparative estimated burned share for broad 1 km mainland cells. It is not a probability, property-level forecast, safety guarantee, insurance estimate, or purchase recommendation. The fixed model underpredicted the high observed outcome associated with T=2024 during final evaluation; use ranks and estimates cautiously alongside the historical recurrence layer and official/local information.
