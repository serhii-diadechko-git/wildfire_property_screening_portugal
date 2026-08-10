# Local exposure lookup API

This is a small, read-only REST API for the published **2026 comparative
wildfire-exposure** output. It is a convenient interface for a website,
prototype, or local GIS-adjacent application; it is not a new model and does
not change any validated data.

## What it answers

`GET /v1/exposure` accepts a WGS84 longitude and latitude and returns:

- the containing canonical mainland Portugal 1 km cell;
- its 2026 continuous estimated burned share and national comparative
  percentile;
- observed 2016-2025 historical recurrence context; and
- intersection-area-weighted context summaries within the requested 1 km,
  3 km, and 5 km radii.

The default response exposes the project estimate and historical recurrence
only. It **does not expose the ICNF structural-hazard raster or derived
hazard classes**, because that official comparison layer has distinct
licensing/use restrictions. It also does not geocode or retain addresses.

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

## Start the service

Run this from the repository root:

```text
python scripts/run_exposure_api.py
```

The default host is `127.0.0.1`, so it is reachable only from the local
machine at `http://127.0.0.1:8000`. Interactive documentation is available at
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
HTTPS, monitoring, a privacy notice, and a data-licence review.

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
not a safety rating. A `404` response means the coordinate is outside the
canonical mainland grid; a `503` response means the required published local
outputs have not been built or failed their contract checks.

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
