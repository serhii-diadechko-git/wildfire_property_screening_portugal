# Data Dictionary - First Version

## Analytical unit

One analytical record represents one **1 km grid cell and one predictor reference year `T`**.

Predictors available for year `T` are used to estimate the observed wildfire outcome in year `T+1`.

## Spatial definitions

- **Grid resolution:** 1 km x 1 km.
- **Initial context buffer:** 2 km around the 1 km cell.
- **Purpose of the buffer:** measure nearby vegetation, terrain, and previous fire activity that may affect the residential location.

The 2 km buffer is not a second grid resolution. It is an initial modelling parameter that will be checked through sensitivity analysis.

## Temporal scope and split

The approved predictor-reference panel is `T = 2015-2024`: training years `2015-2019`, validation years `2020-2021`, and final temporal test years `2022-2024`. The required ICNF annual burned-area archive range is `2005-2025` inclusive.

There is no temporal gap between historical-fire information and predictor year `T`. `fire_years_previous_10y_2km` uses only the inclusive pre-`T` window `T-10` through `T-1`, which is information genuinely available at prediction time and is not leakage. ICNF burned areas are never a same-year `T` predictor.

CLC is broad, release-aware land-cover context rather than annual parcel-level land cover. ERA5-Land is coarse regional context, not 1 km weather: its JJAS values from `T` only are assigned by containing ERA5-Land cell, without interpolation or downscaling. This is a retrospective reproducible evaluation; it does not claim an exact real-time historical reconstruction.

## Technical identifiers

These fields are required to store and join the analytical records. They are not predictive features.

| Column | Type | Meaning | Source / derivation |
|---|---|---|---|
| `cell_id` | string | Stable identifier for one 1 km grid cell. | Generated analytical grid |
| `observation_year` | integer | Year associated with the predictor data. | Derived |
| `geometry` | geometry | Polygon geometry of the 1 km grid cell. | Generated analytical grid |

## MVP analytical columns

This table matches the minimum schema in the completed Capstone Kickoff Workbook.

| Column | Type | Unit / values | Description | Source / derivation |
|---|---|---|---|---|
| `cell_year_id` | string | `<cell_id>_<year>` | Unique key for one 1 km cell and observation year. | Generated from `cell_id` and `observation_year` |
| `built_up_share` | float | 0-1 | Share of the 1 km cell classified as built or artificial land. It is an initial residential-relevance proxy, not proof that the cell is residential. | Release-aware Copernicus CLC broad classes |
| `forest_shrub_share_2km` | float | 0-1 | Combined forest and shrubland share within the initial 2 km buffer around the cell. | Release-aware Copernicus CLC broad classes |
| `mean_slope_2km` | float | degrees | Mean terrain slope within the same 2 km buffer. | Derived from Copernicus DEM GLO-30 |
| `fire_years_previous_10y_2km` | integer | count | Number of years from `T-10` through `T-1` inclusive in which the 2 km buffer intersected an ICNF burned-area polygon. This is strictly pre-`T` information. | ICNF burned-area intersections |
| `warm_season_mean_2m_temperature_c` | float | degrees Celsius | Mean ERA5-Land 2 m temperature for June–September (`JJAS`) in predictor year `T`. | ERA5-Land `2m_temperature` |
| `warm_season_total_precipitation_mm` | float | millimetres | Total ERA5-Land precipitation for `JJAS` in predictor year `T`. | ERA5-Land `total_precipitation` |
| `warm_season_mean_soil_water_layer1` | float | m³/m³ | Mean ERA5-Land volumetric soil water in layer 1 for `JJAS` in predictor year `T`. | ERA5-Land `volumetric_soil_water_layer_1` |
| `burned_share_next_year` | float | 0-1 | Share of the 1 km cell intersected by burned-area polygons in observed outcome year `T+1`. This is the main continuous target. | ICNF burned-area intersections |

## Derived classification target

| Column | Type | Meaning |
|---|---|---|
| `burned_next_year` | boolean | Classification target for observed outcome year `T+1`, derived later from `burned_share_next_year` using a documented threshold selected after continuous-target-distribution analysis. |

## Model and decision outputs

These fields are produced after modelling. They are not input features.

| Column | Type | Meaning |
|---|---|---|
| `predicted_wildfire_probability` | float, 0-1 | Predicted relative probability for the target year. |
| `structural_exposure_score` | float or category | Exposure estimate based mainly on slower-changing features and historical fire activity. Final calculation is defined only after model validation. |
| `annual_outlook_score` | float or category | Updated result using the latest available annual inputs. Final calculation is defined only after model validation. |
| `score_stability` | float or category | Stability of the result across test years and reasonable model variants. |
| `uncertainty_flag` | category | Normal, caution, or insufficient evidence. |
| `recommendation_category` | category | Stronger shortlist candidate, candidate with caution, higher-exposure area, or insufficient evidence. |

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
- Use only predictors available at predictor reference year `T`; never use observed outcome-year `T+1` information as a predictor.
- Record dataset versions and class definitions.
- Treat `built_up_share` only as a residential-relevance proxy until validated.
- Select the burned-area classification threshold after inspecting the target distribution.
- Test the initial 2 km buffer against at least one reasonable alternative if time and processing capacity allow.
