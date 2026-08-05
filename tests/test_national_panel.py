"""Focused validation tests for the assembled canonical national panel."""

import json
import unittest

import pandas as pd
import pyarrow.parquet as pq

from src.feature_contract import TABLE_COLUMNS
from src.national_panel import (
    NATIONAL_PANEL_PATH,
    OBSERVATION_YEARS,
    VALIDATION_METRICS_PATH,
    VALIDATION_REPORT_PATH,
    build_panel_batches,
    compare_representative_pilot,
    load_grid_catalog,
    verify_representative_batch_determinism,
)
from src.representative_feature_pilot import PILOT_CELL_IDS, PILOT_YEARS


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

    def test_climate_water_mask_is_joint_and_stable(self) -> None:
        climate = (
            "warm_season_mean_2m_temperature_c",
            "warm_season_total_precipitation_mm",
            "warm_season_mean_soil_water_layer1",
        )
        missing_ids = []
        for group in range(self.parquet.num_row_groups):
            frame = self.parquet.read_row_group(group, columns=["cell_id", *climate]).to_pandas()
            masks = frame[list(climate)].isna()
            self.assertTrue(masks.eq(masks.iloc[:, 0], axis=0).all().all())
            cells = tuple(frame.loc[masks.iloc[:, 0], "cell_id"])
            self.assertEqual(len(cells), 1_506)
            missing_ids.append(cells)
        self.assertEqual(len(set(missing_ids)), 1)

    def test_representative_pilot_regression(self) -> None:
        pieces = []
        for group, year in enumerate(OBSERVATION_YEARS):
            if year not in PILOT_YEARS:
                continue
            frame = self.parquet.read_row_group(group).to_pandas()
            pieces.append(frame.loc[frame.cell_id.isin(PILOT_CELL_IDS)])
        result = compare_representative_pilot(pd.concat(pieces, ignore_index=True))
        self.assertTrue(result["passed"])
        self.assertEqual(result["row_count"], 40)

    def test_completed_batches_are_reused_without_overwrite(self) -> None:
        result = build_panel_batches(progress=lambda _: None)
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["reused"], self.catalog["batch_count"])

    def test_representative_batch_rerun_is_exact(self) -> None:
        result = verify_representative_batch_determinism()
        self.assertTrue(result["analytical_values_exact"])
        self.assertFalse(result["publication_side_effects"])
        self.assertEqual(result["component_check_count"], 21)

    def test_machine_and_human_validation_reports_agree(self) -> None:
        metrics = json.loads(VALIDATION_METRICS_PATH.read_text(encoding="utf-8"))
        report = VALIDATION_REPORT_PATH.read_text(encoding="utf-8")
        decision = "National panel validated — panel EDA may begin."
        self.assertEqual(metrics["panel_readiness_decision"], decision)
        self.assertIn(decision, report)
        self.assertFalse(metrics["modelling_readiness"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
