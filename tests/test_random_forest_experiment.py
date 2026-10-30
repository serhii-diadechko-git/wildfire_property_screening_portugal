"""Independent checks of delayed-label RF fits and forecast metrics."""
from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.evaluation import tie_aware_ranking_metrics
from src.feature_contract import PREDICTOR_COLUMNS, TARGET_COLUMN
from src.forecast_review import metrics, paired_uncertainty, split_fold
from src.random_forest_experiment import (
    RFHurdleRegressor,
    make_model,
    range_diagnostics,
)


class RandomForestExperimentTests(unittest.TestCase):
    @staticmethod
    def panel():
        records = []
        for year in range(2011, 2018):
            for cell in range(100):
                records.append({
                    "cell_id": f"cell_{cell:03d}",
                    "outcome_year": year,
                    "observation_year": year - 1,
                    **{name: float((cell + j + year) % 20) / 20
                       for j, name in enumerate(PREDICTOR_COLUMNS)},
                    TARGET_COLUMN: (cell % 7 + 1) / 10 if cell % 3 == 0 else 0.,
                })
        return pd.DataFrame(records)

    @staticmethod
    def tiny_model(name):
        if name == "rf_direct":
            return make_model(name).set_params(n_estimators=3, max_depth=3, n_jobs=1)
        return RFHurdleRegressor(n_estimators=3, max_depth=3, n_jobs=1)

    def test_rf_fit_cannot_see_unavailable_future_labels(self):
        frame = self.panel()
        train, test = split_fold(frame, 2016)
        self.assertEqual(train.outcome_year.max(), 2014)
        original = {}
        for name in ("rf_direct", "rf_hurdle"):
            model = self.tiny_model(name)
            model.fit(train.loc[:, PREDICTOR_COLUMNS], train[TARGET_COLUMN])
            original[name] = model.predict(test.loc[:, PREDICTOR_COLUMNS])
        frame.loc[frame.outcome_year >= 2015, TARGET_COLUMN] = .99
        changed_train, changed_test = split_fold(frame, 2016)
        for name in original:
            model = self.tiny_model(name)
            model.fit(changed_train.loc[:, PREDICTOR_COLUMNS], changed_train[TARGET_COLUMN])
            np.testing.assert_array_equal(
                original[name], model.predict(changed_test.loc[:, PREDICTOR_COLUMNS])
            )

    def test_hurdle_positive_fit_and_product(self):
        train, test = split_fold(self.panel(), 2016)
        model = self.tiny_model("rf_hurdle")
        X, y = train.loc[:, PREDICTOR_COLUMNS], train[TARGET_COLUMN]
        with patch.object(model.positive_model, "fit", wraps=model.positive_model.fit) as fit:
            model.fit(X, y)
            positive_y = np.asarray(fit.call_args.args[1])
            self.assertEqual(len(positive_y), int((y > 0).sum()))
            self.assertTrue((positive_y > 0).all())
        X_test = test.loc[:, PREDICTOR_COLUMNS]
        expected = model.occurrence_model.predict_proba(X_test)[:, 1] * np.clip(
            model.positive_model.predict(X_test), 0, 1
        )
        np.testing.assert_array_equal(model.predict(X_test), expected)
        self.assertTrue(np.isfinite(expected).all())
        self.assertTrue(((expected >= 0) & (expected <= 1)).all())

    def test_hurdle_rejects_target_as_predictor(self):
        train, _ = split_fold(self.panel(), 2016)
        X = train.loc[:, [*PREDICTOR_COLUMNS, TARGET_COLUMN]]
        with self.assertRaises(ValueError):
            self.tiny_model("rf_hurdle").fit(X, train[TARGET_COLUMN])

    def test_range_limits_come_only_from_train_and_include_boundaries(self):
        train = pd.DataFrame({name: np.arange(10.) for name in PREDICTOR_COLUMNS})
        test = pd.DataFrame({name: [-1., 0., 9., 10.] for name in PREDICTOR_COLUMNS})
        flags, bounds = range_diagnostics(train, test)
        np.testing.assert_array_equal(flags.outside_range, [True, False, False, True])
        self.assertTrue(bounds.train_min.eq(0).all())
        self.assertTrue(bounds.train_max.eq(9).all())
        self.assertTrue(bounds.test_below.eq(1).all())
        self.assertTrue(bounds.test_above.eq(1).all())
        changed_test = test * 100
        _, changed_bounds = range_diagnostics(train, changed_test)
        np.testing.assert_array_equal(
            bounds[["train_min", "train_max", "train_q10", "train_q90"]],
            changed_bounds[["train_min", "train_max", "train_q10", "train_q90"]],
        )

    def test_fractional_boundary_tie_has_exact_mass_and_is_permutation_invariant(self):
        y = np.array([.1, .2, .4, .3, 0.])
        score = np.array([.9, .8, .8, .2, .1])
        result = tie_aware_ranking_metrics(y, score, .4)
        self.assertAlmostEqual(result["burned_share_mass_capture"], .4)
        self.assertAlmostEqual(result["positive_cell_capture"], .5)
        perm = [2, 0, 4, 3, 1]
        shuffled = tie_aware_ranking_metrics(y[perm], score[perm], .4)
        self.assertEqual(result, shuffled)
        constant = metrics(y, np.zeros(len(y)))
        self.assertAlmostEqual(constant["mass_capture20"], .2)

    def test_paired_summary_recomputes_pooled_rmse_and_positive_weighting(self):
        records = []
        for name in ("a", "b"):
            for year, rows, positive, rmse, posmae in (
                (2016, 10, 2, .1, .5), (2017, 90, 18, .3, .1)
            ):
                records.append(dict(
                    model=name, outcome_year=year, rows=rows, positive_rows=positive,
                    mae=.1 if name == "a" else 0.,
                    rmse=rmse if name == "a" else 0.,
                    positive_mae=posmae if name == "a" else 0.,
                    mass_capture20=.6 if name == "a" else .2,
                ))
        annual = pd.DataFrame(records)
        result = paired_uncertainty(annual, "a", "b", 1, 100).set_index("metric")
        self.assertAlmostEqual(result.loc["rmse", "difference"], np.sqrt(.082))
        self.assertAlmostEqual(result.loc["positive_mae", "difference"], .14)
        self.assertAlmostEqual(result.loc["mass_capture20", "difference"], .4)
        repeated = paired_uncertainty(annual, "a", "b", 1, 100).set_index("metric")
        pd.testing.assert_frame_equal(result, repeated)


if __name__ == "__main__":
    unittest.main(verbosity=2)
