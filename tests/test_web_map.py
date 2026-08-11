"""Focused contract tests for the local browser-map derivative."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import geopandas as gpd
from fastapi.testclient import TestClient
from shapely.geometry import Polygon

from src.exposure_api import ExposureStore, create_app
from src.web_map import build_web_map_assets, public_web_map_frame


def _scores() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({
        "cell_id": ["A", "B", "C"],
        "prediction_input_year": [2025, 2025, 2025],
        "forecast_year": [2026, 2026, 2026],
        "climate_assignment_method": ["containing"] * 3,
        "predicted_burned_share_next_year": [0.001, 0.02, 0.09],
        "predicted_exposure_percentile": [0.50, 0.51, 0.81],
        "model_sha256": ["A"] * 3,
        "score_status": ["scored_comparative_estimate"] * 3,
    }, geometry=[
        Polygon([(0, 0), (1_000, 0), (1_000, 1_000), (0, 1_000)]),
        Polygon([(1_000, 0), (2_000, 0), (2_000, 1_000), (1_000, 1_000)]),
        Polygon([(2_000, 0), (3_000, 0), (3_000, 1_000), (2_000, 1_000)]),
    ], crs="EPSG:3763")


class WebMapTests(unittest.TestCase):
    def test_public_frame_has_only_required_presentation_data_and_stable_bands(self) -> None:
        frame = public_web_map_frame(_scores())
        self.assertEqual(str(frame.crs), "EPSG:4326")
        self.assertEqual(frame["exposure_band_code"].tolist(), ["lower", "intermediate", "higher"])
        self.assertNotIn("climate_assignment_method", frame.columns)
        self.assertNotIn("geometry", frame.drop(columns="geometry").columns)

    def test_asset_build_is_reusable_and_writes_valid_geojson(self) -> None:
        root = Path(self._testMethodName)
        root.mkdir(exist_ok=True)
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        source = root / "estimate.gpkg"
        output = root / "map.geojson"
        metadata = root / "map.metadata.json"
        # The export's reader is injected here so this contract test avoids
        # GDAL/SQLite writes in locked-down Windows temporary directories.
        source.write_bytes(b"validated source stand-in")
        first = build_web_map_assets(source, output, metadata, reader=lambda *_args, **_kwargs: _scores())
        second = build_web_map_assets(source, output, metadata, reader=lambda *_args, **_kwargs: _scores())
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(first["status"], "published")
        self.assertEqual(second["status"], "reused")
        self.assertEqual(payload["type"], "FeatureCollection")
        self.assertEqual(len(payload["features"]), 3)
        self.assertEqual(set(payload["features"][0]["properties"]), {
            "cell_id", "prediction_input_year", "forecast_year", "predicted_burned_share_next_year",
            "predicted_exposure_percentile",
            "exposure_band_code", "estimated_comparative_exposure_band",
        })

    def test_root_serves_the_local_browser_viewer(self) -> None:
        scores = _scores().iloc[:2].copy()
        historical = scores.loc[:, ["cell_id", "geometry"]].copy()
        historical["history_start_year"] = 2016
        historical["history_end_year"] = 2025
        historical["fire_years_history_10y_2km"] = 1
        historical["historical_exposure_band"] = "Lower"
        response = TestClient(create_app(store=ExposureStore.from_frames(scores, historical))).get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("2026 estimated comparative wildfire exposure", response.text)

    def test_browser_client_has_documented_basemap_choices_and_full_view_shell(self) -> None:
        root = Path(__file__).resolve().parents[1]
        client = (root / "web" / "app.js").read_text(encoding="utf-8")
        page = (root / "web" / "index.html").read_text(encoding="utf-8")
        stylesheet = (root / "web" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("OpenStreetMap Standard", client)
        self.assertIn("OpenStreetMap Humanitarian", client)
        self.assertIn("Terrain (Esri World Topographic)", client)
        self.assertIn("Satellite imagery (Esri World Imagery)", client)
        self.assertIn("No online basemap", client)
        self.assertIn("opacity-control", client)
        self.assertIn("opacity-heading", client)
        self.assertIn("These radius areas", client)
        self.assertIn("applyHighlights", client)
        self.assertIn("intersecting_cell_ids", client)
        self.assertIn("fifteen: {", client)
        self.assertIn("15 percentile points wide", client)
        self.assertIn("changeClassification", client)
        self.assertIn("Detail: 15-point rank intervals", page)
        self.assertIn("National relative rank", client)
        self.assertIn("Two different percentages", client)
        self.assertIn("selected-cell-primary", client)
        self.assertIn("Nearby context averages", client)
        self.assertIn("contextRow", client)
        self.assertIn("inputDetailsHtml", client)
        self.assertIn("showInputDetails", client)
        self.assertIn("input-details-dialog", page)
        self.assertIn("Inputs used", page)
        self.assertIn("selection-toolbar", stylesheet)
        self.assertIn("input-details-dialog", stylesheet)
        self.assertIn("L.control.scale", client)
        self.assertIn("feature-info", client)
        self.assertIn("feature-info", stylesheet)
        self.assertIn("feature-help-popover", page)
        self.assertIn("showFeatureHelp", client)
        self.assertIn("overflow-x: hidden", stylesheet)
        self.assertIn("const highlightTiers = new Map()", client)
        self.assertIn("layer.setStyle(style(layer.feature))", client)
        self.assertNotIn("L.geoJSON(sourceLayer.feature", client)
        self.assertIn('selectionTitle.textContent = "Cell details"', client)
        self.assertIn("min-height: 100vh", stylesheet)
        self.assertIn("highlight-three", stylesheet)
        self.assertIn("--map-widget-width: 290px", stylesheet)
        self.assertIn("width: var(--map-widget-width)", stylesheet)


if __name__ == "__main__":
    unittest.main()
