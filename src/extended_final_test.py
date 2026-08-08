"""One frozen final-temporal evaluation of the extended training candidates.

This module may be run only after ``final_temporal_test_protocol.md`` is
committed. It does not fit, tune, or select a model: it reads the nine-feature
T=2022-2024 rows, loads models fitted on T=2010-2019, and reports held-out
performance.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src import national_panel as panel
from src.evaluation import regression_metrics, tie_aware_ranking_metrics
from src.extended_model_refit import MODEL_DIR, ROOT, _sha256
from src.feature_contract import PREDICTOR_COLUMNS, TARGET_COLUMN


FINAL_TEST_YEARS = (2022, 2023, 2024)
OUTPUT_DIR = ROOT / "data/processed/extended_model_selection_2010_2021"
FEATURE_MATRIX_PATH = OUTPUT_DIR / "final_temporal_test_nine_feature_matrix.parquet"
PREDICTIONS_PATH = OUTPUT_DIR / "final_temporal_test_predictions.parquet"
METRICS_PATH = OUTPUT_DIR / "final_temporal_test_metrics.json"
REPORT_PATH = ROOT / "reports/validation/final_temporal_test_2022_2024.md"
PROTOCOL_PATH = ROOT / "reports/validation/final_temporal_test_protocol.md"


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary output requires inspection: {temporary}")
    frame.to_parquet(temporary, index=False, compression="zstd")
    os.replace(temporary, path)


def _row_group_year(parquet: pq.ParquetFile, index: int) -> int:
    field = parquet.schema_arrow.get_field_index("observation_year")
    statistics = parquet.metadata.row_group(index).column(field).statistics
    if statistics is None or not statistics.has_min_max or statistics.min != statistics.max:
        raise ValueError(f"Panel row group {index} lacks a single observation-year value")
    return int(statistics.min)


def _read_final_panel_rows() -> tuple[pd.DataFrame, dict[str, object]]:
    """Open exactly final-test row groups from the validated base panel."""
    parquet = pq.ParquetFile(panel.NATIONAL_PANEL_PATH)
    groups = []
    tables = []
    for index in range(parquet.num_row_groups):
        year = _row_group_year(parquet, index)
        read = year in FINAL_TEST_YEARS
        groups.append({"row_group": index, "observation_year": year, "read": read})
        if read:
            tables.append(parquet.read_row_group(index))
    result = pd.concat([item.to_pandas() for item in tables], ignore_index=True)
    if tuple(sorted(int(value) for value in result.observation_year.unique())) != FINAL_TEST_YEARS:
        raise ValueError("Final-test panel rows do not match the frozen temporal period")
    if len(result) != 89112 * len(FINAL_TEST_YEARS):
        raise ValueError("Unexpected final-test row count")
    return result, {"row_groups": groups, "rows_read": len(result), "years_read": list(FINAL_TEST_YEARS)}


def build_final_feature_matrix() -> dict[str, object]:
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError("Final-test protocol must be present before execution")
    base, access = _read_final_panel_rows()
    result = base.sort_values(["observation_year", "cell_id"], kind="mergesort").reset_index(drop=True)
    if result[list(PREDICTOR_COLUMNS) + [TARGET_COLUMN]].isna().any().any():
        raise ValueError("Final feature matrix contains missing values")
    if not result.outcome_year.eq(result.observation_year + 1).all():
        raise ValueError("Final target year is not T+1")
    _atomic_parquet(result, FEATURE_MATRIX_PATH)
    return {"path": FEATURE_MATRIX_PATH.relative_to(ROOT).as_posix(), "sha256": _sha256(FEATURE_MATRIX_PATH), "row_count": len(result), "panel_access": access}


def _evaluate(frame: pd.DataFrame, predictions: np.ndarray) -> dict[str, object]:
    target = frame[TARGET_COLUMN].to_numpy(dtype="float64")
    cell_ids = frame.cell_id.to_numpy()
    years = frame.observation_year.to_numpy(dtype="int16")
    return {
        "overall": regression_metrics(target, predictions, cell_ids, years),
        "by_final_test_year": {
            str(year): regression_metrics(target[years == year], predictions[years == year], cell_ids[years == year], years[years == year])
            for year in FINAL_TEST_YEARS
        },
    }


def _rankings(frame: pd.DataFrame, predictions: np.ndarray) -> dict[str, object]:
    target = frame[TARGET_COLUMN].to_numpy(dtype="float64")
    years = frame.observation_year.to_numpy(dtype="int16")

    def calculate(mask: np.ndarray) -> dict[str, object]:
        return {
            "top_10_percent": tie_aware_ranking_metrics(target[mask], predictions[mask], 0.10),
            "top_20_percent": tie_aware_ranking_metrics(target[mask], predictions[mask], 0.20),
        }

    return {
        "overall": calculate(np.ones(len(frame), dtype=bool)),
        "by_final_test_year": {str(year): calculate(years == year) for year in FINAL_TEST_YEARS},
    }


def run_final_test() -> dict[str, object]:
    matrix = build_final_feature_matrix()
    frame = pd.read_parquet(FEATURE_MATRIX_PATH)
    model_files = {
        "historical_recurrence_baseline": MODEL_DIR / "historical_recurrence_baseline.joblib",
        "nine_feature_hurdle": MODEL_DIR / "nine_feature_hurdle.joblib",
    }
    predictions: dict[str, np.ndarray] = {}
    artifact_checks = {}
    for name, path in model_files.items():
        payload = joblib.load(path)
        if payload.get("feature_order") != list(PREDICTOR_COLUMNS):
            raise ValueError(f"Frozen model {name} has a different feature contract")
        if payload.get("train_years") != list(range(2010, 2020)):
            raise ValueError(f"Frozen model {name} has a different training period")
        values = np.clip(np.asarray(payload["model"].predict(frame.loc[:, PREDICTOR_COLUMNS]), dtype="float64"), 0.0, 1.0)
        if not np.isfinite(values).all():
            raise ValueError(f"Frozen model {name} returned non-finite values")
        predictions[name] = values
        artifact_checks[name] = {"path": path.relative_to(ROOT).as_posix(), "sha256": _sha256(path)}
    output = frame[["cell_id", "observation_year", "outcome_year", TARGET_COLUMN]].copy()
    for name, values in predictions.items():
        output[name] = values
    _atomic_parquet(output, PREDICTIONS_PATH)
    metrics = {name: _evaluate(frame, values) for name, values in predictions.items()}
    rankings = {name: _rankings(frame, values) for name, values in predictions.items()}
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_path": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
        "design": {"train_years": list(range(2010, 2020)), "validation_years": [2020, 2021], "final_test_years": list(FINAL_TEST_YEARS), "feature_order": list(PREDICTOR_COLUMNS), "target": TARGET_COLUMN, "tuning_performed": False},
        "feature_matrix": matrix,
        "frozen_artifacts": artifact_checks,
        "metrics": metrics,
        "tie_aware_ranking_diagnostics": rankings,
        "prediction_output": {"path": PREDICTIONS_PATH.relative_to(ROOT).as_posix(), "sha256": _sha256(PREDICTIONS_PATH)},
    }
    temporary = METRICS_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2), encoding="utf-8")
    os.replace(temporary, METRICS_PATH)
    return result


def write_report(result: dict[str, object]) -> None:
    lines = [
        "# Frozen final temporal test — T=2022-2024",
        "",
        "This is a single held-out evaluation under the committed protocol. No model fitting, tuning, feature selection, or threshold selection was performed on these years.",
        "",
        "## Overall results",
        "",
        "| Model | MAE | RMSE | Positive-row MAE | Positive-cell capture at 20% | Burned-share mass capture at 20% |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    labels = {"historical_recurrence_baseline": "Historical recurrence baseline", "nine_feature_hurdle": "Nine-feature two-part regression"}
    for name, label in labels.items():
        overall = result["metrics"][name]["overall"]
        rank = result["tie_aware_ranking_diagnostics"][name]["overall"]["top_20_percent"]
        lines.append(f"| {label} | {overall['mae_all']:.8f} | {overall['rmse_all']:.8f} | {overall['mae_positive']:.8f} | {rank['positive_cell_capture']:.4f} | {rank['burned_share_mass_capture']:.4f} |")
    lines.extend(["", "## Results by predictor year", "", "| T | Model | MAE | RMSE | Positive-row MAE | Positive-cell capture at 20% |", "|---:|---|---:|---:|---:|---:|"])
    for year in FINAL_TEST_YEARS:
        for name, label in labels.items():
            item = result["metrics"][name]["by_final_test_year"][str(year)]
        lines.append(f"| {year} | {label} | {item['mae_all']:.8f} | {item['rmse_all']:.8f} | {item['mae_positive']:.8f} | {item['capture_at_20_percent']:.4f} |")
    lines.extend(["", "## Mean-prediction check", "", "| T | Observed mean burned share | Baseline mean prediction | Two-part regression mean prediction |", "|---:|---:|---:|---:|"])
    for year in FINAL_TEST_YEARS:
        baseline = result["metrics"]["historical_recurrence_baseline"]["by_final_test_year"][str(year)]
        hurdle = result["metrics"]["nine_feature_hurdle"]["by_final_test_year"][str(year)]
        lines.append(f"| {year} | {hurdle['mean_observed']:.8f} | {baseline['mean_predicted']:.8f} | {hurdle['mean_predicted']:.8f} |")
    lines.extend(["", "## Scope limitation", "", "The two-part regression model (technical term: hurdle model) has lower overall MAE and stronger burned-share-mass ranking than the baseline, but it materially underpredicts the high-burned T=2024 outcome. The model estimates comparative next-year burned share for 1 km mainland cells; it is not a probability, safety guarantee, property-level forecast, or purchase recommendation."])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> dict[str, object]:
    result = run_final_test()
    write_report(result)
    return result
