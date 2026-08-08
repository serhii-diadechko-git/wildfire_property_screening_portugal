"""Focused validation tests for the assembled canonical national panel."""

import json
import unittest

import pyarrow.parquet as pq

from src.feature_contract import TABLE_COLUMNS
from src.national_panel import (
    BUILD_METRICS_PATH,
    NATIONAL_PANEL_PATH,
    OBSERVATION_YEARS,
    VALIDATION_METRICS_PATH,
    VALIDATION_REPORT_PATH,
    load_grid_catalog,
)


class NationalPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not NATIONAL_PANEL_PATH.exists():
            raise unittest.SkipTest("Assembled national panel is not present")
        cls.parquet = pq.ParquetFile(NATIONAL_PANEL_PATH)
        cls.catalog = load_grid_catalog()

    def test_identity_schema_and_row_groups(self) -> None:
        self.assertEqual(self.catalog["cell_count"], 89_112)
        self.assertEqual(self.parquet.metadata.num_rows, 891_120)
        self.assertEqual(self.parquet.num_row_groups, len(OBSERVATION_YEARS))
        self.assertEqual(tuple(self.parquet.schema.names), TABLE_COLUMNS)

    def test_temporal_source_assignments_and_keys(self) -> None:
        expected_clc = {
            2015: 2006,
            2016: 2012,
            2017: 2012,
            2018: 2012,
            2019: 2018,
            2020: 2018,
            2021: 2018,
            2022: 2018,
            2023: 2018,
            2024: 2018,
        }
        for group, year in enumerate(OBSERVATION_YEARS):
            frame = self.parquet.read_row_group(
                group,
                columns=[
                    "cell_year_id", "cell_id", "observation_year", "outcome_year",
                    "historical_fire_start_year", "historical_fire_end_year",
                    "climate_reference_year", "land_cover_reference_year",
                ],
            ).to_pandas()
            self.assertEqual(len(frame), 89_112)
            self.assertTrue(frame.cell_id.is_unique)
            self.assertTrue(frame.cell_year_id.is_unique)
            self.assertEqual(set(frame.observation_year), {year})
            self.assertEqual(set(frame.outcome_year), {year + 1})
            self.assertEqual(set(frame.historical_fire_start_year), {year - 10})
            self.assertEqual(set(frame.historical_fire_end_year), {year - 1})
            self.assertEqual(set(frame.climate_reference_year), {year})
            self.assertEqual(set(frame.land_cover_reference_year), {expected_clc[year]})

    def test_climate_coastal_fallback_resolves_all_missingness(self) -> None:
        climate = (
            "warm_season_mean_2m_temperature_c",
            "warm_season_total_precipitation_mm",
            "warm_season_mean_soil_water_layer1",
            "warm_season_max_monthly_2m_temperature_c",
            "warm_season_min_monthly_soil_water_layer1",
        )
        for group in range(self.parquet.num_row_groups):
            frame = self.parquet.read_row_group(group, columns=["cell_id", *climate]).to_pandas()
            self.assertFalse(frame[list(climate)].isna().any().any())

    def test_build_recorded_complete_atomic_batches_and_determinism(self) -> None:
        """Read the build's own verification evidence; do not rebuild tiles in tests."""
        build = json.loads(BUILD_METRICS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(build["stage_results"]["grid"]["batch_count"], self.catalog["batch_count"])
        metrics = json.loads(VALIDATION_METRICS_PATH.read_text(encoding="utf-8"))
        deterministic = metrics["representative_batch_determinism"]
        self.assertTrue(deterministic["analytical_values_exact"])
        self.assertFalse(deterministic["publication_side_effects"])
        self.assertEqual(deterministic["component_check_count"], 21)

    def test_machine_and_human_validation_reports_agree(self) -> None:
        metrics = json.loads(VALIDATION_METRICS_PATH.read_text(encoding="utf-8"))
        report = VALIDATION_REPORT_PATH.read_text(encoding="utf-8")
        decision = "National panel validated — panel EDA may begin."
        self.assertEqual(metrics["panel_readiness_decision"], decision)
        self.assertIn(decision, report)
        self.assertTrue(metrics["climate_coastal_fallback"]["adopted"])
        self.assertEqual(metrics["climate_coastal_fallback"]["missing_rows_after"], 0)
        self.assertFalse(metrics["modelling_readiness"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
