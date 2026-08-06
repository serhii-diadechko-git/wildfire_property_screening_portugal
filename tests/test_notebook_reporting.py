"""Unit checks for read-only model-reporting helpers used in notebooks."""

from __future__ import annotations

import unittest

import matplotlib.pyplot as plt
import pandas as pd

from src.notebook_reporting import (
    binned_observed_estimated_table,
    model_comparison_frame,
    plot_binned_observed_estimated,
    plot_metric_comparison,
    plot_prediction_diagnostics,
)


class NotebookReportingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metrics = {
            "metrics": {
                "historical_recurrence_baseline": {
                    "overall": {
                        "rows": 4,
                        "mae_all": 0.2,
                        "rmse_all": 0.3,
                        "mae_positive": 0.4,
                        "rmse_positive": 0.5,
                        "mean_observed": 0.1,
                        "mean_predicted": 0.08,
                        "capture_at_20_percent": 0.25,
                    }
                },
                "nine_feature_hurdle": {
                    "overall": {
                        "rows": 4,
                        "mae_all": 0.15,
                        "rmse_all": 0.25,
                        "mae_positive": 0.35,
                        "rmse_positive": 0.45,
                        "mean_observed": 0.1,
                        "mean_predicted": 0.09,
                        "capture_at_20_percent": 0.5,
                    }
                },
            }
        }
        self.predictions = pd.DataFrame(
            {
                "observation_year": [2022, 2022, 2023, 2023, 2024, 2024],
                "burned_share_next_year": [0.0, 0.1, 0.0, 0.2, 0.4, 0.0],
                "nine_feature_hurdle": [0.01, 0.08, 0.02, 0.16, 0.31, 0.03],
            }
        )

    def tearDown(self) -> None:
        plt.close("all")

    def test_comparison_table_preserves_error_and_ranking_metrics(self) -> None:
        comparison = model_comparison_frame(self.metrics)
        self.assertEqual(list(comparison.index), ["historical_recurrence_baseline", "nine_feature_hurdle"])
        self.assertAlmostEqual(comparison.loc["nine_feature_hurdle", "RMSE"], 0.25)
        self.assertAlmostEqual(comparison.loc["nine_feature_hurdle", "capture_at_20_percent"], 0.5)

    def test_diagnostic_tables_and_figures_are_read_only(self) -> None:
        comparison = model_comparison_frame(self.metrics)
        bins = binned_observed_estimated_table(self.predictions, model_column="nine_feature_hurdle", bins=3)
        self.assertEqual(int(bins["cell_count"].sum()), len(self.predictions))
        self.assertTrue((bins["mean_observed_share"] >= 0).all())
        self.assertEqual(len(plot_metric_comparison(comparison).axes), 3)
        self.assertEqual(len(plot_prediction_diagnostics(self.predictions, model_column="nine_feature_hurdle").axes), 4)
        self.assertEqual(len(plot_binned_observed_estimated(bins).axes), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
