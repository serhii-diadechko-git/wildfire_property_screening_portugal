"""Focused unit tests for the canonical feature-derivation contract."""

from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from src.feature_contract import TABLE_COLUMNS, source_years, validate_feature_table
from src.representative_feature_pilot import (
    PILOT_CELL_IDS,
    PILOT_YEARS,
    derive_representative_pilot,
    era5_source_paths,
    jjas_total_precipitation_mm,
)


class FeatureDerivationContractTests(unittest.TestCase):
    def test_temporal_alignment_is_strictly_leakage_safe(self) -> None:
        for predictor_year in PILOT_YEARS:
            years = source_years(predictor_year)
            self.assertEqual(years["climate_year"], predictor_year)
            self.assertEqual(years["outcome_year"], predictor_year + 1)
            self.assertEqual(years["history_years"], tuple(range(predictor_year - 10, predictor_year)))
            self.assertTrue(all(year < predictor_year for year in years["history_years"]))

    def test_clc_transition_assignments(self) -> None:
        self.assertEqual(source_years(2015)["land_cover_reference_year"], 2006)
        self.assertEqual(source_years(2016)["land_cover_reference_year"], 2012)
        self.assertEqual(source_years(2019)["land_cover_reference_year"], 2018)
        self.assertEqual(source_years(2023)["land_cover_reference_year"], 2018)

    def test_corrected_precipitation_selection(self) -> None:
        paths_2022 = era5_source_paths(2022)
        paths_2023 = era5_source_paths(2023)
        self.assertIn("monthly_by_hour_00", paths_2022["precipitation"].name)
        self.assertIn("monthly_by_hour_00", paths_2023["precipitation"].name)
        self.assertNotEqual(paths_2022["precipitation"], paths_2022["temperature_and_soil_water"])
        self.assertNotEqual(paths_2023["precipitation"], paths_2023["temperature_and_soil_water"])
        self.assertNotIn("monthly_by_hour_00", era5_source_paths(2019)["precipitation"].name)

    def test_day_weighted_precipitation_formula_and_mask(self) -> None:
        values = np.ones((4, 2, 1), dtype=float) * 0.001
        values[:, 1, 0] = np.nan
        result = jjas_total_precipitation_mm(values, (6, 7, 8, 9))
        self.assertAlmostEqual(result[0, 0], 122.0)
        self.assertTrue(np.isnan(result[1, 0]))

    @staticmethod
    def _valid_table() -> pd.DataFrame:
        rows = []
        for cell_id in ("A", "B"):
            for year in (2015, 2016):
                years = source_years(year)
                rows.append({
                    "cell_year_id": f"{cell_id}_{year}",
                    "cell_id": cell_id,
                    "observation_year": year,
                    "outcome_year": years["outcome_year"],
                    "historical_fire_start_year": years["history_years"][0],
                    "historical_fire_end_year": years["history_years"][-1],
                    "climate_reference_year": year,
                    "land_cover_reference_year": years["land_cover_reference_year"],
                    "land_cover_release_id": "V2020_20u1",
                    "land_cover_release_date": "2020",
                    "terrain_release_id": "2021",
                    "built_up_share": 0.2,
                    "forest_shrub_share_2km": 0.4,
                    "mean_slope_2km": 12.0,
                    "fire_years_previous_10y_2km": 3,
                    "warm_season_mean_2m_temperature_c": 22.0,
                    "warm_season_total_precipitation_mm": 100.0,
                    "warm_season_mean_soil_water_layer1": 0.2,
                    "burned_share_next_year": 0.1,
                })
        return pd.DataFrame(rows, columns=TABLE_COLUMNS)

    def test_schema_range_and_duplicate_contract(self) -> None:
        table = self._valid_table()
        result = validate_feature_table(table, expected_years=(2015, 2016), expected_cell_ids=("A", "B"))
        self.assertEqual(result["row_count"], 4)
        duplicate = pd.concat([table, table.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_feature_table(duplicate, expected_years=(2015, 2016), expected_cell_ids=("A", "B"))
        outside = table.copy()
        outside.loc[0, "built_up_share"] = 1.1
        with self.assertRaisesRegex(ValueError, "above allowed range"):
            validate_feature_table(outside, expected_years=(2015, 2016), expected_cell_ids=("A", "B"))

    def test_sample_definition_is_deterministic(self) -> None:
        self.assertEqual(PILOT_YEARS, (2015, 2016, 2019, 2023))
        self.assertEqual(len(PILOT_CELL_IDS), len(set(PILOT_CELL_IDS)))
        self.assertGreaterEqual(len(PILOT_CELL_IDS), 8)

    def test_repeated_source_derivation_is_exact(self) -> None:
        first, first_validation = derive_representative_pilot()
        second, second_validation = derive_representative_pilot()
        pd.testing.assert_frame_equal(
            first.drop(columns="geometry"),
            second.drop(columns="geometry"),
            check_exact=True,
        )
        self.assertEqual(first_validation["row_count"], 40)
        self.assertEqual(first_validation["missingness"], second_validation["missingness"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
