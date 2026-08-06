"""Guards for the annual operational forecast contract."""

from __future__ import annotations

import json
import unittest

import joblib
import pyarrow.parquet as pq

from src.config import OPERATIONAL_FORECAST
from src.modeling import NINE_FEATURES
from src.operational_forecast import (
    CURRENT_FORECAST_YEAR,
    LABELED_PANEL_PATH,
    MODEL_METADATA_PATH,
    MODEL_PATH,
    PANEL_MANIFEST_PATH,
    forecast_preflight,
    run_operational_forecast,
    validate_forecast_artifacts,
)


class OperationalForecastTests(unittest.TestCase):
    def test_annual_cutoff_has_no_future_outcome(self) -> None:
        self.assertEqual(OPERATIONAL_FORECAST.predictor_year(2026), 2025)
        self.assertEqual(OPERATIONAL_FORECAST.latest_labeled_predictor_year(2026), 2024)
        self.assertEqual(OPERATIONAL_FORECAST.latest_observed_outcome_year(2026), 2025)
        self.assertEqual(OPERATIONAL_FORECAST.history_years(2026), tuple(range(2015, 2025)))

    def test_labeled_panel_preserves_the_nine_feature_target_contract(self) -> None:
        self.assertTrue(LABELED_PANEL_PATH.is_file())
        manifest = json.loads(PANEL_MANIFEST_PATH.read_text(encoding="utf-8"))
        metadata = pq.ParquetFile(LABELED_PANEL_PATH).metadata
        self.assertEqual(metadata.num_rows, 89_112 * 15)
        self.assertEqual(manifest["observation_years"], list(range(2010, 2025)))
        self.assertEqual(manifest["feature_order"], list(NINE_FEATURES))
        self.assertEqual(manifest["target_lineage"], "Copied from validated ICNF T+1 labels; no target recalculation performed.")

    def test_operational_model_is_refit_only_through_observed_2025_outcome(self) -> None:
        self.assertTrue(MODEL_PATH.is_file())
        metadata = json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))
        payload = joblib.load(MODEL_PATH)
        self.assertEqual(metadata["training_predictor_years"], list(range(2010, 2025)))
        self.assertEqual(metadata["training_observed_outcome_years"], list(range(2011, 2026)))
        self.assertEqual(payload["feature_order"], list(NINE_FEATURES))
        self.assertIn("not a probability", payload["output_interpretation"])

    def test_current_preflight_is_ready_with_2025_era5_and_no_future_data(self) -> None:
        preflight = forecast_preflight(CURRENT_FORECAST_YEAR)
        self.assertEqual(preflight["status"], "ready_for_feature_derivation")
        self.assertEqual(preflight["missing_inputs"], [])
        self.assertFalse(preflight["target_present_in_scoring_input"])
        self.assertIn("ICNF 2026", preflight["prohibited_sources"])
        self.assertIn("ERA5-Land 2026", preflight["prohibited_sources"])

    def test_published_2026_score_has_no_target_and_reloads_identically(self) -> None:
        validation = validate_forecast_artifacts(CURRENT_FORECAST_YEAR)
        self.assertEqual(validation["row_count"], 89_112)
        self.assertFalse(validation["target_present"])
        self.assertEqual(validation["matrix_missing_values"], 0)
        self.assertEqual(validation["score_missing_values"], 0)
        self.assertTrue(validation["model_reload_predictions_identical"])
        self.assertEqual(
            validation["climate_assignment_counts"],
            {"containing_valid_era5_land_cell": 87_606, "nearest_valid_era5_land_cell": 1_506},
        )

    def test_operational_rerun_revalidates_without_overwriting(self) -> None:
        result = run_operational_forecast(CURRENT_FORECAST_YEAR)
        self.assertEqual(result["status"], "validated_reused")


if __name__ == "__main__":
    unittest.main()
