"""Focused tests for the new zero-inflation-aware continuous candidate."""

import unittest
import json

import numpy as np
import pandas as pd

from src.model_v2_experiments import HurdleHistGradientRegressor, METRICS_PATH
from src.model_v2_features import FEATURE_GROUPS


class ModelV2ExperimentTests(unittest.TestCase):
    def test_hurdle_returns_finite_nonnegative_continuous_values(self) -> None:
        X = pd.DataFrame({"x": np.arange(40, dtype=float), "z": np.mod(np.arange(40), 3)})
        y = pd.Series(np.where(np.mod(np.arange(40), 4) == 0, 0.3, 0.0))
        predicted = HurdleHistGradientRegressor().fit(X, y).predict(X)
        self.assertTrue(np.isfinite(predicted).all())
        self.assertTrue((predicted >= 0.0).all())
        self.assertTrue((predicted <= 1.0).all())

    def test_published_experiment_never_accesses_final_test_years(self) -> None:
        if not METRICS_PATH.exists():
            self.skipTest("Run scripts/run_model_v2_feature_groups.py to publish experiment metrics")
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(metrics["split"]["final_test_rows_read"], 0)
        self.assertEqual(set(metrics["groups"]), set(FEATURE_GROUPS))
        for group, result in metrics["groups"].items():
            self.assertEqual(result["features"], list(FEATURE_GROUPS[group]))
            for artifact in result["artifacts"].values():
                self.assertTrue(artifact["reload_predictions_identical"])


if __name__ == "__main__":
    unittest.main()
