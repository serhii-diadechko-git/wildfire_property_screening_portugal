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
  higher (>80-100th) national rank. The **five-group** view uses equal 20-point
  national-rank ranges for more spatial detail.
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
  selection overlay; they do not alter the exposure bands.
- **Basemap selector:** OpenStreetMap Standard, OpenStreetMap Humanitarian,
  Esri World Topographic terrain, Esri World Imagery satellite, or no online
  basemap. Tiles are loaded only for the view currently used in the browser.
  The map shows each provider's visible attribution. This local viewer does
  not prefetch or package tiles.
- **Opacity control:** changes only the transparency of the 2026 exposure
  overlay so the selected background map is easier to inspect; it does not
  change any estimated value or band.

The browser map is useful for accessible presentation and broad-area research.
QGIS remains the technical GIS review interface. See the repository
[README](../README.md) and the [local exposure API guide](../docs/exposure_api_guide.md)
for scope, source, and limitation details.

The supplied public tile endpoints are for modest local interactive viewing.
They are not a production basemap arrangement. Any hosted or commercial map
must use a provider/plan that permits its traffic and preserve the required
attribution.
