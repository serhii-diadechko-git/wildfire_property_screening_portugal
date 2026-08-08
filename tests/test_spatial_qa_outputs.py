"""Verify the generated GeoPackages referenced by the tracked QGIS projects."""

from __future__ import annotations

import unittest

import pyogrio

from src.era5_coastal_fallback import (
    QA_GPKG_PATH,
    QA_LAYER,
    SNAPSHOT_GPKG_PATH,
    SNAPSHOT_LAYER,
)


class SpatialQaOutputTests(unittest.TestCase):
    def test_qgis_referenced_spatial_qa_layers_are_present_and_valid(self) -> None:
        qa = pyogrio.read_info(QA_GPKG_PATH, layer=QA_LAYER)
        snapshot = pyogrio.read_info(SNAPSHOT_GPKG_PATH, layer=SNAPSHOT_LAYER)
        self.assertEqual(qa["features"], 1_506)
        self.assertEqual(snapshot["features"], 89_112)
        self.assertEqual(str(qa["crs"]), "EPSG:3763")
        self.assertEqual(str(snapshot["crs"]), "EPSG:3763")


if __name__ == "__main__":
    unittest.main(verbosity=2)
