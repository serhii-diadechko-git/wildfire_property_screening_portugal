"""Contracts for the protocol-frozen extended final temporal test."""

from __future__ import annotations

import json
import unittest

from src.extended_final_test import FINAL_TEST_YEARS, METRICS_PATH
from src.modeling import NINE_FEATURES


class ExtendedFinalTestTests(unittest.TestCase):
    def test_final_test_years_are_fixed(self) -> None:
        self.assertEqual(FINAL_TEST_YEARS, (2022, 2023, 2024))

    def test_published_final_test_uses_frozen_contract(self) -> None:
        if not METRICS_PATH.exists():
            self.skipTest("Run scripts/run_extended_final_temporal_test.py first")
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(metrics["design"]["final_test_years"], list(FINAL_TEST_YEARS))
        self.assertFalse(metrics["design"]["tuning_performed"])
        self.assertEqual(metrics["design"]["feature_order"], list(NINE_FEATURES))
        self.assertEqual(metrics["feature_matrix"]["row_count"], 89112 * len(FINAL_TEST_YEARS))
        for model in metrics["metrics"].values():
            self.assertEqual(set(model["by_final_test_year"]), {"2022", "2023", "2024"})

if __name__ == "__main__":
    unittest.main(verbosity=2)
