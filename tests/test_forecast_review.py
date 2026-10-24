"""Temporal leakage, paired evaluation, and publication-date regression checks."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.feature_contract import PREDICTOR_COLUMNS, TARGET_COLUMN
from src.forecast_availability import check_availability
from src.forecast_review import (aggregate_forecasts, block_year_draws, fit_predict,
                                 metrics, paired_uncertainty, sha256, split_fold)

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / "data/processed"


class ForecastReviewTests(unittest.TestCase):
    def panel(self):
        records = []
        for y in range(2011, 2018):
            for cell in range(30):
                records.append({"cell_id": str(cell), "outcome_year": y, "observation_year": y-1,
                                **{key: float(cell % 4) / 4 for key in PREDICTOR_COLUMNS},
                                TARGET_COLUMN: .2 if cell % 5 == 0 else 0.})
        return pd.DataFrame(records)

    def test_fold_excludes_previous_year_unreleased_labels(self):
        train, test = split_fold(self.panel(), 2016)
        self.assertEqual(train.outcome_year.max(), 2014)
        self.assertEqual(set(test.observation_year), {2015})
        self.assertEqual(set(test.outcome_year), {2016})

    def test_future_labels_cannot_change_fit_predictions(self):
        panel = self.panel()
        train, test = split_fold(panel, 2016)
        # Small real two-stage fits, while preserving separate new estimators.
        with patch("src.modeling.HurdleHistGradientRegressor.DEFAULT_OCCURRENCE_PARAMS", {"max_iter": 2}), \
             patch("src.modeling.HurdleHistGradientRegressor.DEFAULT_POSITIVE_SHARE_PARAMS", {"max_iter": 2}):
            first, models = fit_predict(train, test[["cell_id", *PREDICTOR_COLUMNS]])
            panel.loc[panel.outcome_year.gt(2014), TARGET_COLUMN] = .99
            changed_train, changed_test = split_fold(panel, 2016)
            second, _ = fit_predict(changed_train, changed_test[["cell_id", *PREDICTOR_COLUMNS]])
        for key in first:
            np.testing.assert_array_equal(first[key], second[key])
        self.assertIsNot(models["hurdle_published_parameters"], models["hurdle_fixed_iterations"])
        self.assertFalse(models["hurdle_fixed_iterations"].occurrence_model.early_stopping)
        with self.assertRaises(ValueError):
            fit_predict(train, test)

    def test_duplicate_keys_and_target_year_mismatch_rejected(self):
        panel = self.panel()
        with self.assertRaises(ValueError):
            split_fold(pd.concat([panel, panel.iloc[:1]]), 2016)
        panel.loc[0, "outcome_year"] += 1
        with self.assertRaises(ValueError):
            split_fold(panel, 2016)

    def test_zero_baseline_ties_have_no_ranking_skill(self):
        result = metrics(np.array([0., 0., .5, 1.]), np.zeros(4))
        self.assertAlmostEqual(result["mass_capture20"], .2)
        self.assertAlmostEqual(result["positive_capture20"], .2)
        self.assertEqual(result["zero_mae"], 0)

    def test_latest_available_baseline_uses_y_minus_two(self):
        values = pd.Series([.1, .2, .3, .4, .99, .99], index=range(2011, 2017))
        result = aggregate_forecasts(values, 2016)
        self.assertEqual(result["latest_available_year"], .4)
        self.assertAlmostEqual(result["training_mean"], .25)
        values.loc[2015:] = 0
        self.assertEqual(result, aggregate_forecasts(values, 2016))

    def test_year_block_draws_keep_consecutive_years(self):
        draws = block_year_draws(10, 2, 100, 10)
        np.testing.assert_array_equal((draws[:, 0::2] + 1) % 10, draws[:, 1::2])

    def test_paired_identical_models_have_zero_difference_and_interval(self):
        annual = pd.DataFrame([dict(model=model, outcome_year=y, rows=100, positive_rows=5,
                                   mae=.01*y, rmse=.02*y, positive_mae=.03*y, mass_capture20=.5)
                              for model in ("a", "b") for y in range(1, 5)])
        result = paired_uncertainty(annual, "a", "b", 2, 100)
        self.assertTrue(result[["difference", "lower95", "upper95"]].eq(0).all().all())


class AvailabilityTests(unittest.TestCase):
    def manifest(self, root):
        m = dict(forecast_year=2027, issue_at="2026-12-31T12:00:00+00:00",
                 input_cutoff="2026-12-30T23:59:59+00:00", predictor_year=2026,
                 latest_training_outcome_year=2025, inputs=[])
        for source, years in (("icnf", list(range(2000, 2026))),
                              ("era5_land", list(range(2010, 2027))),
                              ("clc", [2006, 2012, 2018]), ("terrain", []), ("grid", [])):
            path = root / (source + ".txt")
            path.write_text("synthetic fixture")
            m["inputs"].append(dict(source=source, reference_years=years, path=path.name,
                                     sha256=sha256(path), available_at="2026-12-01T00:00:00Z",
                                     acquired_at="2026-12-02T00:00:00Z", version="test",
                                     release_evidence_url="https://example.test/release", completed_period=True,
                                     observation_end="2025-12-31T23:59:59Z" if source == "icnf" else "2026-09-30T23:59:59Z"))
        return m

    def test_known_dates_and_checksums_pass(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            result = check_availability(self.manifest(root), root, datetime(2026, 12, 30, tzinfo=timezone.utc))
            self.assertEqual(result["issues"], [])

    def test_late_unknown_incomplete_and_corrupt_inputs_block(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            for key, value in (("available_at", None), ("acquired_at", "2027-01-10T00:00:00Z"),
                               ("completed_period", False), ("sha256", "bad"),
                               ("observation_end", "2025-10-01T00:00:00Z")):
                m = self.manifest(root)
                m["inputs"][0][key] = value
                self.assertEqual(check_availability(m, root, datetime(2026, 12, 30, tzinfo=timezone.utc))["status"], "blocked")

    def test_missing_source_and_late_issue_block(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            m = self.manifest(root)
            m["inputs"].pop()
            result = check_availability(m, root, datetime(2027, 1, 1, tzinfo=timezone.utc))
            self.assertTrue(any("Issue date has passed" in s for s in result["issues"]))
            self.assertTrue(any("grid: missing" in s for s in result["issues"]))


if __name__ == "__main__":
    unittest.main()
