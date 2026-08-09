"""Small, deterministic hyperparameter experiments on the validation split.

This module deliberately reads only the T=2010-2021 development matrix.  It
never opens the held-out final temporal test (T=2022-2024), writes no model
artifact, and cannot change the frozen operational model.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from src.evaluation import evaluate_predictions, evaluate_tie_aware_rankings
from src.extended_model_refit import (
    FEATURE_MATRIX_PATH,
    METRICS_PATH as ARCHIVED_METRICS_PATH,
    TRAIN_YEARS,
    VALIDATION_YEARS,
    _validate_frame,
)
from src.feature_contract import PREDICTOR_COLUMNS, TARGET_COLUMN
from src.modeling import HurdleHistGradientRegressor, RANDOM_SEED


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data/processed/extended_model_selection_2010_2021/hyperparameter_experiments"
TRAIN_SAMPLE_ROWS_PER_YEAR = 15_000

# A deliberately small, predeclared comparison.  It varies model capacity,
# shrinkage and regularisation without becoming an expensive broad search.
V1_OCCURRENCE_PARAMS = {
    "learning_rate": 0.08,
    "max_iter": 120,
    "max_leaf_nodes": 23,
    "min_samples_leaf": 120,
    "l2_regularization": 0.05,
}
V1_POSITIVE_SHARE_PARAMS = {
    "loss": "squared_error",
    "learning_rate": 0.07,
    "max_iter": 150,
    "max_leaf_nodes": 23,
    "min_samples_leaf": 80,
    "l2_regularization": 0.05,
}


CANDIDATES: dict[str, dict[str, Any]] = {
    "current_frozen": {
        "description": "Model v1 frozen operational configuration; reproducibility reference.",
        "occurrence": V1_OCCURRENCE_PARAMS,
        "positive_share": V1_POSITIVE_SHARE_PARAMS,
    },
    "smaller_regularized_trees": {
        "description": "Smaller trees, larger leaves and stronger L2 penalty.",
        "occurrence": {"learning_rate": 0.06, "max_iter": 160, "max_leaf_nodes": 15, "min_samples_leaf": 200, "l2_regularization": 0.20},
        "positive_share": {"learning_rate": 0.06, "max_iter": 200, "max_leaf_nodes": 15, "min_samples_leaf": 140, "l2_regularization": 0.20},
    },
    "slower_learning": {
        "description": "Lower learning rate with more boosting iterations at the current tree size.",
        "occurrence": {"learning_rate": 0.04, "max_iter": 240},
        "positive_share": {"learning_rate": 0.04, "max_iter": 300},
    },
    "larger_trees": {
        "description": "More tree leaves and smaller leaves to test additional non-linear detail.",
        "occurrence": {"learning_rate": 0.07, "max_iter": 160, "max_leaf_nodes": 31, "min_samples_leaf": 80, "l2_regularization": 0.02},
        "positive_share": {"learning_rate": 0.06, "max_iter": 210, "max_leaf_nodes": 31, "min_samples_leaf": 55, "l2_regularization": 0.02},
    },
    "moderate_complexity": {
        "description": "Intermediate complexity with mild regularisation.",
        "occurrence": {"learning_rate": 0.06, "max_iter": 180, "max_leaf_nodes": 27, "min_samples_leaf": 150, "l2_regularization": 0.10},
        "positive_share": {"learning_rate": 0.06, "max_iter": 220, "max_leaf_nodes": 27, "min_samples_leaf": 100, "l2_regularization": 0.10},
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _atomic_parquet(path: Path, value: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    value.to_parquet(temporary, index=False, compression="zstd")
    os.replace(temporary, path)


def _load_development_split() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not FEATURE_MATRIX_PATH.exists():
        raise FileNotFoundError(
            "Missing development matrix. Run scripts/refit_extended_training_models.py first."
        )
    # Load the full compact development matrix so the existing temporal-lineage
    # validator can prove that every predictor remains T-only.
    frame = pd.read_parquet(FEATURE_MATRIX_PATH)
    _validate_frame(frame)
    if frame.observation_year.isin((2022, 2023, 2024)).any():
        raise ValueError("Final-test year entered validation-only experiment")
    train = frame.loc[frame.observation_year.isin(TRAIN_YEARS)].copy()
    validation = frame.loc[frame.observation_year.isin(VALIDATION_YEARS)].copy()
    return train, validation


def _stratified_training_sample(train: pd.DataFrame, rows_per_year: int | None) -> pd.DataFrame:
    """Return a deterministic temporal sample, or the complete training frame."""
    if rows_per_year is None:
        return train
    if rows_per_year < 1:
        raise ValueError("rows_per_year must be positive or None")
    sampled = (
        train.groupby("observation_year", group_keys=False, sort=True)
        .apply(lambda group: group.sample(n=min(rows_per_year, len(group)), random_state=RANDOM_SEED), include_groups=True)
        .sort_values(["observation_year", "cell_id"], kind="mergesort")
        .reset_index(drop=True)
    )
    if tuple(sorted(int(year) for year in sampled.observation_year.unique())) != TRAIN_YEARS:
        raise ValueError("Temporal sample omitted a training year")
    return sampled


def _configuration(name: str) -> dict[str, Any]:
    candidate = CANDIDATES[name]
    # Every candidate is anchored to v1 rather than the active v2 defaults.
    # This keeps the historical comparison stable after model promotion.
    occurrence = dict(V1_OCCURRENCE_PARAMS)
    positive_share = dict(V1_POSITIVE_SHARE_PARAMS)
    occurrence.update(candidate["occurrence"])
    positive_share.update(candidate["positive_share"])
    return {"occurrence": occurrence, "positive_share": positive_share}


def _summary_row(name: str, metrics: dict[str, Any], rankings: dict[str, Any]) -> dict[str, Any]:
    overall = metrics["overall"]
    capture = rankings["overall"]["top_20_percent"]
    return {
        "candidate": name,
        "mae_all": overall["mae_all"],
        "rmse_all": overall["rmse_all"],
        "mae_positive": overall["mae_positive"],
        "rmse_positive": overall["rmse_positive"],
        "positive_cell_capture_at_20_percent": capture["positive_cell_capture"],
        "burned_share_mass_capture_at_20_percent": capture["burned_share_mass_capture"],
    }


def _output_paths(run_name: str) -> tuple[Path, Path, Path]:
    """Keep each experiment run separate rather than overwriting its evidence."""
    if not run_name.replace("_", "").isalnum():
        raise ValueError("run_name may contain only letters, numbers, and underscores")
    run_dir = OUTPUT_DIR / run_name
    return (
        run_dir / "validation_metrics.json",
        run_dir / "validation_predictions.parquet",
        ROOT / f"reports/run_logs/hyperparameter_experiment_{run_name}.md",
    )


def run(
    progress: Callable[[str], None] = print,
    *,
    rows_per_year: int | None = TRAIN_SAMPLE_ROWS_PER_YEAR,
    candidate_names: tuple[str, ...] | None = None,
    run_name: str | None = None,
) -> dict[str, Any]:
    """Fit predeclared candidates and report validation-only comparison.

    The default is a deterministic 15,000-row-per-year screening sample so a
    local experiment remains practical. Passing ``None`` performs a full
    training-frame confirmation for a chosen candidate configuration.
    """
    names = candidate_names or tuple(CANDIDATES)
    unknown = sorted(set(names).difference(CANDIDATES))
    if not names or unknown:
        raise ValueError(f"Unknown or empty candidate selection: {unknown}")
    label = run_name or (
        "full_training_confirmation" if rows_per_year is None
        else f"screening_{rows_per_year}_rows_per_year"
    )
    metrics_path, predictions_path, report_path = _output_paths(label)
    train, validation = _load_development_split()
    sampled_train = _stratified_training_sample(train, rows_per_year)
    X_train = sampled_train.loc[:, PREDICTOR_COLUMNS]
    X_validation = validation.loc[:, PREDICTOR_COLUMNS]
    predictions = validation[["cell_id", "observation_year", "outcome_year", TARGET_COLUMN]].copy()
    candidate_metrics: dict[str, Any] = {}
    summary: list[dict[str, Any]] = []

    for name in names:
        config = _configuration(name)
        model = HurdleHistGradientRegressor(
            random_state=RANDOM_SEED,
            occurrence_params=config["occurrence"],
            positive_share_params=config["positive_share"],
        ).fit(X_train, sampled_train[TARGET_COLUMN])
        values = np.asarray(model.predict(X_validation), dtype="float64")
        if not np.isfinite(values).all() or values.min() < 0.0 or values.max() > 1.0:
            raise ValueError(f"{name} produced invalid burned-share predictions")
        predictions[name] = values
        metrics = evaluate_predictions(validation, values)
        rankings = evaluate_tie_aware_rankings(validation, values)
        candidate_metrics[name] = {
            "description": CANDIDATES[name]["description"],
            "parameters": config,
            "metrics": metrics,
            "ranking_diagnostics": rankings,
        }
        summary.append(_summary_row(name, metrics, rankings))
        progress(f"Validated hyperparameter candidate: {name}")

    archived_full_reference = None
    if ARCHIVED_METRICS_PATH.exists():
        archived = json.loads(ARCHIVED_METRICS_PATH.read_text(encoding="utf-8"))
        archived_full_reference = archived["metrics"]["nine_feature_hurdle"]

    _atomic_parquet(predictions_path, predictions)
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "train_years": list(TRAIN_YEARS),
            "validation_years": list(VALIDATION_YEARS),
            "final_test_years_accessed": [],
            "final_test_rows_read": 0,
            "feature_order": list(PREDICTOR_COLUMNS),
            "random_seed": RANDOM_SEED,
        },
        "row_counts": {
            "train_full": len(train), "train_used_per_candidate": len(sampled_train),
            "training_rows_per_year": rows_per_year, "validation": len(validation),
        },
        "candidates": candidate_metrics,
        "summary": summary,
        "archived_full_training_reference": archived_full_reference,
        "run_name": label,
        "prediction_output": {"path": predictions_path.relative_to(ROOT).as_posix(), "sha256": _sha256(predictions_path)},
        "selection_status": (
            "full-training validation confirmation; selected candidate promotion is recorded separately"
            if rows_per_year is None
            else "screening comparison only; selected candidate promotion is recorded separately"
        ),
    }
    _atomic_json(metrics_path, result)
    write_report(result, report_path)
    return result


def write_report(result: dict[str, Any], report_path: Path) -> None:
    rows = sorted(result["summary"], key=lambda item: (item["mae_all"], -item["burned_share_mass_capture_at_20_percent"]))
    training_description = (
        "the complete T=2010-2019 training set"
        if result["row_counts"]["training_rows_per_year"] is None
        else "a deterministic temporal sample from T=2010-2019"
    )
    lines = [
        "# Validation-only hyperparameter experiment",
        "",
        f"This predeclared comparison fits {training_description} and evaluates the full T=2020-2021 validation set. It did not open final-test years T=2022-2024. The model-version decision is documented separately after this evidence is reviewed.",
        "",
        "| Candidate | All-row MAE | All-row RMSE | Positive-row MAE | Positive-cell capture@20% | Burned-share mass capture@20% |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['candidate']} | {row['mae_all']:.8f} | {row['rmse_all']:.8f} | {row['mae_positive']:.8f} | {row['positive_cell_capture_at_20_percent']:.4f} | {row['burned_share_mass_capture_at_20_percent']:.4f} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "Results are a validation comparison, not proof of a globally best model. All candidates use the same training rows, so they may be compared with each other. A candidate does not replace the frozen operational model without a separately approved model-version decision and a later untouched temporal evaluation.",
    ])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
