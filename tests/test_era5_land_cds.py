"""Tests that make no CDS request and require no CDS credentials."""

from pathlib import Path
import unittest

from src.era5_land_cds import build_pilot_request, dry_run


class Era5LandCdsTests(unittest.TestCase):
    def test_approved_pilot_request_is_small_and_t_only(self) -> None:
        request = build_pilot_request()
        self.assertEqual(request["year"], ["2023"])
        self.assertEqual(request["month"], ["06", "07", "08", "09"])
        self.assertEqual(request["variable"], [
            "2m_temperature",
            "total_precipitation",
            "volumetric_soil_water_layer_1",
        ])
        self.assertEqual(request["data_format"], "grib")
        self.assertEqual(request["area"], [42.2, -9.6, 36.8, -6.0])

    def test_dry_run_does_not_call_network_or_read_credentials(self) -> None:
        result = dry_run(Path(__file__).resolve().parents[1])
        self.assertFalse(result["network_called"])
        self.assertFalse(result["credentials_read"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
