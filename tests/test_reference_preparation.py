"""Regression checks for reproducible CAOP reference derivatives."""

import unittest

import pyogrio

from src.geospatial_utils import BOUNDARY_PATH, GRID_PATH
from src.reference_preparation import (
    CANONICAL_GRID_LAYER,
    EXPECTED_CANONICAL_GRID_CELLS,
)


class ReferencePreparationTests(unittest.TestCase):
    def test_published_grid_has_the_canonical_geometry_contract(self) -> None:
        """Verify the published lookup without regenerating 89,112 polygons in a test."""
        boundary_info = pyogrio.read_info(BOUNDARY_PATH)
        published = pyogrio.read_dataframe(GRID_PATH, layer=CANONICAL_GRID_LAYER, columns=["cell_id"])

        self.assertEqual(boundary_info["features"], 1)
        self.assertEqual(len(published), EXPECTED_CANONICAL_GRID_CELLS)
        self.assertTrue(published.cell_id.is_unique)
        self.assertEqual(str(published.crs), "EPSG:3763")


if __name__ == "__main__":
    unittest.main(verbosity=2)
