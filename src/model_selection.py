"""Deterministic train/validation-only regression model selection.

The loader deliberately opens only Parquet row groups whose metadata proves that
they belong to the canonical training or validation years. Final-test row groups
are never read by this module.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pyarrow
import pyarrow.parquet as pq
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import TweedieRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config import CLC
from src.feature_contract import FIELD_CONTRACTS, PREDICTOR_COLUMNS, TARGET_COLUMN


PANEL_PATH = Path("data/processed/national_panel_2015_2024.parquet")
PANEL_VALIDATION_PATH = Path("data/processed/national_panel_2015_2024_validation.json")
OUTPUT_DIR = Path("data/processed/model_selection_2015_2021")
MODEL_DIR = OUTPUT_DIR / "models"
PREDICTIONS_PATH = OUTPUT_DIR / "validation_predictions.parquet"
ARTIFACT_METADATA_PATH = OUTPUT_DIR / "artifact_metadata.json"
METRICS_PATH = Path("reports/validation/train_validation_model_selection.json")
REPORT_PATH = Path("reports/validation/train_validation_model_selection.md")

TRAIN_YEARS = (2015, 2016, 2017, 2018, 2019)
VALIDATION_YEARS = (2020, 2021)
FINAL_TEST_YEARS = (2022, 2023, 2024)
MODEL_SELECTION_YEARS = TRAIN_YEARS + VALIDATION_YEARS
RANDOM_SEED = 20260805
MODEL_CONTRACT_VERSION = "train-validation-regression-v1"
MEANINGFUL_IMPROVEMENT_FRACTION = 0.02

READ_COLUMNS = (
    "cell_id",
    "observation_year",
    "outcome_year",
    "historical_fire_start_year",
    "historical_fire_end_year",
    "climate_reference_year",
    "land_cover_reference_year",
) + PREDICTOR_COLUMNS + (TARGET_COLUMN,)


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _prediction_sha256(values: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(values, dtype="<f8")
    return hashlib.sha256(contiguous.tobytes()).hexdigest().upper()


def _row_group_year(parquet_file: pq.ParquetFile, row_group_index: int) -> int:
    column_index = parquet_file.schema_arrow.get_field_index("observation_year")
    statistics = parquet_file.metadata.row_group(row_group_index).column(column_index).statistics
    if statistics is None or not statistics.has_min_max or statistics.min != statistics.max:
        raise ValueError(f"Row group {row_group_index} lacks a single-year observation_year statistic")
    return int(statistics.min)


def read_train_validation_rows(
    panel_path: Path = PANEL_PATH,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Read only train/validation row groups and audit every unopened group."""
    parquet_file = pq.ParquetFile(panel_path)
    available = set(parquet_file.schema_arrow.names)
    missing = sorted(set(READ_COLUMNS) - available)
    if missing:
        raise ValueError(f"Canonical panel is missing model-selection columns: {missing}")

    tables = []
    row_group_audit = []
    for index in range(parquet_file.num_row_groups):
        year = _row_group_year(parquet_file, index)
        rows = parquet_file.metadata.row_group(index).num_rows
        should_read = year in MODEL_SELECTION_YEARS
        if year not in MODEL_SELECTION_YEARS + FINAL_TEST_YEARS:
            raise ValueError(f"Unexpected observation year {year} in row group {index}")
        row_group_audit.append(
            {"row_group": index, "observation_year": year, "rows": rows, "read": should_read}
        )
        if should_read:
            tables.append(parquet_file.read_row_group(index, columns=list(READ_COLUMNS)))

    if not tables:
        raise ValueError("No training/validation row groups were read")
    frame = pyarrow.concat_tables(tables).to_pandas()
    read_years = tuple(sorted(int(value) for value in frame.observation_year.unique()))
    if read_years != MODEL_SELECTION_YEARS:
        raise ValueError(f"Read years {read_years} do not match {MODEL_SELECTION_YEARS}")
    if frame.observation_year.isin(FINAL_TEST_YEARS).any():
        raise ValueError("Final-test rows entered model-selection memory")

    audit = {
        "row_groups": row_group_audit,
        "read_row_groups": [item["row_group"] for item in row_group_audit if item["read"]],
        "unopened_final_test_row_groups": [
            item["row_group"]
            for item in row_group_audit
            if item["observation_year"] in FINAL_TEST_YEARS and not item["read"]
        ],
        "final_test_rows_read": 0,
    }
    return frame, audit


def validate_model_selection_frame(frame: pd.DataFrame) -> dict[str, Any]:
    """Validate split, contract, temporal alignment, and leakage controls."""
    if frame.duplicated(["cell_id", "observation_year"]).any():
        raise ValueError("Duplicate cell_id x observation_year keys")
    if frame[list(PREDICTOR_COLUMNS) + [TARGET_COLUMN]].isna().any().any():
        raise ValueError("Missing predictors or target are forbidden for model selection")
    if tuple(frame.columns[-8:-1]) != PREDICTOR_COLUMNS:
        raise ValueError("Canonical predictor order was not preserved while reading the panel")

    expected_outcome = frame.observation_year + 1
    if not frame.outcome_year.eq(expected_outcome).all():
        raise ValueError("Outcome year is not T+1")
    if not frame.climate_reference_year.eq(frame.observation_year).all():
        raise ValueError("Climate reference year is not T")
    if not frame.historical_fire_start_year.eq(frame.observation_year - 10).all():
        raise ValueError("Historical-fire start year is not T-10")
    if not frame.historical_fire_end_year.eq(frame.observation_year - 1).all():
        raise ValueError("Historical-fire end year is not T-1")
    expected_clc = frame.observation_year.map(CLC.reference_year)
    if not frame.land_cover_reference_year.eq(expected_clc).all():
        raise ValueError("CLC assignment does not match the governed reference year")

    for name in PREDICTOR_COLUMNS + (TARGET_COLUMN,):
        contract = FIELD_CONTRACTS[name]
        if contract.missing_rule != "forbidden":
            raise ValueError(f"Canonical model contract still permits missing values in {name}")
        values = frame[name].to_numpy(dtype=np.float64)
        if not np.isfinite(values).all():
            raise ValueError(f"Non-finite values in {name}")
        if contract.minimum is not None and float(values.min()) < contract.minimum - 1e-9:
            raise ValueError(f"{name} is below its contract minimum")
        if contract.maximum is not None and float(values.max()) > contract.maximum + 1e-9:
            raise ValueError(f"{name} is above its contract maximum")

    counts = frame.groupby("observation_year", sort=True).size().to_dict()
    if len(set(counts.values())) != 1:
        raise ValueError("Train/validation years have unequal canonical cell counts")
    train_count = int(frame.observation_year.isin(TRAIN_YEARS).sum())
    validation_count = int(frame.observation_year.isin(VALIDATION_YEARS).sum())
    return {
        "train_rows": train_count,
        "validation_rows": validation_count,
        "rows_by_year": {str(int(year)): int(count) for year, count in counts.items()},
        "duplicate_keys": 0,
        "missing_predictor_values": 0,
        "final_test_rows_in_memory": 0,
        "feature_order": list(PREDICTOR_COLUMNS),
        "target": TARGET_COLUMN,
    }


def capture_at_20_percent(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    cell_ids: np.ndarray,
    years: np.ndarray,
) -> float:
    """Fraction of positive-target rows within the deterministic top prediction quintile."""
    positive = y_true > 0.0
    positive_count = int(positive.sum())
    if positive_count == 0:
        return float("nan")
    top_count = int(math.ceil(0.20 * len(y_true)))
    ranking = pd.DataFrame(
        {"prediction": y_pred, "cell_id": cell_ids.astype(str), "year": years, "positive": positive}
    ).sort_values(
        ["prediction", "cell_id", "year"],
        ascending=[False, True, True],
        kind="mergesort",
    )
    return float(ranking.iloc[:top_count].positive.sum() / positive_count)


def regression_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    cell_ids: np.ndarray,
    years: np.ndarray,
) -> dict[str, float | int]:
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
        "capture_at_20_percent": capture_at_20_percent(y_true, y_pred, cell_ids, years),
        "prediction_min": float(np.min(y_pred)),
        "prediction_max": float(np.max(y_pred)),
    }


def evaluate_predictions(validation: pd.DataFrame, predictions: np.ndarray) -> dict[str, Any]:
    y_true = validation[TARGET_COLUMN].to_numpy(dtype=np.float64)
    cell_ids = validation.cell_id.to_numpy()
    years = validation.observation_year.to_numpy(dtype=np.int16)
    by_year = {}
    for year in VALIDATION_YEARS:
        mask = years == year
        by_year[str(year)] = regression_metrics(
            y_true[mask], predictions[mask], cell_ids[mask], years[mask]
        )
    return {
        "overall": regression_metrics(y_true, predictions, cell_ids, years),
        "by_validation_year": by_year,
    }


def _candidate_specs() -> dict[str, dict[str, Any]]:
    return {
        "random_forest_regressor": {
            "n_estimators": 60,
            "max_depth": 14,
            "min_samples_leaf": 20,
            "max_features": 0.8,
            "bootstrap": True,
            "random_state": RANDOM_SEED,
            "n_jobs": 1,
        },
        "tweedie_regressor": {
            "power": 1.5,
            "alpha": 0.1,
            "link": "log",
            "max_iter": 500,
            "tol": 1e-7,
        },
    }


def _make_candidate(name: str, specs: dict[str, dict[str, Any]]) -> Any:
    if name == "random_forest_regressor":
        return RandomForestRegressor(**specs[name])
    if name == "tweedie_regressor":
        return Pipeline(
            [
                ("standardize", StandardScaler()),
                ("regressor", TweedieRegressor(**specs[name])),
            ]
        )
    raise KeyError(name)


def _selection_decision(metrics: dict[str, Any]) -> dict[str, Any]:
    baseline = metrics["historical_fire_baseline"]["overall"]
    qualifying = []
    evidence = {}
    for name in ("random_forest_regressor", "tweedie_regressor"):
        candidate = metrics[name]["overall"]
        mae_improvement = 1.0 - candidate["mae_all"] / baseline["mae_all"]
        rmse_improvement = 1.0 - candidate["rmse_all"] / baseline["rmse_all"]
        capture_not_lower = candidate["capture_at_20_percent"] >= baseline["capture_at_20_percent"]
        passes = (
            mae_improvement >= MEANINGFUL_IMPROVEMENT_FRACTION
            and rmse_improvement >= MEANINGFUL_IMPROVEMENT_FRACTION
            and capture_not_lower
        )
        evidence[name] = {
            "relative_mae_improvement": float(mae_improvement),
            "relative_rmse_improvement": float(rmse_improvement),
            "capture_not_lower_than_historical_baseline": bool(capture_not_lower),
            "passes_predeclared_gate": bool(passes),
        }
        if passes:
            qualifying.append(name)
    selected = min(qualifying, key=lambda item: metrics[item]["overall"]["rmse_all"]) if qualifying else None
    return {
        "predeclared_rule": (
            "At least 2% lower validation MAE and RMSE than the historical-fire baseline, "
            "with capture@20% no lower; choose the qualifying candidate with lowest RMSE."
        ),
        "candidate_evidence": evidence,
        "provisional_model": selected,
        "final_temporal_test_may_begin": selected is not None,
    }


def _save_and_verify_model(
    name: str,
    model: Any,
    validation_features: pd.DataFrame,
    expected_predictions: np.ndarray,
) -> dict[str, Any]:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    path = MODEL_DIR / f"{name}.joblib"
    joblib.dump(model, path)
    loaded = joblib.load(path)
    reloaded_predictions = loaded.predict(validation_features)
    identical = np.array_equal(expected_predictions, reloaded_predictions)
    if not identical:
        raise ValueError(f"Reloaded {name} predictions are not byte-identical")
    return {
        "path": path.as_posix(),
        "sha256": _sha256(path),
        "reload_predictions_identical": True,
        "prediction_sha256": _prediction_sha256(expected_predictions),
    }


def _format_metric(value: float) -> str:
    return f"{value:.8f}"


def _write_report(result: dict[str, Any]) -> None:
    model_labels = {
        "zero_prediction_baseline": "Zero reference",
        "historical_fire_baseline": "Historical-fire baseline",
        "random_forest_regressor": "Random Forest",
        "tweedie_regressor": "Tweedie (power 1.5)",
    }
    rows = []
    for name, label in model_labels.items():
        metric = result["metrics"][name]["overall"]
        rows.append(
            f"| {label} | {_format_metric(metric['mae_all'])} | {_format_metric(metric['rmse_all'])} | "
            f"{_format_metric(metric['mae_positive'])} | {_format_metric(metric['rmse_positive'])} | "
            f"{_format_metric(metric['mean_predicted'])} | {_format_metric(metric['mean_observed'])} | "
            f"{metric['capture_at_20_percent']:.2%} |"
        )
    year_rows = []
    for year in VALIDATION_YEARS:
        for name, label in model_labels.items():
            metric = result["metrics"][name]["by_validation_year"][str(year)]
            year_rows.append(
                f"| {year} | {label} | {_format_metric(metric['mae_all'])} | "
                f"{_format_metric(metric['rmse_all'])} | {_format_metric(metric['mae_positive'])} | "
                f"{_format_metric(metric['rmse_positive'])} | {metric['capture_at_20_percent']:.2%} |"
            )

    selected = result["selection"]["provisional_model"]
    if selected:
        decision = (
            f"**Provisional model selected: `{selected}`.** It passed the predeclared "
            "validation-only gate. The final temporal test may begin in a separate, frozen evaluation task."
        )
    else:
        decision = (
            "**No candidate passed the predeclared validation gate.** Final temporal testing must not begin "
            "until the model design is reconsidered without consulting final-test outcomes."
        )

    content = f"""# Train/validation regression model selection

{decision}

No records from final-test years `T=2022-2024` were opened, fitted, tuned, scored, or reported. This report covers training `T=2015-2019` and validation `T=2020-2021` only.

## Data and guardrails

- Canonical panel: `{result['panel']['path']}`; validated SHA-256 `{result['panel']['validated_sha256']}`.
- Training rows: {result['contract_validation']['train_rows']:,}.
- Validation rows: {result['contract_validation']['validation_rows']:,}.
- Features, in recorded order: {', '.join(f'`{name}`' for name in PREDICTOR_COLUMNS)}.
- Target: `{TARGET_COLUMN}`; model output: `predicted_burned_share_next_year`, never a probability.
- Final-test rows read: 0; unopened final-test row groups: {result['row_group_access']['unopened_final_test_row_groups']}.
- Climate missingness is forbidden after the validated coastal fallback; train/validation missing predictor values: 0.

## Intentionally limited models

- Zero prediction: reference error only, not an acceptable model.
- Historical-fire baseline: training-period empirical mean target for each integer `fire_years_previous_10y_2km` value.
- Random Forest: 60 trees, depth 14, minimum leaf 20, 80% features per split, seed {RANDOM_SEED}.
- Tweedie: power 1.5, log link, alpha 0.1; seven predictors standardized using training-fitted parameters only.

No broad hyperparameter search was performed. Physically valid predictor values, including precipitation outside the training distribution, were neither clipped nor removed.

## Overall validation metrics

| Model | MAE all | RMSE all | MAE positive | RMSE positive | Mean predicted | Mean observed | Positive-cell capture@20% |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

Capture@20% is the fraction of rows with target greater than zero found within the highest-ranked 20% of regression predictions; ties use stable `cell_id`, then year ordering.

## Metrics by validation year

| T | Model | MAE all | RMSE all | MAE positive | RMSE positive | Capture@20% |
|---:|---|---:|---:|---:|---:|---:|
{chr(10).join(year_rows)}

## Provisional-selection rule

{result['selection']['predeclared_rule']}

```json
{json.dumps(result['selection']['candidate_evidence'], indent=2)}
```

## Reproducibility checks

- Seed: {RANDOM_SEED}.
- Every fitted model produced analytically identical validation predictions on a second fit with the same seed/settings.
- Every saved and reloaded model produced byte-identical validation predictions.
- Source-year checks confirmed outcome `T+1`, climate `T`, fire history `T-10..T-1`, and governed CLC assignment.
- Machine-readable metrics: `{METRICS_PATH.as_posix()}`.
- Validation predictions: `{PREDICTIONS_PATH.as_posix()}`.
- Model and feature-order metadata: `{ARTIFACT_METADATA_PATH.as_posix()}`.

This is a model-selection gate, not final-test evaluation, model acceptance, classification, probability calibration, or a predictive recommendation.
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(content, encoding="utf-8")


def run_model_selection() -> dict[str, Any]:
    started = time.perf_counter()
    panel_validation = json.loads(PANEL_VALIDATION_PATH.read_text(encoding="utf-8"))
    if Path(panel_validation["panel_path"]).as_posix() != PANEL_PATH.as_posix():
        raise ValueError("Panel path does not match the validated canonical artifact")

    frame, row_group_access = read_train_validation_rows(PANEL_PATH)
    contract_validation = validate_model_selection_frame(frame)
    train = frame.loc[frame.observation_year.isin(TRAIN_YEARS)].copy()
    validation = frame.loc[frame.observation_year.isin(VALIDATION_YEARS)].copy()
    train.sort_values(["observation_year", "cell_id"], inplace=True, kind="mergesort")
    validation.sort_values(["observation_year", "cell_id"], inplace=True, kind="mergesort")

    X_train = train.loc[:, PREDICTOR_COLUMNS]
    y_train = train[TARGET_COLUMN]
    X_validation = validation.loc[:, PREDICTOR_COLUMNS]
    y_validation = validation[TARGET_COLUMN].to_numpy(dtype=np.float64)

    specs = _candidate_specs()
    predictions: dict[str, np.ndarray] = {
        "zero_prediction_baseline": np.zeros(len(validation), dtype=np.float64),
    }
    fit_seconds: dict[str, float] = {}
    artifact_records: dict[str, Any] = {}
    repeatability: dict[str, Any] = {}

    baseline_start = time.perf_counter()
    historical = HistoricalFireMeanRegressor().fit(X_train, y_train)
    predictions["historical_fire_baseline"] = historical.predict(X_validation)
    fit_seconds["historical_fire_baseline"] = time.perf_counter() - baseline_start
    artifact_records["historical_fire_baseline"] = _save_and_verify_model(
        "historical_fire_baseline",
        historical,
        X_validation,
        predictions["historical_fire_baseline"],
    )
    historical_repeat = HistoricalFireMeanRegressor().fit(X_train, y_train).predict(X_validation)
    repeatability["historical_fire_baseline"] = {
        "predictions_identical_on_second_fit": bool(
            np.array_equal(predictions["historical_fire_baseline"], historical_repeat)
        ),
        "maximum_absolute_difference": float(
            np.max(np.abs(predictions["historical_fire_baseline"] - historical_repeat))
        ),
    }

    for name in ("random_forest_regressor", "tweedie_regressor"):
        fit_start = time.perf_counter()
        model = _make_candidate(name, specs)
        model.fit(X_train, y_train)
        model_predictions = np.asarray(model.predict(X_validation), dtype=np.float64)
        if not np.isfinite(model_predictions).all() or (model_predictions < 0).any():
            raise ValueError(f"{name} produced invalid negative or non-finite predictions")
        predictions[name] = model_predictions
        fit_seconds[name] = time.perf_counter() - fit_start
        artifact_records[name] = _save_and_verify_model(name, model, X_validation, model_predictions)

        repeat_model = _make_candidate(name, specs)
        repeat_model.fit(X_train, y_train)
        repeat_predictions = np.asarray(repeat_model.predict(X_validation), dtype=np.float64)
        difference = np.abs(model_predictions - repeat_predictions)
        identical = np.array_equal(model_predictions, repeat_predictions)
        if not identical:
            raise ValueError(f"{name} was not prediction-identical on deterministic repeat fit")
        repeatability[name] = {
            "predictions_identical_on_second_fit": True,
            "maximum_absolute_difference": float(difference.max()),
        }
        del repeat_model, repeat_predictions

    metrics = {name: evaluate_predictions(validation, values) for name, values in predictions.items()}
    selection = _selection_decision(metrics)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prediction_table = validation.loc[:, ["cell_id", "observation_year", TARGET_COLUMN]].copy()
    for name, values in predictions.items():
        prediction_table[f"predicted__{name}"] = values
    prediction_table.to_parquet(PREDICTIONS_PATH, index=False)

    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model_contract_version": MODEL_CONTRACT_VERSION,
        "panel": {
            "path": PANEL_PATH.as_posix(),
            "validated_sha256": panel_validation["panel_sha256"],
            "validation_record": PANEL_VALIDATION_PATH.as_posix(),
        },
        "split": {
            "training_years": list(TRAIN_YEARS),
            "validation_years": list(VALIDATION_YEARS),
            "final_test_years_reserved_and_unopened": list(FINAL_TEST_YEARS),
        },
        "row_group_access": row_group_access,
        "contract_validation": contract_validation,
        "candidate_parameters": specs,
        "random_seed": RANDOM_SEED,
        "fit_seconds": fit_seconds,
        "metrics": metrics,
        "selection": selection,
        "repeatability": repeatability,
        "artifacts": artifact_records,
        "validation_predictions": {
            "path": PREDICTIONS_PATH.as_posix(),
            "rows": len(prediction_table),
            "sha256": _sha256(PREDICTIONS_PATH),
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "pyarrow": pyarrow.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
        "runtime_seconds": time.perf_counter() - started,
    }

    ARTIFACT_METADATA_PATH.write_text(
        json.dumps(
            {
                "model_contract_version": MODEL_CONTRACT_VERSION,
                "feature_order": list(PREDICTOR_COLUMNS),
                "target": TARGET_COLUMN,
                "regression_output": "predicted_burned_share_next_year",
                "panel": result["panel"],
                "split": result["split"],
                "candidate_parameters": specs,
                "random_seed": RANDOM_SEED,
                "artifacts": artifact_records,
                "selection": selection,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    _write_report(result)
    return result
