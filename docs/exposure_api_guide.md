# Local exposure lookup API

This is a small, read-only REST API for the published **2026 comparative
wildfire-exposure** output. It also serves the repository's local browser map
at `http://127.0.0.1:8000`. Both are convenient presentation interfaces over
the same validated output; neither is a new model or changes validated data.

## What it answers

`GET /v1/exposure` accepts a WGS84 longitude and latitude and returns:

- the containing canonical mainland Portugal 1 km cell;
- its 2026 continuous estimated burned share and national comparative
  percentile;
- the nine recorded 2025 model inputs and their source periods, for a
  selected-cell explanation in the local viewer; and
- observed 2016-2025 historical recurrence context; and
- intersection-area-weighted context summaries within the requested 1 km,
  3 km, and 5 km radii; and
- the canonical cell identifiers with positive overlap in each metric context
  radius, so the local browser map can highlight the selected surrounding
  cells precisely.

The default response exposes the project estimate and historical recurrence
only. It **does not expose the ICNF structural-hazard raster or derived
hazard classes**, because that official comparison layer has distinct
licensing/use restrictions. It also does not geocode or retain addresses.

## Endpoint contract

All endpoints are read-only and return data from already published local
artefacts. They never train, refit, score a new year, or modify a dataset.

| Endpoint | Purpose | Successful response |
|---|---|---|
| `GET /` | Serves the local browser map. | HTML page. |
| `GET /v1/map/2026/cells.geojson` | Serves the reduced 2026 browser-map asset. | GeoJSON. |
| `GET /v1/exposure` | Looks up one coordinate and its requested context radii. | JSON object described below. |
| `GET /health` | Confirms that the required published local artefacts can be loaded. | `{"status":"ok","api_version":"0.1.0"}`. |
| `GET /docs` | Interactive FastAPI documentation. | HTML documentation. |
| `GET /openapi.json` | Live OpenAPI description from the running service. | OpenAPI JSON. |

### `GET /v1/exposure` request

| Query parameter | Type | Required | Rule |
|---|---|---:|---|
| `longitude` | decimal number | Yes | WGS84 (`EPSG:4326`) decimal degrees; API validation range −31 to 15. |
| `latitude` | decimal number | Yes | WGS84 (`EPSG:4326`) decimal degrees; API validation range 25 to 55. |
| `buffers_km` | comma-separated decimals | No | Positive, unique radii no larger than 10 km; default `1,3,5`. |

The coordinate must also fall inside the canonical mainland 1 km grid. A
valid WGS84 coordinate outside that grid returns `404`.

### `GET /v1/exposure` response

| Field | Type | Meaning |
|---|---|---|
| `api_version` | string | API version used to create the response. |
| `request_longitude`, `request_latitude` | number | Echoed WGS84 request coordinate. |
| `grid_x_epsg_3763`, `grid_y_epsg_3763` | number | Same point transformed to the project’s metric `EPSG:3763` CRS. |
| `containing_cell` | object | Published 2026 estimate and observed historical-context fields for the containing 1 km cell. |
| `model_inputs` | object | The nine recorded 2025 values jointly supplied to the final model, with source-period metadata. |
| `context_buffers` | array | One descriptive, intersection-area-weighted summary per requested radius. |
| `limitations` | array of strings | Scope and responsible-use statements returned with every lookup. |

`containing_cell` always contains `cell_id`, `forecast_year`,
`prediction_input_year`, `predicted_burned_share_next_year`,
`predicted_exposure_percentile`, `estimated_comparative_exposure_band`,
`historical_evidence_period`, `fire_years_history_10y_2km`, and
`historical_exposure_band`. The burned-share estimate is a continuous fraction
from 0 to 1; multiply by 100 for percentage display. The percentile is a
separate national rank from 0 to 1, not a second estimate.

`model_inputs` contains provenance fields
`historical_fire_start_year`, `historical_fire_end_year`,
`climate_reference_year`, `land_cover_reference_year`,
`land_cover_release_id`, and `terrain_release_id`, followed by these nine
model fields in their recorded order:

| Field | Unit / interpretation |
|---|---|
| `built_up_share` | 1 km mainland-land share classified as built/artificial land. |
| `forest_shrub_share_2km` | Forest/shrub share of mainland land in the outward 2 km context. |
| `mean_slope_2km` | Mean terrain slope, in degrees, in the 2 km context. |
| `fire_years_previous_10y_2km` | Distinct burned years in the strictly pre-predictor 10-year context window. |
| `warm_season_mean_2m_temperature_c` | June–September mean 2 m air temperature, °C. |
| `warm_season_total_precipitation_mm` | Day-weighted June–September precipitation total, mm. |
| `warm_season_mean_soil_water_layer1` | June–September mean shallow (layer-1) soil water, m³/m³. |
| `warm_season_max_monthly_2m_temperature_c` | Warmest June–September monthly mean 2 m air temperature, °C. |
| `warm_season_min_monthly_soil_water_layer1` | Driest June–September monthly mean shallow soil water, m³/m³. |

Each `context_buffers` item contains `radius_km`,
`intersecting_cell_count`, `intersected_grid_area_sq_km`,
`mean_predicted_burned_share_next_year`,
`mean_predicted_exposure_percentile`,
`higher_estimated_exposure_area_share`,
`mean_fire_years_history_10y_2km`, and `intersecting_cell_ids`. These are
surrounding-area summaries of overlapping 1 km cells; they are not a second
grid, additional model estimate, or property assessment.

### Errors

| Status | Meaning |
|---:|---|
| `404` | The coordinate is outside the canonical mainland Portugal 1 km grid. |
| `422` | A coordinate or `buffers_km` parameter is malformed or outside its accepted range. |
| `503` | Required published local outputs or the browser-map asset are unavailable or fail contract checks. |

## Preconditions

1. Create and activate the project Python environment and install
   `requirements.txt`.
2. Obtain the source data under the provider terms and run the documented
   reproduction workflow successfully. The API reads these derived outputs:

   - `data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg`
   - `data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg`

3. Validate the local API contract:

   ```text
   python scripts/validate_exposure_api.py
   ```
4. Build the reduced, browser-ready map derivative:

   ```text
   python scripts/build_web_map_assets.py --overwrite
   ```

   The derivative is `data/processed/web_map/estimated_comparative_wildfire_exposure_2026.geojson`.
   It contains only the fields needed to display and inspect the annual
   estimate. The GeoPackage remains the validated spatial publication.

## Start the service

Run this from the repository root:

```text
python scripts/run_exposure_api.py
```

The default host is `127.0.0.1`, so it is reachable only from the local
machine at `http://127.0.0.1:8000`. The local browser map is at that root URL;
it uses the local 2026 derivative as its overlay. Its optional online
backgrounds are OpenStreetMap Standard, OpenStreetMap Humanitarian, Esri World
Topographic terrain, and Esri World Imagery; users can also select no online
basemap. Interactive API documentation is available at
`http://127.0.0.1:8000/docs`; the machine-readable OpenAPI document is at
`http://127.0.0.1:8000/openapi.json`.

The checked-in API contract is also available at
[`docs/openapi/exposure_api.json`](openapi/exposure_api.json). Regenerate it
after an intentional endpoint/schema change with:

```text
python scripts/export_exposure_api_openapi.py
```

For a deliberately managed deployment host and port:

```text
python scripts/run_exposure_api.py --host 0.0.0.0 --port 8000
```

Do not expose the service publicly without authentication, rate limiting,
HTTPS, monitoring, a privacy notice, a data-licence review, and a basemap
provider suitable for production traffic. The OpenStreetMap public tile service
is appropriate only for modest interactive use under its current policy; do not
prefetch or package its tiles.

## Example request

```text
GET http://127.0.0.1:8000/v1/exposure?longitude=-8.40&latitude=40.21&buffers_km=1,3,5
```

`longitude` and `latitude` are decimal WGS84 coordinates (`EPSG:4326`).
`buffers_km` is optional, comma-separated, positive, unique values no larger
than 10 km; its default is `1,3,5`.

The response contains a continuous `predicted_burned_share_next_year`: the
estimated share of the 1 km cell land area that may burn in 2026. It is not a
probability. `predicted_exposure_percentile` is a comparative national rank,
calculated by ranking all same-year mainland cell estimates from low to high;
it is not the percentage expected to burn or a safety rating. A `404` response means the coordinate is outside the
canonical mainland grid; a `503` response means the required published local
outputs have not been built or failed their contract checks.

`model_inputs` records the nine values supplied jointly to the final model for
the containing cell, together with their source periods. They help a user
understand the context behind the displayed estimate; they do not identify
individual causes or convert the estimate into a property-level assessment.

## Address input and privacy

Address-to-coordinate conversion is intentionally not included. It requires a
separate geocoding provider, its own terms, consent/retention choices, and a
privacy assessment. A client may geocode an address through an approved
provider and send only the resulting coordinates to this local API. The API
does not write application-level request logs or store coordinates; a deployed
web server/operator must still configure access logs and privacy controls.

## Scope and responsible use

This API is a broad-area comparative screening interface. It must not be used
as a property-level forecast, safety guarantee, insurance quote, or
buy/do-not-buy recommendation. It does not prove the future performance of the
target-free 2026 estimate; that requires the future observed ICNF outcome.

For source attribution, redistribution, and commercialisation caveats, read
[data licensing and attribution](data_licensing_and_attribution.md) and the
working [commercialisation legal notes](commercialisation_legal_working_notes.md).
