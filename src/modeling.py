"""Stable estimator and feature contract for the operational model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

RANDOM_SEED = 20260805

# The final nine-feature model was selected using only the complete T=2020-2021 validation set.
# It is intentionally a versioned, explicit configuration rather than an
# implicit change hidden in a fitted joblib artefact.
MODEL_SPECIFICATION_VERSION = "v2_validation_selected_20260809"


@dataclass
class HistoricalFireMeanRegressor:
    """Training-only empirical target mean for each historical-fire count."""

    feature_name: str = "fire_years_previous_10y_2km"
    means_by_count: dict[int, float] | None = None
    global_mean: float | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "HistoricalFireMeanRegressor":
        values = pd.DataFrame({"count": X[self.feature_name].astype(int), "target": y.astype(float)})
        self.means_by_count = {
            int(key): float(value)
            for key, value in values.groupby("count", sort=True)["target"].mean().items()
        }
        self.global_mean = float(y.mean())
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.means_by_count is None or self.global_mean is None:
            raise RuntimeError("HistoricalFireMeanRegressor is not fitted")
        return (
            X[self.feature_name]
            .astype(int)
            .map(self.means_by_count)
            .fillna(self.global_mean)
            .to_numpy(dtype=np.float64)
        )


class HurdleHistGradientRegressor:
    """Continuous expected burned share from occurrence and positive-share parts."""

    # Validation-selected operational defaults. Validation-only experiments
    # may override them explicitly, but must never mutate this dictionary.
    DEFAULT_OCCURRENCE_PARAMS: dict[str, Any] = {
        "learning_rate": 0.07,
        "max_iter": 160,
        "max_leaf_nodes": 31,
        "min_samples_leaf": 80,
        "l2_regularization": 0.02,
    }
    DEFAULT_POSITIVE_SHARE_PARAMS: dict[str, Any] = {
        "loss": "squared_error",
        "learning_rate": 0.06,
        "max_iter": 210,
        "max_leaf_nodes": 31,
        "min_samples_leaf": 55,
        "l2_regularization": 0.02,
    }

    def __init__(
        self,
        *,
        random_state: int = RANDOM_SEED,
        occurrence_params: Mapping[str, Any] | None = None,
        positive_share_params: Mapping[str, Any] | None = None,
    ) -> None:
        self.random_state = random_state
        occurrence_config = dict(self.DEFAULT_OCCURRENCE_PARAMS)
        positive_config = dict(self.DEFAULT_POSITIVE_SHARE_PARAMS)
        if occurrence_params:
            occurrence_config.update(occurrence_params)
        if positive_share_params:
            positive_config.update(positive_share_params)
        if "random_state" in occurrence_config or "random_state" in positive_config:
            raise ValueError("Pass random_state through the model constructor, not a parameter override")
        self.occurrence_params = occurrence_config
        self.positive_share_params = positive_config
        self.occurrence_model = HistGradientBoostingClassifier(
            **occurrence_config, random_state=random_state
        )
        self.positive_model = HistGradientBoostingRegressor(
            **positive_config, random_state=random_state
        )

    def parameter_config(self) -> dict[str, dict[str, Any]]:
        """Return the concise, reproducible configuration used by this instance."""
        return {
            "occurrence": dict(self.occurrence_params),
            "positive_share": dict(self.positive_share_params),
        }

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "HurdleHistGradientRegressor":
        target = np.asarray(y, dtype="float64")
        positive = target > 0.0
        if positive.sum() < 2 or (~positive).sum() < 2:
            raise ValueError("Hurdle model needs both positive and zero targets")
        with threadpool_limits(limits=1, user_api="openmp"):
            self.occurrence_model.fit(X, positive.astype("int8"))
            self.positive_model.fit(X.loc[positive], target[positive])
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        probability = self.occurrence_model.predict_proba(X)[:, 1]
        positive_share = np.clip(self.positive_model.predict(X), 0.0, 1.0)
        return np.clip(probability * positive_share, 0.0, 1.0)
