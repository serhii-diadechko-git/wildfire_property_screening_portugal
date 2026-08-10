"""Focused contract tests for the public read-only lookup API."""

from __future__ import annotations

import unittest

import geopandas as gpd
from fastapi.testclient import TestClient
from pyproj import Transformer
from shapely.geometry import Polygon

from src.exposure_api import ExposureStore, create_app


class ExposureApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        geometry = [
            Polygon([(0, 0), (1_000, 0), (1_000, 1_000), (0, 1_000)]),
            Polygon([(1_000, 0), (2_000, 0), (2_000, 1_000), (1_000, 1_000)]),
        ]
        scores = gpd.GeoDataFrame({
            "cell_id": ["A", "B"], "forecast_year": [2026, 2026], "prediction_input_year": [2025, 2025],
            "predicted_burned_share_next_year": [0.01, 0.04], "predicted_exposure_percentile": [0.25, 0.90],
        }, geometry=geometry, crs="EPSG:3763")
        historical = gpd.GeoDataFrame({
            "cell_id": ["A", "B"], "history_start_year": [2016, 2016], "history_end_year": [2025, 2025],
            "fire_years_history_10y_2km": [1, 5], "historical_exposure_band": ["Lower", "Higher"],
        }, geometry=geometry, crs="EPSG:3763")
        cls.client = TestClient(create_app(store=ExposureStore.from_frames(scores, historical)))
        cls.transformer = Transformer.from_crs("EPSG:3763", "EPSG:4326", always_xy=True)

    def test_lookup_returns_containing_cell_and_default_context(self) -> None:
        longitude, latitude = self.transformer.transform(500, 500)
        response = self.client.get("/v1/exposure", params={"longitude": longitude, "latitude": latitude})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["containing_cell"]["cell_id"], "A")
        self.assertEqual([item["radius_km"] for item in payload["context_buffers"]], [1.0, 3.0, 5.0])
        self.assertEqual(payload["containing_cell"]["estimated_comparative_exposure_band"], "Lower estimated comparative exposure percentile (0-50%)")

    def test_lookup_rejects_invalid_or_outside_locations(self) -> None:
        longitude, latitude = self.transformer.transform(10_000, 10_000)
        self.assertEqual(self.client.get("/v1/exposure", params={"longitude": longitude, "latitude": latitude}).status_code, 404)
        longitude, latitude = self.transformer.transform(500, 500)
        response = self.client.get("/v1/exposure", params={"longitude": longitude, "latitude": latitude, "buffers_km": "1,1"})
        self.assertEqual(response.status_code, 422)

    def test_openapi_and_health_are_published(self) -> None:
        self.assertEqual(self.client.get("/health").status_code, 200)
        schema = self.client.get("/openapi.json").json()
        self.assertIn("/v1/exposure", schema["paths"])
        self.assertEqual(schema["info"]["version"], "0.1.0")


if __name__ == "__main__":
    unittest.main()
