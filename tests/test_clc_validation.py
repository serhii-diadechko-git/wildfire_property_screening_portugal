"""Read-only test for the existing CLC 2018 mainland vector derivative."""

from pathlib import Path
import unittest

from src.clc_validation import validate_clc_2018_mainland, validate_registered_prepared_clc
from src.source_registry import CLC_PREPARED_PORTUGAL_LAYERS


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

    def test_canonical_prepared_portugal_layers(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        expected_counts = {2006: 51555, 2012: 54041, 2018: 54191}
        expected_fields = {2006: "Code_06", 2012: "Code_12", 2018: "Code_18"}
        for year, record in CLC_PREPARED_PORTUGAL_LAYERS.items():
            with self.subTest(reference_year=year):
                result = validate_registered_prepared_clc(project_root, record)
                self.assertTrue(result["ready"])
                self.assertEqual(result["feature_count"], expected_counts[year])
                self.assertEqual(result["class_code_field"], expected_fields[year])
                self.assertEqual(result["crs"], "EPSG:3035")
                self.assertEqual(result["observed_code_count"], 42)
                self.assertEqual(result["null_geometry_count"], 0)
                self.assertEqual(result["empty_geometry_count"], 0)
                self.assertEqual(result["invalid_geometry_count"], 0)
                self.assertEqual(result["missing_mainland_area_share"], 0.0)
                self.assertEqual(result["outside_mainland_area_share"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
