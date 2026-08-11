# Local 2026 web map

This directory contains the small static browser client for the validated 2026
comparative wildfire-exposure layer. It is served by the existing local
FastAPI service; it is not a second modelling workflow.

## Build and open

After the documented reproduction workflow has created the 2026 GeoPackage:

```text
python scripts/build_web_map_assets.py --overwrite
python scripts/run_exposure_api.py
```

Open `http://127.0.0.1:8000` in a browser. The local page loads its derived
2026 GeoJSON from `data/processed/web_map/` and uses the API only for click
context summaries. It does not retain coordinates, accept addresses, train a
model, or expose the ICNF structural-hazard comparison layer.

## Map components

- **2026 comparative estimate:** 89,112 1 km cells. Each cell has a continuous
  estimated burned share and a separate national rank of that estimate. The
  default **three-group** view is lower (0-50th), intermediate (>50-80th), and
  higher (>80-100th) national rank. The detailed view uses mostly
  15-percentile-point intervals (0-15, >15-30, >30-45, >45-60, >60-75,
  >75-90, and >90-100) for finer spatial comparison.
  Switching the display changes colours and the legend together, but never
  changes the underlying estimated burned-share values. Both are relative
  comparison views, not burned-share percentages, physical risk thresholds,
  safety categories, or Capture@20% validation results.
- **Selected-cell card:** clicking a cell fills a persistent map card that
  emphasises the selected 1 km cell's own estimated burned share. Separate
  1/3/5 km rows show area-weighted averages across all cells intersecting each
  surrounding circle; they are context summaries, not replacement values for
  the selected cell. The selected cell is yellow, cells within 3 km are cyan,
  and the outer 3-5 km context cells are blue. The colours are a temporary
  selection overlay; they do not alter the exposure bands. The card receives
  its lookup and context data from same-origin `GET /v1/exposure`; the browser
  does not calculate or rescore an estimate.
- **Basemap selector:** OpenStreetMap Standard, OpenStreetMap Humanitarian,
  Esri World Topographic terrain, Esri World Imagery satellite, or no online
  basemap. Tiles are loaded only for the view currently used in the browser.
  The map shows each provider's visible attribution. This local viewer does
  not prefetch or package tiles.
- **Opacity control:** changes only the transparency of the 2026 exposure
  overlay so the selected background map is easier to inspect; it does not
  change any estimated value or band.
- **Scale bar:** shows the current metric map scale and updates automatically
  when the user zooms.
- **Measurement tools:** the ruler measures multi-segment distance and the
  polygon tool measures area. Click vertices and double-click to finish; the
  measured value remains labelled on the map until the clear-measurements
  action is used. Both tools use a cyan/teal overlay deliberately distinct
  from the beige/orange/red exposure palette. Clearing measurements restores
  normal cell selection immediately. These measurements are map geometry aids,
  not model outputs.
- **Inputs used:** opens the nine recorded predictor values for the selected
  cell. Each information icon opens a nearby, independent plain-language
  definition; the displayed values remain visible underneath.

## Local endpoints used by the map

The browser client is deliberately thin and uses only two same-origin,
read-only endpoints:

| Endpoint | Purpose | When called |
|---|---|---|
| `GET /v1/map/2026/cells.geojson` | Reduced 2026 cell geometry with presentation fields. | Once when the map opens. |
| `GET /v1/exposure` | Containing-cell estimate, nine recorded inputs, and requested surrounding-context summaries. | Each time a user clicks a cell. |

The API contract, request parameters, output fields, and error behavior are
defined in the [local exposure API guide](../docs/exposure_api_guide.md) and
the checked-in [OpenAPI schema](../docs/openapi/exposure_api.json).

The browser map is useful for accessible presentation and broad-area research.
QGIS remains the technical GIS review interface. See the repository
[README](../README.md) and the [local exposure API guide](../docs/exposure_api_guide.md)
for scope, source, and limitation details.

The supplied public tile endpoints are for modest local interactive viewing.
They are not a production basemap arrangement. Any hosted or commercial map
must use a provider/plan that permits its traffic and preserve the required
attribution.
