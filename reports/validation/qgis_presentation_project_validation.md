# QGIS presentation-project validation

Validation date: 2026-08-09.

Both portable QGIS projects reference existing, validated GeoPackage inputs
only. They do not alter or duplicate screening or model data.

| Project | CRS | Map layers | Purpose |
|---|---|---:|---|
| `qgis/wildfire_exposure_screening_portugal.qgz` | EPSG:3763 | 5 | Historical recurrence, official ICNF structural-hazard comparison, boundary, and off-by-default QA layers. |
| `qgis/wildfire_exposure_screening_portugal_2026.qgz` | EPSG:3763 | 6 | The same historical/official context plus the separate target-free 2026 comparative-estimate layer. |

The historical screening and annual estimate layers each contain 89,112
canonical mainland 1 km cells. Layout aliases for the historical project were
validated. The 2026 project's layer path and required annual estimate are
validated by the operational QGIS check; see `operational_forecast_2026_validation.md`.

## Layout exports

| Layout | PNG | PDF |
|---|---|---|
| historical | `reports/figures/historical_wildfire_exposure_screening_mainland_portugal.png` | `reports/figures/historical_wildfire_exposure_screening_mainland_portugal.pdf` |
| comparison | `reports/figures/historical_exposure_and_official_icnf_structural_hazard_comparison.png` | `reports/figures/historical_exposure_and_official_icnf_structural_hazard_comparison.pdf` |

## Interpretation boundary

The map represents **1 km mainland grid cells with fire recurrence measured in a 2 km context**. It is historical comparative exposure only, not a next-year forecast, property-level safety guarantee, or purchase recommendation. The official ICNF structural-hazard view is a separate official product summarized to the same 1 km comparison resolution; it is not this project's prediction.
