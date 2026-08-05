"""Focused tests for the train/validation-only regression selection gate."""

import json
import unittest

import numpy as np
import pandas as pd

from src.feature_contract import FIELD_CONTRACTS, PREDICTOR_COLUMNS
from src.model_selection import (
    ARTIFACT_METADATA_PATH,
    FINAL_TEST_YEARS,
    METRICS_PATH,
    MODEL_SELECTION_YEARS,
    PREDICTIONS_PATH,
    TRAIN_YEARS,
    VALIDATION_YEARS,
    HistoricalFireMeanRegressor,
    capture_at_20_percent,
    read_train_validation_rows,
    validate_model_selection_frame,
)


class ModelSelectionTests(unittest.TestCase):
    def test_climate_missingness_is_forbidden(self) -> None:
        for name in PREDICTOR_COLUMNS[-3:]:
            self.assertEqual(FIELD_CONTRACTS[name].missing_rule, "forbidden")

    def test_loader_opens_no_final_test_row_groups(self) -> None:
        frame, audit = read_train_validation_rows()
        self.assertEqual(tuple(sorted(frame.observation_year.unique())), MODEL_SELECTION_YEARS)
        self.assertFalse(frame.observation_year.isin(FINAL_TEST_YEARS).any())
        self.assertEqual(audit["final_test_rows_read"], 0)
        self.assertEqual(audit["unopened_final_test_row_groups"], [7, 8, 9])
        contract = validate_model_selection_frame(frame)
        self.assertEqual(contract["train_rows"], 445_560)
        self.assertEqual(contract["validation_rows"], 178_224)

    def test_historical_baseline_fits_training_mapping_only(self) -> None:
        X = pd.DataFrame({"fire_years_previous_10y_2km": [0, 0, 1, 1]})
        y = pd.Series([0.0, 0.2, 0.4, 0.8])
        model = HistoricalFireMeanRegressor().fit(X, y)
        predicted = model.predict(pd.DataFrame({"fire_years_previous_10y_2km": [0, 1, 9]}))
        np.testing.assert_allclose(predicted, [0.1, 0.6, 0.35])

    def test_capture_at_20_percent(self) -> None:
        y = np.array([1.0, 0.5, 0.0, 0.0, 0.0])
        prediction = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
        cell_ids = np.array(["a", "b", "c", "d", "e"])
        years = np.repeat(2020, 5)
        self.assertEqual(capture_at_20_percent(y, prediction, cell_ids, years), 0.5)

    def test_published_artifacts_record_the_frozen_contract(self) -> None:
        if not METRICS_PATH.exists():
            self.skipTest("Run scripts/run_model_selection.py to publish artifacts")
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        metadata = json.loads(ARTIFACT_METADATA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(metrics["split"]["training_years"], list(TRAIN_YEARS))
        self.assertEqual(metrics["split"]["validation_years"], list(VALIDATION_YEARS))
        self.assertEqual(metrics["row_group_access"]["final_test_rows_read"], 0)
        self.assertEqual(metadata["feature_order"], list(PREDICTOR_COLUMNS))
        self.assertTrue(PREDICTIONS_PATH.exists())
        for record in metrics["repeatability"].values():
            self.assertTrue(record["predictions_identical_on_second_fit"])
        for record in metrics["artifacts"].values():
            self.assertTrue(record["reload_predictions_identical"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
