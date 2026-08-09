"""Lightweight contracts for the validation-only hyperparameter runner."""

from __future__ import annotations

import unittest

from src.extended_model_refit import TRAIN_YEARS, VALIDATION_YEARS
from src.hyperparameter_experiments import (
    CANDIDATES,
    TRAIN_SAMPLE_ROWS_PER_YEAR,
    V1_OCCURRENCE_PARAMS,
    V1_POSITIVE_SHARE_PARAMS,
    _configuration,
    _output_paths,
)


class HyperparameterExperimentTests(unittest.TestCase):
    def test_experiment_candidates_include_current_frozen_reference(self) -> None:
        self.assertIn("current_frozen", CANDIDATES)
        self.assertEqual(CANDIDATES["current_frozen"]["occurrence"], V1_OCCURRENCE_PARAMS)
        self.assertEqual(CANDIDATES["current_frozen"]["positive_share"], V1_POSITIVE_SHARE_PARAMS)

    def test_current_configuration_preserves_v1_reference_after_v2_promotion(self) -> None:
        config = _configuration("current_frozen")
        self.assertEqual(config["occurrence"], V1_OCCURRENCE_PARAMS)
        self.assertEqual(config["positive_share"], V1_POSITIVE_SHARE_PARAMS)

    def test_experiment_scope_has_no_final_test_year(self) -> None:
        self.assertEqual(TRAIN_YEARS, tuple(range(2010, 2020)))
        self.assertEqual(VALIDATION_YEARS, (2020, 2021))
        self.assertTrue(all(year < 2022 for year in (*TRAIN_YEARS, *VALIDATION_YEARS)))

    def test_default_screening_sample_is_temporally_balanced_by_design(self) -> None:
        self.assertEqual(TRAIN_SAMPLE_ROWS_PER_YEAR, 15_000)

    def test_run_paths_are_isolated_by_experiment_name(self) -> None:
        metrics, predictions, report = _output_paths("full_training_confirmation")
        self.assertIn("full_training_confirmation", str(metrics))
        self.assertIn("full_training_confirmation", str(predictions))
        self.assertIn("full_training_confirmation", str(report))


if __name__ == "__main__":
    unittest.main(verbosity=2)
