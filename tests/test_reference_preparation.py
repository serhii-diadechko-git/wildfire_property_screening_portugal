"""Regression checks for reproducible CAOP reference derivatives."""

import unittest

import pyogrio
import shapely

from src.geospatial_utils import BOUNDARY_PATH, GRID_PATH
from src.reference_preparation import (
    CANONICAL_GRID_LAYER,
    EXPECTED_CANONICAL_GRID_CELLS,
    _canonical_grid_geometries,
)


class ReferencePreparationTests(unittest.TestCase):
    def test_caop_driven_grid_recipe_matches_the_published_grid(self) -> None:
        """A clean checkout must recreate the same stable geometry lookup."""
        boundary = pyogrio.read_dataframe(BOUNDARY_PATH, columns=[]).geometry.iloc[0]
        rebuilt = _canonical_grid_geometries(boundary)
        published = pyogrio.read_dataframe(GRID_PATH, layer=CANONICAL_GRID_LAYER, columns=["cell_id"])

        self.assertEqual(len(rebuilt), EXPECTED_CANONICAL_GRID_CELLS)
        self.assertEqual(len(published), EXPECTED_CANONICAL_GRID_CELLS)
        self.assertTrue(published.cell_id.is_unique)
        for index in (0, 1, len(rebuilt) // 2, len(rebuilt) - 1):
            self.assertTrue(shapely.equals(rebuilt[index], published.geometry.iloc[index]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
