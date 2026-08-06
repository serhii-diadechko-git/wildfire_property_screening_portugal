"""Stable regression-ranking diagnostics used by historical evaluation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.feature_contract import TARGET_COLUMN


def capture_at_fraction(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    cell_ids: np.ndarray,
    years: np.ndarray,
    fraction: float = 0.20,
) -> float:
    """Deterministic positive-row capture using stable cell/year tie breaking."""
    if not 0.0 < fraction <= 1.0:
        raise ValueError("fraction must be in (0, 1]")
    positive = y_true > 0.0
    positive_count = int(positive.sum())
    if positive_count == 0:
        return float("nan")
    top_count = int(np.ceil(fraction * len(y_true)))
    ranking = pd.DataFrame(
        {"prediction": y_pred, "cell_id": cell_ids.astype(str), "year": years, "positive": positive}
    ).sort_values(["prediction", "cell_id", "year"], ascending=[False, True, True], kind="mergesort")
    return float(ranking.iloc[:top_count].positive.sum() / positive_count)


def regression_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    cell_ids: np.ndarray,
    years: np.ndarray,
) -> dict[str, float | int]:
    """Canonical continuous-target error and ranking summary."""
    errors = y_pred - y_true
    positive = y_true > 0.0
    return {
        "rows": int(len(y_true)),
        "positive_target_rows": int(positive.sum()),
        "mae_all": float(np.mean(np.abs(errors))),
        "rmse_all": float(np.sqrt(np.mean(np.square(errors)))),
        "mae_positive": float(np.mean(np.abs(errors[positive]))),
        "rmse_positive": float(np.sqrt(np.mean(np.square(errors[positive])))),
        "mean_observed": float(np.mean(y_true)),
        "mean_predicted": float(np.mean(y_pred)),
        "capture_at_20_percent": capture_at_fraction(y_true, y_pred, cell_ids, years),
        "prediction_min": float(np.min(y_pred)),
        "prediction_max": float(np.max(y_pred)),
    }


def evaluate_predictions(validation: pd.DataFrame, predictions: np.ndarray) -> dict[str, Any]:
    """Evaluate predictions overall and separately for every present year."""
    y_true = validation[TARGET_COLUMN].to_numpy(dtype=np.float64)
    cell_ids = validation.cell_id.to_numpy()
    years = validation.observation_year.to_numpy(dtype=np.int16)
    return {
        "overall": regression_metrics(y_true, predictions, cell_ids, years),
        "by_validation_year": {
            str(year): regression_metrics(
                y_true[years == year], predictions[years == year], cell_ids[years == year], years[years == year]
            )
            for year in sorted(set(int(value) for value in years))
        },
    }


def tie_aware_ranking_metrics(
    y_true: np.ndarray,
    scores: np.ndarray,
    selection_fraction: float,
) -> dict[str, float | int]:
    """Evaluate a ranking without arbitrarily splitting equal-score boundary ties."""
    if not 0.0 < selection_fraction <= 1.0:
        raise ValueError("selection_fraction must be in (0, 1]")
    target = np.asarray(y_true, dtype="float64")
    ranking_scores = np.asarray(scores, dtype="float64")
    if target.shape != ranking_scores.shape or target.ndim != 1:
        raise ValueError("y_true and scores must be aligned one-dimensional arrays")
    if not np.isfinite(target).all() or not np.isfinite(ranking_scores).all():
        raise ValueError("Ranking inputs must be finite")
    grouped = (
        pd.DataFrame({
            "score": ranking_scores,
            "positive": (target > 0.0).astype("int64"),
            "burned_mass": target,
        })
        .groupby("score", sort=False, as_index=False)
        .agg(rows=("positive", "size"), positives=("positive", "sum"), burned_mass=("burned_mass", "sum"))
        .sort_values("score", ascending=False, kind="mergesort")
    )
    budget = selection_fraction * len(target)
    selected_rows = selected_positives = selected_mass = 0.0
    for row in grouped.itertuples(index=False):
        remaining = budget - selected_rows
        if remaining <= 0.0:
            break
        weight = min(1.0, remaining / float(row.rows))
        selected_rows += weight * float(row.rows)
        selected_positives += weight * float(row.positives)
        selected_mass += weight * float(row.burned_mass)
    positive_total = int((target > 0.0).sum())
    mass_total = float(target.sum())
    selected_positive_rate = selected_positives / selected_rows if selected_rows else float("nan")
    population_positive_rate = positive_total / len(target) if len(target) else float("nan")
    return {
        "selection_fraction": float(selection_fraction),
        "selected_rows_fractional": float(selected_rows),
        "unique_scores": int(grouped.shape[0]),
        "positive_cell_capture": float(selected_positives / positive_total) if positive_total else float("nan"),
        "burned_share_mass_capture": float(selected_mass / mass_total) if mass_total > 0.0 else float("nan"),
        "selected_positive_precision": float(selected_positive_rate),
        "positive_lift": float(selected_positive_rate / population_positive_rate)
        if population_positive_rate > 0.0 else float("nan"),
    }


def evaluate_tie_aware_rankings(validation: pd.DataFrame, predictions: np.ndarray) -> dict[str, Any]:
    """Report tie-aware 10% and 20% diagnostics overall and by present year."""
    target = validation[TARGET_COLUMN].to_numpy(dtype="float64")
    years = validation.observation_year.to_numpy(dtype="int16")

    def for_mask(mask: np.ndarray) -> dict[str, Any]:
        return {
            f"top_{int(fraction * 100)}_percent": tie_aware_ranking_metrics(
                target[mask], predictions[mask], fraction
            )
            for fraction in (0.10, 0.20)
        }

    return {
        "overall": for_mask(np.ones(len(validation), dtype=bool)),
        "by_validation_year": {
            str(year): for_mask(years == year) for year in sorted(set(int(value) for value in years))
        },
    }
