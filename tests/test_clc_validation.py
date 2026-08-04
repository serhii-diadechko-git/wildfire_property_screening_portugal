"""Read-only test for the existing CLC 2018 mainland vector derivative."""

from pathlib import Path
import unittest

from src.clc_validation import validate_clc_2018_mainland


class ClcValidationTests(unittest.TestCase):
    def test_existing_mainland_vector_extract(self) -> None:
        result = validate_clc_2018_mainland(Path(__file__).resolve().parents[1])
        self.assertEqual(result["crs"], "EPSG:3035")
        self.assertEqual(result["layer"], "clc_2018_mainland")
        self.assertEqual(result["feature_count"], 54191)
        self.assertEqual(result["unique_valid_clc_codes"], 42)
        self.assertEqual(result["null_geometry_count"], 0)
        self.assertEqual(result["empty_geometry_count"], 0)
        self.assertEqual(result["invalid_geometry_count"], 0)
        self.assertFalse(result["raster_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
