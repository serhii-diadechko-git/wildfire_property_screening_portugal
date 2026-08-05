# QGIS presentation project validation

The portable QGIS project was created from existing, validated GeoPackage inputs only. It does not alter or duplicate the screening data.

- Project: `qgis/wildfire_exposure_screening_portugal.qgz`
- Project CRS: EPSG:3763
- Project layers: 5
- Layout aliases validated: True
- Screening-view features validated: 89,112 for each styled view

## Layout exports

| Layout | PNG | PDF |
|---|---|---|
| historical | `reports/figures/historical_wildfire_exposure_screening_mainland_portugal.png` | `reports/figures/historical_wildfire_exposure_screening_mainland_portugal.pdf` |
| comparison | `reports/figures/historical_exposure_and_official_icnf_structural_hazard_comparison.png` | `reports/figures/historical_exposure_and_official_icnf_structural_hazard_comparison.pdf` |

## Interpretation boundary

The map represents **1 km mainland grid cells with fire recurrence measured in a 2 km context**. It is historical comparative exposure only, not a next-year forecast, property-level safety guarantee, or purchase recommendation. The official ICNF structural-hazard view is a separate official product summarized to the same 1 km comparison resolution; it is not this project's prediction.
