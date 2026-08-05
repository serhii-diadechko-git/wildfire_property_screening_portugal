"""Offline tests for collection provenance and pilot configuration."""

from pathlib import Path
import unittest

from src.collection_validation import (
    validate_era5_land_pilot_request,
    validate_era5_land_request,
    validate_icnf_archive,
    validate_zip_archive,
)
from src.config import PILOT_2023_TO_2024
from src.source_registry import (
    CAOP_2025,
    ICNF_2000_2008_COMBINED,
    ICNF_2009,
    ICNF_2010,
    ICNF_2011,
    ICNF_2023,
    ICNF_2024,
    ICNF_2025,
    PILOT_ICNF_ARCHIVES,
    PILOT_ICNF_HISTORY,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CollectionValidationTests(unittest.TestCase):
    def test_early_icnf_archives_match_registered_facts(self) -> None:
        combined = validate_icnf_archive(
            ICNF_2000_2008_COMBINED, PROJECT_ROOT, expected_year=tuple(range(2000, 2009))
        )
        self.assertEqual(combined["year_values"], tuple(range(2000, 2009)))
        self.assertEqual(combined["feature_count"], 10981)
        for year, record, count, invalid in (
            (2009, ICNF_2009, 1441, 22),
            (2010, ICNF_2010, 2513, 40),
            (2011, ICNF_2011, 3686, 33),
        ):
            with self.subTest(year=year):
                result = validate_icnf_archive(record, PROJECT_ROOT, expected_year=year)
                self.assertEqual(result["feature_count"], count)
                self.assertEqual(result["invalid_geometry_count"], invalid)
    def test_pilot_era5_request_is_t_only_and_jjas(self) -> None:
        result = validate_era5_land_pilot_request()
        self.assertEqual(result["predictor_year"], 2023)
        self.assertEqual(result["outcome_year"], 2024)
        self.assertEqual(result["season_months"], (6, 7, 8, 9))
        self.assertEqual(result["documented_temporal_coverage"], "1950-present")

    def test_era5_coverage_includes_every_approved_predictor_year(self) -> None:
        for year in range(2015, 2025):
            self.assertEqual(validate_era5_land_request(year)["predictor_year"], year)

    def test_registered_archives_are_unchanged_and_valid(self) -> None:
        caop = validate_zip_archive(CAOP_2025, PROJECT_ROOT)
        icnf = validate_icnf_archive(ICNF_2024, PROJECT_ROOT, expected_year=2024, expected_feature_count=1558)
        self.assertEqual(caop["zip_integrity"], "passed")
        self.assertEqual(icnf["feature_count"], 1558)
        self.assertTrue(icnf["geometries_valid_and_non_empty"])

    def test_pilot_icnf_archives_match_registered_facts_without_predictor_year(self) -> None:
        expected_history = tuple(range(2013, 2023))
        self.assertEqual(tuple(int(record.filename.removeprefix("ardida_").removesuffix(".zip")) for record in PILOT_ICNF_HISTORY), expected_history)
        self.assertEqual(tuple(PILOT_ICNF_ARCHIVES), expected_history + (2024,))
        self.assertNotIn(PILOT_2023_TO_2024.predictor_year, PILOT_ICNF_ARCHIVES)

        for year in expected_history:
            result = validate_icnf_archive(PILOT_ICNF_ARCHIVES[year], PROJECT_ROOT, expected_year=year)
            self.assertEqual(result["year"], year)
            self.assertEqual(result["non_empty_geometry_count"], result["feature_count"])
            self.assertGreater(result["invalid_geometry_count"], 0)

    def test_final_test_icnf_archives_match_registered_facts(self) -> None:
        for year, record, expected_count, expected_invalid in (
            (2023, ICNF_2023, 1736, 11),
            (2025, ICNF_2025, 2084, 2),
        ):
            result = validate_icnf_archive(record, PROJECT_ROOT, expected_year=year)
            self.assertEqual(result["feature_count"], expected_count)
            self.assertEqual(result["non_empty_geometry_count"], expected_count)
            self.assertEqual(result["invalid_geometry_count"], expected_invalid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
