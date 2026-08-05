"""Focused contracts for the isolated backward training extension."""

from __future__ import annotations

import json
import unittest

from src.extended_model_refit import (
    ALLOWED_YEARS,
    FEATURE_MATRIX_PATH,
    METRICS_PATH,
    NINE_FEATURES,
    TRAIN_YEARS,
    VALIDATION_YEARS,
)
from src.extended_training_panel import (
    CANONICAL_REUSED_YEARS,
    NEW_OBSERVATION_YEARS,
    extended_source_years,
)
from src.feature_contract import PREDICTOR_COLUMNS


class ExtendedTrainingRefitTests(unittest.TestCase):
    def test_backward_source_years_are_strictly_prior_only(self) -> None:
        years = extended_source_years(2010)
        self.assertEqual(years["history_years"], tuple(range(2000, 2010)))
        self.assertEqual(years["outcome_year"], 2011)
        self.assertEqual(years["land_cover_reference_year"], 2006)
        self.assertTrue(all(year < 2010 for year in years["history_years"]))

    def test_extended_clc_transition_and_canonical_isolation(self) -> None:
        self.assertEqual(extended_source_years(2014)["land_cover_reference_year"], 2006)
        self.assertEqual(extended_source_years(2016)["land_cover_reference_year"], 2012)
        self.assertEqual(extended_source_years(2019)["land_cover_reference_year"], 2018)
        self.assertEqual(NEW_OBSERVATION_YEARS, (2010, 2011, 2012, 2013, 2014))
        self.assertEqual(CANONICAL_REUSED_YEARS, (2015, 2016, 2017, 2018, 2019, 2020, 2021))

    def test_frozen_nine_feature_contract(self) -> None:
        self.assertEqual(NINE_FEATURES[:7], PREDICTOR_COLUMNS)
        self.assertEqual(NINE_FEATURES[-2:], (
            "warm_season_max_monthly_2m_temperature_c",
            "warm_season_min_monthly_soil_water_layer1",
        ))
        self.assertEqual(ALLOWED_YEARS, tuple(range(2010, 2022)))
        self.assertEqual(TRAIN_YEARS, tuple(range(2010, 2020)))
        self.assertEqual(VALIDATION_YEARS, (2020, 2021))

    def test_published_refit_never_accesses_final_test(self) -> None:
        if not METRICS_PATH.exists() or not FEATURE_MATRIX_PATH.exists():
            self.skipTest("Run scripts/refit_extended_training_models.py first")
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(metrics["design"]["final_test_years_accessed"], [])
        self.assertEqual(metrics["design"]["final_test_rows_read"], 0)
        self.assertEqual(metrics["design"]["train_years"], list(TRAIN_YEARS))
        self.assertEqual(metrics["design"]["validation_years"], list(VALIDATION_YEARS))
        self.assertEqual(metrics["design"]["feature_order"], list(NINE_FEATURES))
        self.assertTrue(metrics["reproducibility"]["saved_model_reload_predictions_identical"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
