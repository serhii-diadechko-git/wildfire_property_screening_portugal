"""Read-only test for the downloaded ERA5-Land pilot GRIB."""

from pathlib import Path
import unittest

from src.era5_land_validation import validate_era5_land_pilot_grib


class Era5LandValidationTests(unittest.TestCase):
    def test_downloaded_pilot_grib_matches_approved_request(self) -> None:
        result = validate_era5_land_pilot_grib(Path(__file__).resolve().parents[1])
        self.assertEqual(result["dataset_id"], "reanalysis-era5-land-monthly-means")
        self.assertEqual(result["grid_shape_time_latitude_longitude"], (4, 55, 37))
        self.assertEqual(tuple(result["variables"]), (
            "2m_temperature", "total_precipitation", "volumetric_soil_water_layer_1",
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
