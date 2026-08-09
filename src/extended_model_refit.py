"""Refit the frozen nine-feature candidate on the extended training period.

This module deliberately operates only on T=2010-2021. T=2022-2024 are
neither present in its input panel nor read from the canonical national panel.
The validated extended panel already contains the single nine-predictor
contract, including all five T-only ERA5-Land climate summaries.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from src import national_panel as panel
from src.evaluation import evaluate_predictions, evaluate_tie_aware_rankings
from src.extended_training_panel import (
    PANEL_PATH as EXTENDED_PANEL_PATH,
)
from src.feature_contract import FIELD_CONTRACTS, PREDICTOR_COLUMNS, TARGET_COLUMN
from src.modeling import (
    MODEL_SPECIFICATION_VERSION,
    HistoricalFireMeanRegressor,
    HurdleHistGradientRegressor,
    RANDOM_SEED,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data/processed/extended_model_selection_2010_2021"
FEATURE_MATRIX_PATH = OUTPUT_DIR / "nine_feature_train_validation_matrix.parquet"
MODEL_DIR = OUTPUT_DIR / "models"
PREDICTIONS_PATH = OUTPUT_DIR / "validation_predictions.parquet"
METRICS_PATH = OUTPUT_DIR / "metrics.json"
REPORT_PATH = ROOT / "reports/validation/extended_training_model_refit.md"

TRAIN_YEARS = tuple(range(2010, 2020))
VALIDATION_YEARS = (2020, 2021)
ALLOWED_YEARS = TRAIN_YEARS + VALIDATION_YEARS


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _prediction_sha256(values: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(values, dtype="<f8").tobytes()).hexdigest().upper()


def _validate_frame(frame: pd.DataFrame) -> None:
    if tuple(sorted(int(value) for value in frame.observation_year.unique())) != ALLOWED_YEARS:
        raise ValueError("Extended model frame does not contain precisely T=2010-2021")
    if frame.observation_year.isin((2022, 2023, 2024)).any():
        raise ValueError("Final-test year entered extended model frame")
    if frame.duplicated(["cell_id", "observation_year"]).any():
        raise ValueError("Duplicate extended model analytical key")
    required = list(PREDICTOR_COLUMNS) + [TARGET_COLUMN]
    if frame[required].isna().any().any() or not np.isfinite(frame[required].to_numpy(dtype="float64")).all():
        raise ValueError("Extended model frame contains non-finite values")
    for column in PREDICTOR_COLUMNS:
        contract = FIELD_CONTRACTS[column]
        values = frame[column].to_numpy(dtype="float64")
        if values.min() < contract.minimum or values.max() > contract.maximum:
            raise ValueError(f"{column} violates its model feature range")
    if not frame.outcome_year.eq(frame.observation_year + 1).all():
        raise ValueError("Outcome year is not T+1")
    if not frame.climate_reference_year.eq(frame.observation_year).all():
        raise ValueError("Climate reference year is not T")
    if not frame.historical_fire_start_year.eq(frame.observation_year - 10).all():
        raise ValueError("Historical fire start year is not T-10")
    if not frame.historical_fire_end_year.eq(frame.observation_year - 1).all():
        raise ValueError("Historical fire end year is not T-1")


def build_extended_nine_feature_matrix(progress: Callable[[str], None] = print) -> dict[str, object]:
    """Create a reproducible T=2010-2021-only nine-feature matrix."""
    if FEATURE_MATRIX_PATH.exists():
        existing = pd.read_parquet(FEATURE_MATRIX_PATH)
        _validate_frame(existing)
        return {
            "path": FEATURE_MATRIX_PATH.relative_to(ROOT).as_posix(),
            "sha256": _sha256(FEATURE_MATRIX_PATH),
            "row_count": len(existing),
            "train_rows": int(existing.observation_year.isin(TRAIN_YEARS).sum()),
            "validation_rows": int(existing.observation_year.isin(VALIDATION_YEARS).sum()),
            "feature_order": list(PREDICTOR_COLUMNS),
            "final_test_rows_read": 0,
            "status": "validated_reused",
        }
    base = pd.read_parquet(EXTENDED_PANEL_PATH)
    base = base.loc[base.observation_year.isin(ALLOWED_YEARS)].copy()
    result = base.sort_values(
        ["observation_year", "cell_id"], kind="mergesort"
    ).reset_index(drop=True)
    _validate_frame(result)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporary = FEATURE_MATRIX_PATH.with_suffix(".parquet.tmp")
    result.to_parquet(temporary, index=False, compression="zstd")
    os.replace(temporary, FEATURE_MATRIX_PATH)
    return {
        "path": FEATURE_MATRIX_PATH.relative_to(ROOT).as_posix(),
        "sha256": _sha256(FEATURE_MATRIX_PATH),
        "row_count": len(result),
        "train_rows": int(result.observation_year.isin(TRAIN_YEARS).sum()),
        "validation_rows": int(result.observation_year.isin(VALIDATION_YEARS).sum()),
        "feature_order": list(PREDICTOR_COLUMNS),
        "final_test_rows_read": 0,
    }


def _save_model(name: str, model: Any, predictions: np.ndarray) -> dict[str, object]:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    path = MODEL_DIR / f"{name}.joblib"
    payload = {
        "model": model,
        "model_name": name,
        "feature_order": list(PREDICTOR_COLUMNS),
        "train_years": list(TRAIN_YEARS),
        "validation_years": list(VALIDATION_YEARS),
        "random_seed": RANDOM_SEED,
        "temporal_rule": "predictors are T-only; target is T+1; final-test rows are absent",
    }
    if isinstance(model, HurdleHistGradientRegressor):
        payload["model_specification_version"] = MODEL_SPECIFICATION_VERSION
        payload["parameters"] = model.parameter_config()
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary model output requires inspection: {temporary}")
    joblib.dump(payload, temporary)
    os.replace(temporary, path)
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": _sha256(path), "prediction_sha256": _prediction_sha256(predictions)}


def refit_extended_models() -> dict[str, object]:
    """Fit the v2 historical baseline and nine-feature two-part model, then validate only T=2020-2021."""
    if not FEATURE_MATRIX_PATH.exists():
        raise FileNotFoundError("Build the extended nine-feature matrix first")
    frame = pd.read_parquet(FEATURE_MATRIX_PATH)
    _validate_frame(frame)
    train = frame.loc[frame.observation_year.isin(TRAIN_YEARS)].copy()
    validation = frame.loc[frame.observation_year.isin(VALIDATION_YEARS)].copy()
    if len(train) != 89112 * len(TRAIN_YEARS) or len(validation) != 89112 * len(VALIDATION_YEARS):
        raise ValueError("Unexpected extended split row count")
    X_train, X_validation = train.loc[:, PREDICTOR_COLUMNS], validation.loc[:, PREDICTOR_COLUMNS]
    historical = HistoricalFireMeanRegressor().fit(X_train, train[TARGET_COLUMN])
    historical_predictions = np.clip(historical.predict(X_validation), 0.0, 1.0)
    hurdle = HurdleHistGradientRegressor()
    with threadpool_limits(limits=1, user_api="openmp"):
        hurdle.fit(X_train, train[TARGET_COLUMN])
    hurdle_predictions = hurdle.predict(X_validation)

    # Reloads test reproducibility of the emitted, reusable artefact rather
    # than claiming byte-level determinism across library/platform versions.
    historical_artifact = _save_model("historical_recurrence_baseline", historical, historical_predictions)
    hurdle_artifact = _save_model("nine_feature_hurdle", hurdle, hurdle_predictions)
    reloaded_historical = joblib.load(ROOT / historical_artifact["path"])["model"].predict(X_validation)
    reloaded_hurdle = joblib.load(ROOT / hurdle_artifact["path"])["model"].predict(X_validation)
    if not np.array_equal(historical_predictions, reloaded_historical):
        raise ValueError("Reloaded historical baseline predictions differ")
    if not np.array_equal(hurdle_predictions, reloaded_hurdle):
        raise ValueError("Reloaded nine-feature hurdle predictions differ")

    prediction_sets = {
        "historical_recurrence_baseline": historical_predictions,
        "nine_feature_hurdle": hurdle_predictions,
    }
    predictions = validation[["cell_id", "observation_year", TARGET_COLUMN]].copy()
    for name, values in prediction_sets.items():
        predictions[name] = values
    temporary_predictions = PREDICTIONS_PATH.with_suffix(".parquet.tmp")
    predictions.to_parquet(temporary_predictions, index=False, compression="zstd")
    os.replace(temporary_predictions, PREDICTIONS_PATH)
    metrics = {name: evaluate_predictions(validation, values) for name, values in prediction_sets.items()}
    rankings = {name: evaluate_tie_aware_rankings(validation, values) for name, values in prediction_sets.items()}
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "design": {
            "train_years": list(TRAIN_YEARS), "validation_years": list(VALIDATION_YEARS),
            "final_test_years_accessed": [], "final_test_rows_read": 0,
            "feature_order": list(PREDICTOR_COLUMNS), "target": TARGET_COLUMN,
        },
        "row_counts": {"train": len(train), "validation": len(validation)},
        "models": {
            "historical_recurrence_baseline": {"definition": "training-period empirical mean target by prior-ten-year recurrence count", "artifact": historical_artifact},
            "nine_feature_hurdle": {"definition": "P(next-year burned share > 0) times conditional expected positive burned share", "artifact": hurdle_artifact,
                                    "model_specification_version": MODEL_SPECIFICATION_VERSION,
                                    "parameters": hurdle.parameter_config()},
        },
        "metrics": metrics,
        "tie_aware_ranking_diagnostics": rankings,
        "prediction_output": {"path": PREDICTIONS_PATH.relative_to(ROOT).as_posix(), "sha256": _sha256(PREDICTIONS_PATH)},
        "reproducibility": {"seed": RANDOM_SEED, "saved_model_reload_predictions_identical": True},
    }
    temporary_metrics = METRICS_PATH.with_suffix(".json.tmp")
    temporary_metrics.write_text(json.dumps(result, indent=2), encoding="utf-8")
    os.replace(temporary_metrics, METRICS_PATH)
    return result


def write_report(result: dict[str, object]) -> None:
    metrics = result["metrics"]
    lines = [
        "# Model v2 training-only refit",
        "",
        "This controlled refit uses Model v2, selected from the complete T=2020-2021 validation comparison. It fits T=2010-2019 and validates T=2020-2021. T=2022-2024 were not opened or used.",
        "",
        "## Candidate comparison",
        "",
        "| Model | Validation MAE | Validation RMSE | Positive-row MAE | Positive-cell capture at 20% | Burned-share mass capture at 20% |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, label in (("historical_recurrence_baseline", "Historical recurrence baseline"), ("nine_feature_hurdle", "Nine-feature two-part regression")):
        overall = metrics[name]["overall"]
        rank = result["tie_aware_ranking_diagnostics"][name]["overall"]["top_20_percent"]
        lines.append(
            f"| {label} | {overall['mae_all']:.8f} | {overall['rmse_all']:.8f} | {overall['mae_positive']:.8f} | {rank['positive_cell_capture']:.4f} | {rank['burned_share_mass_capture']:.4f} |"
        )
    lines.extend([
        "",
        "## Validation by year",
        "",
        "| Validation T | Model | MAE | RMSE | Positive-row MAE | Positive-cell capture at 20% |",
        "|---:|---|---:|---:|---:|---:|",
    ])
    for year in VALIDATION_YEARS:
        for name, label in (("historical_recurrence_baseline", "Historical recurrence baseline"), ("nine_feature_hurdle", "Nine-feature two-part regression")):
            current = metrics[name]["by_validation_year"][str(year)]
            lines.append(
                f"| {year} | {label} | {current['mae_all']:.8f} | {current['rmse_all']:.8f} | {current['mae_positive']:.8f} | {current['capture_at_20_percent']:.4f} |"
            )
    lines.extend([
        "",
        "## Guardrails",
        "",
        "- The historical baseline is a training-only empirical mapping from the strict T-10 through T-1 recurrence count to expected next-year burned share.",
        "- The two-part regression output is a continuous expected burned share, not a buyer-facing probability or decision threshold.",
        "- This report is validation evidence only; it contains no final-temporal-test result.",
    ])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(progress: Callable[[str], None] = print) -> dict[str, object]:
    started = time.perf_counter()
    matrix = build_extended_nine_feature_matrix(progress)
    progress(f"Extended nine-feature matrix: {matrix['row_count']:,} rows")
    result = refit_extended_models()
    result["feature_matrix"] = matrix
    result["runtime_seconds"] = round(time.perf_counter() - started, 3)
    temporary_metrics = METRICS_PATH.with_suffix(".json.tmp")
    temporary_metrics.write_text(json.dumps(result, indent=2), encoding="utf-8")
    os.replace(temporary_metrics, METRICS_PATH)
    write_report(result)
    return result
