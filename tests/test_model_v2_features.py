"""Focused pure tests for V2 feature grouping and leakage guards."""

import unittest

import numpy as np
import pandas as pd

from src.feature_contract import PREDICTOR_COLUMNS
from src.model_v2_features import EXTRA_FEATURE_COLUMNS, FEATURE_GROUPS, _history_extension_frame


class ModelV2FeatureTests(unittest.TestCase):
    def test_groups_are_cumulative_and_preserve_baseline_order(self) -> None:
        self.assertEqual(FEATURE_GROUPS["baseline_7"], PREDICTOR_COLUMNS)
        self.assertEqual(len(FEATURE_GROUPS["full_v2_15"]), 15)
        self.assertEqual(FEATURE_GROUPS["full_v2_15"][-8:], EXTRA_FEATURE_COLUMNS)

    def test_history_extension_is_strictly_prior_to_t(self) -> None:
        frame = pd.DataFrame({"cell_id": ["a"]})
        for year in range(2005, 2022):
            frame[f"context_{year}"] = year == 2014
            frame[f"share_{year}"] = 0.25 if year == 2014 else 0.0
        result = _history_extension_frame(frame, np.array(["a"]))
        row = result.loc[result.observation_year.eq(2015)].iloc[0]
        self.assertEqual(row.years_since_last_context_fire_2km, 1)
        self.assertEqual(row.burned_share_previous_3y_1km, 0.25)
        self.assertEqual(row.burned_share_previous_10y_1km, 0.25)


if __name__ == "__main__":
    unittest.main()
