# Spatial output registry

The canonical machine-learning dataset remains `data/processed/national_panel_2015_2024.parquet`. Geometry is not repeated for all ten cell-years.

## Existing spatial outputs

| Purpose | Path and layer | CRS | Features | Key fields | Role |
|---|---|---|---:|---|---|
| Canonical reusable 1 km grid geometry | `data/processed/pilot_2023_to_2024/pilot_2023_to_2024_icnf_caop.gpkg` | EPSG:3763 | 89,112 | `cell_id`, grid geometry and established pilot attributes | Canonical spatial lookup; join analytical Parquet rows by `cell_id`. |
| ERA5-Land coastal fallback QA | `data/processed/spatial_qa/era5_land_coastal_fallback_qa.gpkg`, layer `era5_coastal_fallback_qa` | EPSG:3763 | 1,506 | `cell_id`, `land_class`, `orig_era_lat`, `orig_era_lon`, `fallback_lat`, `fallback_lon`, `distance_km`, `assignment_method` | QA/presentation output, not a model table. |
| National `T=2024` GIS snapshot | `data/processed/spatial_qa/national_panel_snapshot_2024.gpkg`, layer `national_panel_snapshot_2024` | EPSG:3763 | 89,112 | `cell_id`, `observation_year`, `outcome_year`, seven predictors, `burned_share_next_year`, `climate_assignment` | GIS/EDA/presentation output, not the canonical ML table. The target is observed 2025 burned share, not a prediction. |
| Historical residential wildfire-exposure screening | `data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg`, layer `historical_exposure_screening` | EPSG:3763 | 89,112 | `cell_id`, 2016-2025 recurrence measured in a 2 km context for each 1 km mainland grid cell, recurrence-only historical band, CLC/slope context, predominant official ICNF hazard class, evidence status | Final historical/descriptive comparison layer; not a prediction, probability, safety guarantee, official-map validation, or purchase recommendation. |

## GIS presentation outputs

| Purpose | Path | CRS / content | Role |
|---|---|---|---|
| Portable QGIS presentation project | `qgis/wildfire_exposure_screening_portugal.qgz` | EPSG:3763; relative GeoPackage layer paths; historical screening, official ICNF comparison, CAOP boundary, and two off-by-default QA layers | GIS inspection and presentation project; it is not the canonical analytical table. |
| Historical screening layout | `reports/figures/historical_wildfire_exposure_screening_mainland_portugal.png` and `.pdf` | 1 km mainland cells; 2016-2025 recurrence measured in a 2 km context | Presentation output; historical comparative exposure only. |
| Historical / official comparison layout | `reports/figures/historical_exposure_and_official_icnf_structural_hazard_comparison.png` and `.pdf` | Side-by-side 1 km views of historical recurrence bands and predominant official ICNF 25 m structural-hazard classes | Descriptive comparison only; not an accuracy assessment or project prediction. |

## Conditional future outputs

- No model prediction/exposure or purchase-recommendation GeoPackage is authorized because no candidate passed the train/validation gate.
- Such outputs would require a separate future methodology decision and a new validated predictive gate; they are not part of the current capstone result.
- Important spatial EDA diagnostics may be added when they answer a defined analytical question; ten geometry copies of the national panel are not planned.
