"""Validate durable final-test model-reporting artefacts."""

from __future__ import annotations

import pandas as pd
import unittest

from src.model_diagnostics import DIAGNOSTIC_TABLES, validate_model_diagnostics


class ModelDiagnosticsTests(unittest.TestCase):
    def test_diagnostic_inventory_is_present_and_readable(self) -> None:
        inventory = validate_model_diagnostics()
        self.assertEqual(inventory["status"], "verified_existing")
        overall = pd.read_csv(DIAGNOSTIC_TABLES["overall_metrics"])
        by_year = pd.read_csv(DIAGNOSTIC_TABLES["by_year_metrics"])
        binned = pd.read_csv(DIAGNOSTIC_TABLES["binned_comparison"])
        self.assertEqual(
            set(overall["model"]),
            {"Historical recurrence baseline", "Final nine-feature model"},
        )
        self.assertEqual(set(by_year["predictor_year"]), {2022, 2023, 2024})
        self.assertEqual(int(binned["cell_count"].sum()), 267_336)


if __name__ == "__main__":
    unittest.main(verbosity=2)
