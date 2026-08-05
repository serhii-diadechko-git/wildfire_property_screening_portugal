# Spatial output registry

The canonical machine-learning dataset remains `data/processed/national_panel_2015_2024.parquet`. Geometry is not repeated for all ten cell-years.

## Existing spatial outputs

| Purpose | Path and layer | CRS | Features | Key fields | Role |
|---|---|---|---:|---|---|
| Canonical reusable 1 km grid geometry | `data/processed/pilot_2023_to_2024/pilot_2023_to_2024_icnf_caop.gpkg` | EPSG:3763 | 89,112 | `cell_id`, grid geometry and established pilot attributes | Canonical spatial lookup; join analytical Parquet rows by `cell_id`. |
| ERA5-Land coastal fallback QA | `data/processed/spatial_qa/era5_land_coastal_fallback_qa.gpkg`, layer `era5_coastal_fallback_qa` | EPSG:3763 | 1,506 | `cell_id`, `land_class`, `orig_era_lat`, `orig_era_lon`, `fallback_lat`, `fallback_lon`, `distance_km`, `assignment_method` | QA/presentation output, not a model table. |
| National `T=2024` GIS snapshot | `data/processed/spatial_qa/national_panel_snapshot_2024.gpkg`, layer `national_panel_snapshot_2024` | EPSG:3763 | 89,112 | `cell_id`, `observation_year`, `outcome_year`, seven predictors, `burned_share_next_year`, `climate_assignment` | GIS/EDA/presentation output, not the canonical ML table. The target is observed 2025 burned share, not a prediction. |

## Planned outputs after modelling

- A model prediction/exposure GeoPackage may be created only after the modelling and temporal-evaluation gates pass.
- A residential screening/recommendation GeoPackage may be created only after recommendation categories, uncertainty and insufficient-evidence rules are frozen.
- Important spatial EDA diagnostics may be added when they answer a defined analytical question; ten geometry copies of the national panel are not planned.
