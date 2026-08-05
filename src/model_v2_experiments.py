"""Deterministic train/validation-only comparison of grouped V2 features."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import TweedieRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.feature_contract import PREDICTOR_COLUMNS, TARGET_COLUMN
from src.model_selection import (
    HistoricalFireMeanRegressor,
    MEANINGFUL_IMPROVEMENT_FRACTION,
    RANDOM_SEED,
    TRAIN_YEARS,
    VALIDATION_YEARS,
    evaluate_predictions,
)
from src.model_v2_features import FEATURE_GROUPS, FEATURE_MATRIX_MANIFEST_PATH, FEATURE_MATRIX_PATH, validate_v2_feature_matrix


OUTPUT_DIR = Path("data/processed/model_v2_feature_experiments")
MODELS_DIR = OUTPUT_DIR / "models"
METRICS_PATH = OUTPUT_DIR / "train_validation_metrics.json"
PREDICTIONS_PATH = OUTPUT_DIR / "validation_predictions.parquet"
ISOLATED_CLIMATE_PAIR_GROUP = "climate_extremes_9"
ISOLATED_CLIMATE_PAIR_FEATURES = PREDICTOR_COLUMNS + (
    "warm_season_max_monthly_2m_temperature_c",
    "warm_season_min_monthly_soil_water_layer1",
)
ISOLATED_METRICS_PATH = OUTPUT_DIR / "isolated_climate_pair_validation.json"
ISOLATED_PREDICTIONS_PATH = OUTPUT_DIR / "isolated_climate_pair_validation_predictions.parquet"


class HurdleHistGradientRegressor:
    """Expected burned share = P(positive) × expected positive burned share.

    This treats zero-inflation explicitly while retaining a continuous output;
    it is not a classification model or a probability output to end users.
    """

    def __init__(self, *, random_state: int = RANDOM_SEED) -> None:
        self.random_state = random_state
        self.occurrence_model = HistGradientBoostingClassifier(
            learning_rate=0.08, max_iter=120, max_leaf_nodes=23, min_samples_leaf=120,
            l2_regularization=0.05, random_state=random_state,
        )
        self.positive_model = HistGradientBoostingRegressor(
            loss="squared_error", learning_rate=0.07, max_iter=150, max_leaf_nodes=23,
            min_samples_leaf=80, l2_regularization=0.05, random_state=random_state,
        )

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "HurdleHistGradientRegressor":
        target = np.asarray(y, dtype="float64")
        positive = target > 0.0
        if positive.sum() < 2 or (~positive).sum() < 2:
            raise ValueError("Hurdle model needs both positive and zero targets")
        # Constrain OpenMP explicitly: the project runs on a memory-limited
        # desktop environment where uncontrolled worker creation is unsafe.
        with threadpool_limits(limits=1, user_api="openmp"):
            self.occurrence_model.fit(X, positive.astype("int8"))
            self.positive_model.fit(X.loc[positive], target[positive])
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        probability = self.occurrence_model.predict_proba(X)[:, 1]
        positive_share = np.clip(self.positive_model.predict(X), 0.0, 1.0)
        return np.clip(probability * positive_share, 0.0, 1.0)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_v2_experiment_frame() -> pd.DataFrame:
    """Open only train/validation V2 rows; final-test data are absent by design."""
    if not FEATURE_MATRIX_PATH.exists() or not FEATURE_MATRIX_MANIFEST_PATH.exists():
        raise FileNotFoundError("Build V2 feature extensions before running experiments")
    manifest = json.loads(FEATURE_MATRIX_MANIFEST_PATH.read_text(encoding="utf-8"))
    if tuple(manifest["model_selection_years"]) != TRAIN_YEARS + VALIDATION_YEARS:
        raise ValueError("V2 feature matrix is not restricted to train/validation years")
    if int(manifest["final_test_rows_read"]) != 0:
        raise ValueError("V2 matrix contract reports final-test access")
    frame = pd.read_parquet(FEATURE_MATRIX_PATH)
    validate_v2_feature_matrix(frame)
    if not set(frame.observation_year).issubset(set(TRAIN_YEARS + VALIDATION_YEARS)):
        raise ValueError("Final-test years entered V2 experiment frame")
    return frame.sort_values(["observation_year", "cell_id"], kind="mergesort").reset_index(drop=True)


def _models() -> dict[str, Any]:
    return {
        "random_forest_regressor": RandomForestRegressor(
            n_estimators=80, max_depth=14, min_samples_leaf=20, max_features=0.8,
            bootstrap=True, random_state=RANDOM_SEED, n_jobs=1,
        ),
        "tweedie_regressor": Pipeline([
            ("standardize", StandardScaler()),
            ("regressor", TweedieRegressor(power=1.5, alpha=0.1, link="log", max_iter=500, tol=1e-7)),
        ]),
        "hist_gradient_boosting_regressor": HistGradientBoostingRegressor(
            loss="squared_error", learning_rate=0.07, max_iter=150, max_leaf_nodes=31,
            min_samples_leaf=100, l2_regularization=0.05, random_state=RANDOM_SEED,
        ),
        "hurdle_hist_gradient_regressor": HurdleHistGradientRegressor(),
    }


def _save_model(group: str, name: str, model: Any, X_validation: pd.DataFrame, expected: np.ndarray) -> dict[str, object]:
    directory = MODELS_DIR / group
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.joblib"
    joblib.dump({"model": model, "feature_order": list(X_validation.columns), "group": group}, path)
    loaded = joblib.load(path)
    actual = np.clip(np.asarray(loaded["model"].predict(X_validation), dtype="float64"), 0.0, 1.0)
    if not np.array_equal(actual, expected):
        raise ValueError(f"Reloaded {group}/{name} predictions differ")
    return {"path": path.as_posix(), "sha256": _sha256(path), "reload_predictions_identical": True}


def _existing_model(group: str, name: str, X_validation: pd.DataFrame) -> tuple[Any, np.ndarray, dict[str, object]] | None:
    """Reuse a verified group artifact after an interrupted deterministic run."""
    path = MODELS_DIR / group / f"{name}.joblib"
    if not path.exists():
        return None
    payload = joblib.load(path)
    if payload.get("group") != group or payload.get("feature_order") != list(X_validation.columns):
        raise ValueError(f"Existing {group}/{name} artifact has a different feature contract")
    values = np.clip(np.asarray(payload["model"].predict(X_validation), dtype="float64"), 0.0, 1.0)
    if not np.isfinite(values).all():
        raise ValueError(f"Existing {group}/{name} artifact produces non-finite predictions")
    return payload["model"], values, {"path": path.as_posix(), "sha256": _sha256(path), "reload_predictions_identical": True, "status": "reused"}


def _candidate_gate(metrics: dict[str, Any]) -> dict[str, object]:
    baseline = metrics["historical_fire_baseline"]["overall"]
    qualifying: list[str] = []
    evidence: dict[str, object] = {}
    for name, result in metrics.items():
        if name in ("zero_prediction_baseline", "historical_fire_baseline"):
            continue
        current = result["overall"]
        mae_improvement = 1.0 - current["mae_all"] / baseline["mae_all"]
        rmse_improvement = 1.0 - current["rmse_all"] / baseline["rmse_all"]
        capture_not_lower = current["capture_at_20_percent"] >= baseline["capture_at_20_percent"]
        passes = mae_improvement >= MEANINGFUL_IMPROVEMENT_FRACTION and capture_not_lower
        evidence[name] = {"relative_mae_improvement": mae_improvement,
                          "relative_rmse_improvement": rmse_improvement,
                          "capture_not_lower_than_historical_baseline": capture_not_lower,
                          "passes_exploratory_validation_gate": passes}
        if passes:
            qualifying.append(name)
    chosen = min(qualifying, key=lambda name: metrics[name]["overall"]["mae_all"]) if qualifying else None
    return {"rule": "At least 2% lower validation MAE than the historical baseline and capture@20% not lower; choose lowest MAE. Exploratory only.",
            "candidate_evidence": evidence, "provisional_candidate": chosen}


def tie_aware_ranking_metrics(
    y_true: np.ndarray,
    scores: np.ndarray,
    selection_fraction: float,
) -> dict[str, float | int]:
    """Evaluate a ranking without arbitrarily splitting equal-score boundary ties.

    If the selection budget ends inside a tied score group, every row in that
    group contributes the same fractional weight. This is particularly
    important for the discrete historical-fire baseline.
    """
    if not 0.0 < selection_fraction <= 1.0:
        raise ValueError("selection_fraction must be in (0, 1]")
    target = np.asarray(y_true, dtype="float64")
    ranking_scores = np.asarray(scores, dtype="float64")
    if target.shape != ranking_scores.shape or target.ndim != 1:
        raise ValueError("y_true and scores must be aligned one-dimensional arrays")
    if not np.isfinite(target).all() or not np.isfinite(ranking_scores).all():
        raise ValueError("Ranking inputs must be finite")

    grouped = (
        pd.DataFrame(
            {
                "score": ranking_scores,
                "positive": (target > 0.0).astype("int64"),
                "burned_mass": target,
            }
        )
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


def evaluate_tie_aware_rankings(
    validation: pd.DataFrame,
    predictions: np.ndarray,
) -> dict[str, Any]:
    """Report tie-aware 10% and 20% ranking diagnostics overall and by year."""
    target = validation[TARGET_COLUMN].to_numpy(dtype="float64")
    years = validation.observation_year.to_numpy(dtype="int16")

    def _for_mask(mask: np.ndarray) -> dict[str, Any]:
        return {
            f"top_{int(fraction * 100)}_percent": tie_aware_ranking_metrics(
                target[mask], predictions[mask], fraction
            )
            for fraction in (0.10, 0.20)
        }

    return {
        "overall": _for_mask(np.ones(len(validation), dtype=bool)),
        "by_validation_year": {
            str(year): _for_mask(years == year) for year in VALIDATION_YEARS
        },
    }


def isolated_climate_pair_gate(metrics: dict[str, Any]) -> dict[str, Any]:
    """Apply the audit's predeclared validation gate to the nine-feature model."""
    historical = metrics["historical_fire_baseline"]
    canonical = metrics["canonical_7_hurdle"]
    candidate = metrics["climate_extremes_9_hurdle"]
    checks: dict[str, bool] = {
        "overall_mae_at_least_2pct_better_than_canonical_7": (
            candidate["overall"]["mae_all"] <= 0.98 * canonical["overall"]["mae_all"]
        ),
    }
    for year in VALIDATION_YEARS:
        key = str(year)
        hist_year = historical["by_validation_year"][key]
        canonical_year = canonical["by_validation_year"][key]
        candidate_year = candidate["by_validation_year"][key]
        checks[f"mae_better_than_canonical_7_{key}"] = (
            candidate_year["mae_all"] < canonical_year["mae_all"]
        )
        checks[f"rmse_within_3pct_of_historical_{key}"] = (
            candidate_year["rmse_all"] <= 1.03 * hist_year["rmse_all"]
        )
        checks[f"positive_mae_within_3pct_of_historical_{key}"] = (
            candidate_year["mae_positive"] <= 1.03 * hist_year["mae_positive"]
        )
        checks[f"absolute_mean_bias_better_than_historical_{key}"] = (
            abs(candidate_year["mean_predicted"] - candidate_year["mean_observed"])
            < abs(hist_year["mean_predicted"] - hist_year["mean_observed"])
        )
    passed = all(checks.values())
    return {
        "rule": (
            "Candidate must improve overall MAE by at least 2% versus the canonical seven-feature hurdle; "
            "improve MAE in both validation years; remain within 3% of the historical baseline for RMSE and "
            "positive-row MAE in each year; and have lower absolute mean-prediction bias than the historical "
            "baseline in each year. Ranking diagnostics are reported but are not a buyer threshold."
        ),
        "checks": checks,
        "passes_gate": passed,
        "decision": (
            "freeze_nine_feature_hurdle_and_historical_baseline_for_final_test"
            if passed else "stop_feature_expansion_nine_feature_candidate_not_approved"
        ),
        "final_temporal_test_may_begin": passed,
    }


def _load_reference_model(group: str, name: str, feature_order: tuple[str, ...]) -> Any:
    path = MODELS_DIR / group / f"{name}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"Required reference model is missing: {path}")
    payload = joblib.load(path)
    if payload.get("group") != group or payload.get("feature_order") != list(feature_order):
        raise ValueError(f"Reference artifact {path} does not match its feature contract")
    return payload["model"]


def run_isolated_climate_pair_validation() -> dict[str, Any]:
    """Run the single audit-approved nine-feature hurdle validation experiment."""
    started = time.perf_counter()
    frame = load_v2_experiment_frame()
    train = frame.loc[frame.observation_year.isin(TRAIN_YEARS)].copy()
    validation = frame.loc[frame.observation_year.isin(VALIDATION_YEARS)].copy()
    if frame.observation_year.isin((2022, 2023, 2024)).any():
        raise ValueError("Final-test years entered isolated climate-pair validation")

    canonical_features = tuple(PREDICTOR_COLUMNS)
    X_train = train.loc[:, ISOLATED_CLIMATE_PAIR_FEATURES]
    X_validation = validation.loc[:, ISOLATED_CLIMATE_PAIR_FEATURES]
    y_train = train[TARGET_COLUMN]

    historical_model = _load_reference_model("baseline_7", "historical_fire_baseline", canonical_features)
    canonical_model = _load_reference_model("baseline_7", "hurdle_hist_gradient_regressor", canonical_features)
    historical_predictions = np.clip(
        np.asarray(historical_model.predict(validation.loc[:, canonical_features]), dtype="float64"), 0.0, 1.0
    )
    canonical_predictions = np.clip(
        np.asarray(canonical_model.predict(validation.loc[:, canonical_features]), dtype="float64"), 0.0, 1.0
    )

    candidate = HurdleHistGradientRegressor()
    with threadpool_limits(limits=1, user_api="openmp"):
        candidate.fit(X_train, y_train)
    candidate_predictions = candidate.predict(X_validation)
    artifact = _save_model(
        ISOLATED_CLIMATE_PAIR_GROUP,
        "hurdle_hist_gradient_regressor",
        candidate,
        X_validation,
        candidate_predictions,
    )

    repeated = HurdleHistGradientRegressor()
    with threadpool_limits(limits=1, user_api="openmp"):
        repeated.fit(X_train, y_train)
    repeated_predictions = repeated.predict(X_validation)
    repeat_identical = np.array_equal(candidate_predictions, repeated_predictions)
    if not repeat_identical:
        raise ValueError("Repeated nine-feature fit did not reproduce validation predictions")

    prediction_sets = {
        "historical_fire_baseline": historical_predictions,
        "canonical_7_hurdle": canonical_predictions,
        "climate_extremes_9_hurdle": candidate_predictions,
    }
    metrics = {
        name: evaluate_predictions(validation, values) for name, values in prediction_sets.items()
    }
    rankings = {
        name: evaluate_tie_aware_rankings(validation, values) for name, values in prediction_sets.items()
    }
    gate = isolated_climate_pair_gate(metrics)
    gate["checks"]["repeat_fit_predictions_identical"] = repeat_identical
    gate["checks"]["saved_model_reload_predictions_identical"] = bool(
        artifact["reload_predictions_identical"]
    )
    gate["checks"]["final_test_rows_read_is_zero"] = True
    gate["passes_gate"] = all(gate["checks"].values())
    gate["final_temporal_test_may_begin"] = gate["passes_gate"]
    gate["decision"] = (
        "freeze_nine_feature_hurdle_and_historical_baseline_for_final_test"
        if gate["passes_gate"] else "stop_feature_expansion_nine_feature_candidate_not_approved"
    )

    output_predictions = validation[["cell_id", "observation_year", TARGET_COLUMN]].copy()
    for name, values in prediction_sets.items():
        output_predictions[name] = values
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporary_predictions = ISOLATED_PREDICTIONS_PATH.with_suffix(".parquet.tmp")
    output_predictions.to_parquet(temporary_predictions, index=False, compression="zstd")
    os.replace(temporary_predictions, ISOLATED_PREDICTIONS_PATH)

    results: dict[str, Any] = {
        "experiment": "single_audit_approved_climate_extremes_pair",
        "split": {
            "training_years": list(TRAIN_YEARS),
            "validation_years": list(VALIDATION_YEARS),
            "final_test_years_accessed": [],
            "final_test_rows_read": 0,
            "train_rows": len(train),
            "validation_rows": len(validation),
        },
        "feature_order": list(ISOLATED_CLIMATE_PAIR_FEATURES),
        "added_features": list(ISOLATED_CLIMATE_PAIR_FEATURES[-2:]),
        "model": {
            "name": "hurdle_hist_gradient_regressor",
            "random_seed": RANDOM_SEED,
            "parameter_search": "none",
            "same_estimator_contract_as_existing_canonical_7_hurdle": True,
        },
        "metrics": metrics,
        "tie_aware_ranking_diagnostics": rankings,
        "validation_gate": gate,
        "artifacts": {
            "model": artifact,
            "predictions": {
                "path": ISOLATED_PREDICTIONS_PATH.as_posix(),
                "sha256": _sha256(ISOLATED_PREDICTIONS_PATH),
            },
        },
        "determinism": {
            "repeat_fit_predictions_identical": repeat_identical,
            "saved_model_reload_predictions_identical": artifact["reload_predictions_identical"],
        },
        "runtime_seconds": time.perf_counter() - started,
    }
    temporary_metrics = ISOLATED_METRICS_PATH.with_suffix(".json.tmp")
    temporary_metrics.write_text(json.dumps(results, indent=2), encoding="utf-8")
    os.replace(temporary_metrics, ISOLATED_METRICS_PATH)
    return results


def run_v2_feature_group_experiments() -> dict[str, Any]:
    """Fit modest, deterministic regression candidates on each feature group."""
    started = time.perf_counter()
    frame = load_v2_experiment_frame()
    train = frame.loc[frame.observation_year.isin(TRAIN_YEARS)].copy()
    validation = frame.loc[frame.observation_year.isin(VALIDATION_YEARS)].copy()
    y_train = train[TARGET_COLUMN]
    y_validation = validation[TARGET_COLUMN].to_numpy(dtype="float64")
    output_predictions = validation[["cell_id", "observation_year", TARGET_COLUMN]].copy()
    results: dict[str, Any] = {"split": {"training_years": list(TRAIN_YEARS), "validation_years": list(VALIDATION_YEARS),
                                          "final_test_rows_read": 0, "train_rows": len(train), "validation_rows": len(validation)},
                               "groups": {}}
    for group, features in FEATURE_GROUPS.items():
        X_train = train.loc[:, features]
        X_validation = validation.loc[:, features]
        predictions: dict[str, np.ndarray] = {"zero_prediction_baseline": np.zeros(len(validation), dtype="float64")}
        existing = _existing_model(group, "historical_fire_baseline", X_validation)
        if existing is None:
            historical = HistoricalFireMeanRegressor().fit(X_train, y_train)
            predictions["historical_fire_baseline"] = historical.predict(X_validation)
            historical_artifact = _save_model(group, "historical_fire_baseline", historical, X_validation, predictions["historical_fire_baseline"])
        else:
            _, predictions["historical_fire_baseline"], historical_artifact = existing
        artifacts: dict[str, Any] = {"historical_fire_baseline": historical_artifact}
        for name, model in _models().items():
            existing = _existing_model(group, name, X_validation)
            if existing is not None:
                _, values, artifact = existing
            else:
                with threadpool_limits(limits=1, user_api="openmp"):
                    model.fit(X_train, y_train)
                raw_values = np.asarray(model.predict(X_validation), dtype="float64")
                if not np.isfinite(raw_values).all():
                    raise ValueError(f"{group}/{name} produced non-finite burned-share predictions")
                # A burned share has closed support [0, 1].  This constrains only a
                # regressor's output, never physically valid predictor inputs.
                values = np.clip(raw_values, 0.0, 1.0)
                artifact = _save_model(group, name, model, X_validation, values)
            predictions[name] = values
            artifacts[name] = artifact
        metrics = {name: evaluate_predictions(validation, values) for name, values in predictions.items()}
        results["groups"][group] = {"features": list(features), "metrics": metrics,
                                    "selection": _candidate_gate(metrics), "artifacts": artifacts}
        for name, values in predictions.items():
            output_predictions[f"{group}__{name}"] = values
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_predictions.to_parquet(PREDICTIONS_PATH, index=False, compression="zstd")
    results["prediction_path"] = PREDICTIONS_PATH.as_posix()
    results["runtime_seconds"] = time.perf_counter() - started
    METRICS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results
