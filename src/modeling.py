"""Stable estimator and feature contract for the operational model."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

from src.feature_contract import MODEL_PREDICTOR_COLUMNS


RANDOM_SEED = 20260805
NINE_FEATURES = MODEL_PREDICTOR_COLUMNS


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

    def __init__(self, *, random_state: int = RANDOM_SEED) -> None:
        self.random_state = random_state
        self.occurrence_model = HistGradientBoostingClassifier(
            learning_rate=0.08,
            max_iter=120,
            max_leaf_nodes=23,
            min_samples_leaf=120,
            l2_regularization=0.05,
            random_state=random_state,
        )
        self.positive_model = HistGradientBoostingRegressor(
            loss="squared_error",
            learning_rate=0.07,
            max_iter=150,
            max_leaf_nodes=23,
            min_samples_leaf=80,
            l2_regularization=0.05,
            random_state=random_state,
        )

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
