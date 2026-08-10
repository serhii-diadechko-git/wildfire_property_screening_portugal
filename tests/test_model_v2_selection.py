"""Contracts for the documented validation-selected final-model configuration."""

from __future__ import annotations

import json
import unittest

from src.model_v2_reporting import EXPERIMENT_PATH, V1_NAME, V2_NAME, load_experiment
from src.modeling import MODEL_SPECIFICATION_VERSION, HurdleHistGradientRegressor


class ModelV2SelectionTests(unittest.TestCase):
    def test_active_defaults_are_the_validation_selected_v2_configuration(self) -> None:
        model = HurdleHistGradientRegressor()
        self.assertEqual(MODEL_SPECIFICATION_VERSION, "v2_validation_selected_20260809")
        self.assertEqual(model.parameter_config()["occurrence"]["max_leaf_nodes"], 31)
        self.assertEqual(model.parameter_config()["positive_share"]["max_iter"], 210)

    def test_recorded_experiment_is_validation_only_and_supports_v2_selection(self) -> None:
        if not EXPERIMENT_PATH.is_file():
            self.skipTest("Run the full-training hyperparameter experiment first")
        result = load_experiment()
        self.assertEqual(result["scope"]["final_test_years_accessed"], [])
        self.assertEqual(result["scope"]["final_test_rows_read"], 0)
        metrics = {row["candidate"]: row for row in result["summary"]}
        self.assertLess(metrics[V2_NAME]["mae_all"], metrics[V1_NAME]["mae_all"])
        self.assertGreater(
            metrics[V2_NAME]["burned_share_mass_capture_at_20_percent"],
            metrics[V1_NAME]["burned_share_mass_capture_at_20_percent"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
