# Data Dictionary

## Analytical unit

> The retained analytical model has exactly nine predictors. Identifiers and geometry are stored separately from the tabular model matrix.

One analytical record represents one **1 km grid cell and one predictor reference year `T`**.

Predictors available for year `T` are used to estimate the observed wildfire outcome in year `T+1`.

## Spatial definitions

- **Grid resolution:** 1 km x 1 km.
- **Context buffer:** 2 km around the 1 km cell.
- **Purpose of the buffer:** measure nearby vegetation, terrain, and previous fire activity that may affect the residential location.

The 2 km buffer is not a second grid resolution. It is the fixed context definition used by this completed project. No alternative-buffer sensitivity analysis was completed, so the chosen distance remains a documented limitation for future research rather than an empirically optimized value.

## Temporal scope and split

In ERA5-Land, `2m_temperature` means air temperature at a standard height of 2 metres above the land surface. The `2m` label describes measurement height, not a 2 m spatial resolution or a 2 m context buffer.

For ERA5-Land soil water, `layer 1` means the shallowest soil layer, approximately the top 0–7 cm. It is a volumetric water-content measurement (`m³/m³`), not a GIS layer. ERA5-Land also provides deeper soil layers, but this project uses only layer 1 to represent shallow warm-season soil moisture.

The labelled nine-feature model panel covers predictor years `T=2010-2024`. Final-model selection used `T=2010-2019` for fitting and `T=2020-2021` for validation only; no `T=2022-2024` row was read during selection. The later labelled years are used for the operational refit through observed outcome 2025. The ICNF archive range is `2000-2025` inclusive.

There is no temporal gap between historical-fire information and predictor year `T`. `fire_years_previous_10y_2km` uses only the inclusive pre-`T` window `T-10` through `T-1`, which is information genuinely available at prediction time and is not leakage. ICNF burned areas are never a same-year `T` predictor.

CLC is broad, retrospective land-cover context rather than annual parcel-level land cover. Assign CLC 2006 to `T=2010-2015`, CLC 2012 to `T=2016-2018`, and CLC 2018 to `T=2019-2025`. The assigned CLC reference year must be no later than `T`; the current official revised package is used for each reference layer. This is reproducible retrospective covariate reconstruction and does not imply that the later revised package was operationally available at `T`. ERA5-Land is coarse regional context, not 1 km weather: its JJAS values from `T` only use the centroid-containing ERA5-Land cell when valid. If that source cell is water-masked for a mainland analytical cell, use the deterministic nearest valid ERA5-Land land cell established by `reports/validation/era5_coastal_fallback_analysis.md`. This is a source-cell fallback, not interpolation or downscaling.

For an operational score for forecast year `Y`, build one unlabelled row per cell using `T=Y-1`, refit only through labelled predictor year `Y-2`, and leave `burned_share_next_year` absent. For example, a 2026 estimate uses T=2025 predictor values and a model trained through observed outcome 2025. The source cutoff and model checksum are mandatory output metadata.

## Technical identifiers

These fields are required to store and join the analytical records. They are not predictive features.

| Column | Type | Meaning | Source / derivation |
|---|---|---|---|
| `cell_id` | string | Stable identifier for one 1 km grid cell. | Generated analytical grid |
| `observation_year` | integer | Year associated with the predictor data. | Derived |
| `geometry` | geometry | Polygon geometry of the 1 km grid cell. | Generated analytical grid |
| `land_cover_reference_year` | integer | CLC reference year assigned under the governed retrospective rule; must be `<= observation_year`. | CLC governance metadata |
| `land_cover_release_id` | string | Current official revised package identifier used for that reference layer. | CLC package provenance |
| `land_cover_release_date` | string/date | Official package release/update date, or an explicit statement that the exact day is unavailable. | CLC package provenance |

## Nine-feature analytical columns

This table matches the minimum schema in the completed Capstone Kickoff Workbook.

| Column | Type | Unit / values | Description | Source / derivation |
|---|---|---|---|---|
| `cell_year_id` | string | `<cell_id>_<year>` | Unique key for one 1 km cell and observation year. | Generated from `cell_id` and `observation_year` |
| `built_up_share` | float | 0-1 | Share of the mainland-land portion of the 1 km cell classified as built or artificial land. It is an initial residential-relevance proxy, not proof that the cell is residential. | Governed retrospective Copernicus CLC broad classes; equal-area intersection in EPSG:3035 |
| `forest_shrub_share_2km` | float | 0-1 | Combined forest and shrubland share of mainland land within the fixed 2 km outward buffer around the cell. | Governed retrospective Copernicus CLC broad classes; equal-area intersection in EPSG:3035 |
| `mean_slope_2km` | float | degrees | Mean terrain slope within the same mainland-masked 2 km buffer. Elevations are reprojected to a metric CRS before slope is calculated; slope is never calculated in geographic degrees. | Derived from Copernicus DEM GLO-30 |
| `fire_years_previous_10y_2km` | integer | count | Number of years from `T-10` through `T-1` inclusive in which the 2 km buffer intersected an ICNF burned-area polygon. This is strictly pre-`T` information. | ICNF burned-area intersections |
| `warm_season_mean_2m_temperature_c` | float | degrees Celsius | Mean ERA5-Land 2 m temperature for June–September (`JJAS`) in predictor year `T`. | ERA5-Land `2m_temperature` |
| `warm_season_total_precipitation_mm` | float | millimetres | Total ERA5-Land precipitation for `JJAS` in predictor year `T`. | ERA5-Land `total_precipitation` |
| `warm_season_mean_soil_water_layer1` | float | m³/m³ | Mean ERA5-Land volumetric soil water in the shallow layer 1 (approximately 0–7 cm below the surface) for `JJAS` in predictor year `T`. | ERA5-Land `volumetric_soil_water_layer_1` |
| `warm_season_max_monthly_2m_temperature_c` | float | degrees Celsius | Maximum of the four monthly mean 2 m temperatures for June-September in predictor year `T`. | ERA5-Land `2m_temperature`; T-only JJAS GRIB |
| `warm_season_min_monthly_soil_water_layer1` | float | m³/m³ | Minimum of the four monthly mean layer-1 (approximately 0–7 cm) volumetric soil-water values for June-September in predictor year `T`; a shallow-soil dryness extreme. | ERA5-Land `volumetric_soil_water_layer_1`; T-only JJAS GRIB |
| `burned_share_next_year` | float | 0-1 | Share of the mainland-land portion of the 1 km cell intersected by the dissolved burned-area geometry in observed outcome year `T+1`. This is the main continuous target. | ICNF burned-area intersections after derived-only geometry repair and annual union |

## Derived classification target

| Column | Type | Meaning |
|---|---|---|
| `burned_next_year` | boolean | Classification target for observed outcome year `T+1`, derived later from `burned_share_next_year` using a documented threshold selected after continuous-target-distribution analysis. |

## Model and decision outputs

The retained final model is a continuous comparative estimate, not a probability, safety score, or buyer-facing recommendation. None of these model-output fields is present in the historical screening layer. A forecast GeoPackage is created only after its source preflight passes.

| Column | Type | Meaning |
|---|---|---|
| `predicted_burned_share_next_year` | float, 0-1 | Final nine-feature two-stage burned-share regression output: estimated share of the cell's mainland-land area burned in `T+1`. It is a continuous research estimate, not a probability or recommendation. |
| `forecast_year` | integer | Calendar year estimated by an operational scoring output; equal to `observation_year + 1`. |
| `prediction_input_year` | integer | Completed predictor year used for all dynamic inputs; equal to `forecast_year - 1`. |
| `model_sha256` | string | Checksum of the exact serialized nine-feature model used for scoring. |
| `score_status` | string | `scored_comparative_estimate`, `blocked_missing_input`, or `insufficient_evidence`; never interpret an absent score as low exposure. |
| `predicted_wildfire_probability` | float, 0-1 | Conditional future output only if a separate classification model and `burned_next_year` threshold are later documented. Probability metrics and calibration do not apply to the initial regression output. |

## Historical exposure screening output

These fields exist in `data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg`, layer `historical_exposure_screening`. They describe **1 km mainland grid cells with fire recurrence measured in a 2 km context**. They are descriptive evidence, not model features or predictions.

| Column | Type | Meaning |
|---|---|---|
| `cell_id` | string | Stable canonical 1 km mainland cell identifier. |
| `evidence_as_of_year` | integer | Latest complete observed burned-area year used: 2025. |
| `history_start_year` | integer | First year in the recurrence window: 2016. |
| `history_end_year` | integer | Last year in the recurrence window: 2025. |
| `fire_years_history_10y_2km` | integer, 0-10 | Number of distinct years in 2016-2025 when the mainland-masked 2 km context intersected annual dissolved ICNF burned-area geometry. |
| `historical_exposure_band` | string | Recurrence-only empirical band: `lower` for 0-1 years, `moderate` for 2-3, and `higher` for 4-10. |
| `historical_exposure_note` | string | Human-readable recurrence range and caution that lower does not mean safe. |
| `forest_shrub_share_2km` | float, 0-1 | CLC 2018 forest/shrub share in the mainland-masked 2 km context. |
| `mean_slope_2km` | float, degrees | Static mean slope in the same context. |
| `built_up_share` | float, 0-1 | CLC 2018 built/artificial share of cell mainland land; contextual only. |
| `official_icnf_hazard_code` | integer | Predominant valid official 25 m class code; `-1` means unmatched, never low hazard. |
| `official_icnf_hazard_class` | string | `very_low`, `low`, `medium`, `high`, `very_high`, or `unmatched`. |
| `icnf_valid_pixel_count` | integer | Valid official 25 m hazard pixels contributing to the cell summary. |
| `icnf_hazard_coverage_share` | float, 0-1 | Share of rasterized mainland-cell pixels with a valid official class. |
| `icnf_modal_class_share` | float, 0-1 | Share of valid official pixels belonging to the assigned predominant class. |
| `icnf_modal_tie` | boolean | Whether multiple official classes tied for the largest pixel count; exact ties select the higher class. |
| `icnf_source_version` | string | Registered official SRUP-CPIR 2020-2030 source/version label. This is an official structural-hazard reference, not a fire prediction. |
| `evidence_status` | string | `complete_descriptive_evidence` or `official_hazard_unmatched`. |

Lower historical exposure does not mean safe, zero recorded fire years does not mean zero wildfire risk, and this layer is not a property-level guarantee or purchase recommendation.

## Mandatory feature groups

A cell can receive a predictive score only when these groups are complete:

1. historical burned-area feature;
2. land-cover features;
3. terrain feature;
4. temperature, precipitation, and layer-1 soil-water features.

Missing mandatory data must not be interpreted as low exposure. The result must be marked as **insufficient evidence** or excluded with a documented reason.

## Data-quality rules

- Use one projected CRS for all area and distance calculations.
- Keep raw files unchanged.
- Never convert `NoData` automatically to zero.
- ERA5-Land containing-cell water-mask cases retain the 1 km analytical cell and use the validated static nearest-valid-land source-cell fallback. Never use zero, interpolation, a different product, or T+1 data.
- After applying the accepted coastal fallback, missing values are forbidden in all three canonical ERA5-Land predictors.
- Use only predictors available at predictor reference year `T`; never use observed outcome-year `T+1` information as a predictor.
- Record dataset versions and class definitions.
- Treat `built_up_share` only as a residential-relevance proxy until validated.
- Select the burned-area classification threshold after inspecting the target distribution.
- Test the fixed 2 km buffer against at least one reasonable alternative only in a separately documented future sensitivity study.
