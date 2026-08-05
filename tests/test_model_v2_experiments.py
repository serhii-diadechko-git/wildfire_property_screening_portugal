"""Focused tests for the new zero-inflation-aware continuous candidate."""

import unittest
import json

import numpy as np
import pandas as pd

from src.feature_contract import PREDICTOR_COLUMNS
from src.model_v2_experiments import (
    HurdleHistGradientRegressor,
    ISOLATED_CLIMATE_PAIR_FEATURES,
    ISOLATED_METRICS_PATH,
    METRICS_PATH,
    isolated_climate_pair_gate,
    tie_aware_ranking_metrics,
)
from src.model_v2_features import FEATURE_GROUPS


class ModelV2ExperimentTests(unittest.TestCase):
    def test_isolated_feature_contract_adds_only_two_climate_extremes(self) -> None:
        self.assertEqual(len(ISOLATED_CLIMATE_PAIR_FEATURES), 9)
        self.assertEqual(ISOLATED_CLIMATE_PAIR_FEATURES[:7], PREDICTOR_COLUMNS)
        self.assertEqual(
            ISOLATED_CLIMATE_PAIR_FEATURES[-2:],
            (
                "warm_season_max_monthly_2m_temperature_c",
                "warm_season_min_monthly_soil_water_layer1",
            ),
        )

    def test_tie_aware_ranking_fractionally_allocates_boundary_group(self) -> None:
        target = np.array([1.0, 0.0, 1.0, 0.0])
        scores = np.array([2.0, 1.0, 1.0, 0.0])
        result = tie_aware_ranking_metrics(target, scores, 0.5)
        self.assertAlmostEqual(result["selected_rows_fractional"], 2.0)
        self.assertAlmostEqual(result["positive_cell_capture"], 0.75)
        self.assertAlmostEqual(result["burned_share_mass_capture"], 0.75)

    def test_isolated_gate_requires_stability_in_both_validation_years(self) -> None:
        def result(mae: float, rmse: float, positive_mae: float, bias: float) -> dict:
            overall = {
                "mae_all": mae,
                "rmse_all": rmse,
                "mae_positive": positive_mae,
                "mean_observed": 0.01,
                "mean_predicted": 0.01 + bias,
            }
            return {
                "overall": overall,
                "by_validation_year": {"2020": dict(overall), "2021": dict(overall)},
            }

        metrics = {
            "historical_fire_baseline": result(0.03, 0.08, 0.20, 0.02),
            "canonical_7_hurdle": result(0.02, 0.081, 0.201, 0.015),
            "climate_extremes_9_hurdle": result(0.019, 0.08, 0.20, 0.01),
        }
        self.assertTrue(isolated_climate_pair_gate(metrics)["passes_gate"])
        metrics["climate_extremes_9_hurdle"]["by_validation_year"]["2021"]["mae_all"] = 0.021
        self.assertFalse(isolated_climate_pair_gate(metrics)["passes_gate"])

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

    def test_published_isolated_experiment_obeys_audit_contract(self) -> None:
        if not ISOLATED_METRICS_PATH.exists():
            self.skipTest("Run scripts/run_isolated_climate_pair_validation.py first")
        result = json.loads(ISOLATED_METRICS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(result["split"]["final_test_rows_read"], 0)
        self.assertEqual(result["split"]["final_test_years_accessed"], [])
        self.assertEqual(result["feature_order"], list(ISOLATED_CLIMATE_PAIR_FEATURES))
        self.assertTrue(result["determinism"]["repeat_fit_predictions_identical"])
        self.assertTrue(result["determinism"]["saved_model_reload_predictions_identical"])
        self.assertEqual(
            set(result["tie_aware_ranking_diagnostics"]["climate_extremes_9_hurdle"]["overall"]),
            {"top_10_percent", "top_20_percent"},
        )


if __name__ == "__main__":
    unittest.main()
