"""Read-only test for the downloaded ERA5-Land pilot GRIB."""

from pathlib import Path
import unittest

from src.era5_land_validation import (
    validate_era5_land_grib_record,
    validate_era5_land_pilot_grib,
    validate_extended_training_era5_grib,
)
from src.source_registry import (
    ERA5_LAND_EXTENDED_TRAINING_ARCHIVES,
    ERA5_LAND_2022_CORRECTED_PRECIPITATION,
    ERA5_LAND_2022_JJAS,
    ERA5_LAND_2023_CORRECTED_PRECIPITATION,
    ERA5_LAND_2024_JJAS,
)


class Era5LandValidationTests(unittest.TestCase):
    def test_extended_training_contract_matches_existing_2015_layout(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        path = project_root / "data/raw/climate/era5_land/era5_land_monthly_jjas_2015_mainland_portugal.grib"
        result = validate_extended_training_era5_grib(path, 2010)
        self.assertEqual(result["grid_shape_time_latitude_longitude"], (4, 55, 37))
        self.assertEqual(tuple(result["grib_metadata"]), ("2t", "tp", "swvl1"))
        self.assertEqual(result["water_mask_counts"], {"2t": 1928, "tp": 1928, "swvl1": 1928})

    def test_extended_training_raw_files_match_registered_contract(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        self.assertEqual(set(ERA5_LAND_EXTENDED_TRAINING_ARCHIVES), set(range(2010, 2015)))
        for year, record in ERA5_LAND_EXTENDED_TRAINING_ARCHIVES.items():
            with self.subTest(year=year):
                result = validate_era5_land_grib_record(record, project_root)
                self.assertEqual(result["year"], year)
                self.assertEqual(result["precipitation_status"], "validated")

    def test_downloaded_pilot_grib_matches_approved_request(self) -> None:
        result = validate_era5_land_pilot_grib(Path(__file__).resolve().parents[1])
        self.assertEqual(result["dataset_id"], "reanalysis-era5-land-monthly-means")
        self.assertEqual(result["grid_shape_time_latitude_longitude"], (4, 55, 37))
        self.assertEqual(tuple(result["variables"]), (
            "2m_temperature", "total_precipitation", "volumetric_soil_water_layer_1",
        ))

    def test_full_scope_missing_year_retrievals_match_registered_contract(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        result_2022 = validate_era5_land_grib_record(ERA5_LAND_2022_JJAS, project_root)
        result_2024 = validate_era5_land_grib_record(ERA5_LAND_2024_JJAS, project_root)
        self.assertEqual(result_2022["grid_shape_time_latitude_longitude"], (4, 55, 37))
        self.assertEqual(result_2024["grid_shape_time_latitude_longitude"], (4, 55, 37))
        self.assertEqual(result_2022["precipitation_status"], "blocked-known-upstream-issue")
        self.assertEqual(result_2024["precipitation_status"], "validated-post-fix")
        self.assertEqual(result_2022["grib_metadata"]["tp"]["step_type"], "avgad")
        self.assertEqual(result_2024["grib_metadata"]["tp"]["step_type"], "avgas")

    def test_corrected_precipitation_files_match_official_workaround_contract(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        for record in (
            ERA5_LAND_2022_CORRECTED_PRECIPITATION,
            ERA5_LAND_2023_CORRECTED_PRECIPITATION,
        ):
            with self.subTest(year=record.year):
                result = validate_era5_land_grib_record(record, project_root)
                self.assertEqual(tuple(result["variables"]), ("tp",))
                self.assertEqual(result["grib_metadata"]["tp"]["unit"], "m")
                self.assertEqual(result["grib_metadata"]["tp"]["step_type"], "avgas")
                self.assertEqual(result["grib_metadata"]["tp"]["step_range"], "23-24")
                self.assertEqual(result["grib_metadata"]["tp"]["stream"], "mnth")
                self.assertEqual(result["precipitation_status"], "validated-official-workaround")


if __name__ == "__main__":
    unittest.main(verbosity=2)
