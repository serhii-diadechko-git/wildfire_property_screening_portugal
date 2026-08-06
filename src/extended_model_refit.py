"""Refit the frozen nine-feature candidate on the extended training period.

This module deliberately operates only on T=2010-2021.  T=2022-2024 are
neither present in its input panel nor read from the canonical national panel.
The two climate-extreme features are derived directly from the registered local
JJAS ERA5-Land files and accepted static coastal fallback map. The validated
base panel is read without changing its values.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from src import national_panel as panel
from src.climate_features import read_grib_variable
from src.evaluation import evaluate_predictions, evaluate_tie_aware_rankings
from src.extended_training_panel import (
    PANEL_PATH as EXTENDED_PANEL_PATH,
)
from src.feature_contract import PREDICTOR_COLUMNS, TARGET_COLUMN
from src.modeling import HistoricalFireMeanRegressor, HurdleHistGradientRegressor, NINE_FEATURES, RANDOM_SEED


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
EXTRA_FEATURES = NINE_FEATURES[-2:]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _prediction_sha256(values: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(values, dtype="<f8").tobytes()).hexdigest().upper()


def _monthly_extreme_grids(years: tuple[int, ...]) -> dict[int, dict[str, np.ndarray]]:
    """Read the two monthly-extreme fields from each requested annual GRIB."""
    result: dict[int, dict[str, np.ndarray]] = {}
    for year in years:
        path = ROOT / f"data/raw/climate/era5_land/era5_land_monthly_jjas_{year}_mainland_portugal.grib"
        latitude, longitude, temperature, temperature_months = read_grib_variable(path, "2t")
        soil_lat, soil_lon, soil, soil_months = read_grib_variable(path, "swvl1")
        if not (
            temperature_months == soil_months == (6, 7, 8, 9)
            and np.array_equal(latitude, soil_lat)
            and np.array_equal(longitude, soil_lon)
        ):
            raise ValueError(f"ERA5 monthly grids/months do not align for T={year}")
        with warnings.catch_warnings(), np.errstate(invalid="ignore"):
            warnings.simplefilter("ignore", category=RuntimeWarning)
            result[year] = {
                "latitude": latitude,
                "longitude": longitude,
                "warm_season_max_monthly_2m_temperature_c": np.nanmax(temperature, axis=0) - 273.15,
                "warm_season_min_monthly_soil_water_layer1": np.nanmin(soil, axis=0),
            }
    return result


def _derive_extremes_batch(
    batch_id: str,
    grids: dict[int, dict[str, np.ndarray]],
    fallback: pd.DataFrame,
) -> pd.DataFrame:
    grid = pd.read_parquet(
        panel._grid_batch_path(batch_id), columns=["cell_id", "centroid_latitude", "centroid_longitude"]
    )
    latitudes = grid.centroid_latitude.to_numpy()
    longitudes = grid.centroid_longitude.to_numpy()
    rows: list[pd.DataFrame] = []
    for year in sorted(grids):
        source = grids[year]
        lat_index = np.abs(source["latitude"][:, None] - latitudes).argmin(axis=0)
        lon_index = np.abs(source["longitude"][:, None] - longitudes).argmin(axis=0)
        maximum_temperature = source["warm_season_max_monthly_2m_temperature_c"][lat_index, lon_index].astype("float64")
        minimum_soil_water = source["warm_season_min_monthly_soil_water_layer1"][lat_index, lon_index].astype("float64")
        masked = np.isnan(maximum_temperature)
        if not np.array_equal(np.isnan(minimum_soil_water), masked):
            raise ValueError(f"ERA5 monthly-extreme water-mask differs for T={year}/{batch_id}")
        for position in np.flatnonzero(masked):
            cell_id = grid.cell_id.iloc[position]
            if cell_id not in fallback.index:
                raise ValueError(f"No accepted ERA5 fallback mapping for {cell_id}")
            flat_index = int(fallback.loc[cell_id, "fallback_flat_index"])
            maximum_temperature[position] = float(source["warm_season_max_monthly_2m_temperature_c"].ravel()[flat_index])
            minimum_soil_water[position] = float(source["warm_season_min_monthly_soil_water_layer1"].ravel()[flat_index])
        if np.isnan(maximum_temperature).any() or np.isnan(minimum_soil_water).any():
            raise ValueError(f"ERA5 fallback left missing monthly extrema for T={year}/{batch_id}")
        rows.append(pd.DataFrame({
            "cell_id": grid.cell_id.to_numpy(),
            "observation_year": np.full(len(grid), year, dtype="int16"),
            "warm_season_max_monthly_2m_temperature_c": maximum_temperature,
            "warm_season_min_monthly_soil_water_layer1": minimum_soil_water,
        }))
    return pd.concat(rows, ignore_index=True)


def _monthly_extremes(
    years: tuple[int, ...], progress: Callable[[str], None] = print
) -> pd.DataFrame:
    """Build annual extrema in bounded grid batches, then concatenate."""
    grids = _monthly_extreme_grids(years)
    fallback = panel._load_era5_fallback_mapping()
    catalog = panel.load_grid_catalog()
    frames: list[pd.DataFrame] = []
    for number, batch in enumerate(catalog["batches"], start=1):
        frame = _derive_extremes_batch(batch["batch_id"], grids, fallback)
        frames.append(frame)
        progress(f"Extended climate extremes {batch['batch_id']}: {len(frame)} rows ({number}/{catalog['batch_count']})")
    result = pd.concat(frames, ignore_index=True)
    if result.duplicated(["cell_id", "observation_year"]).any() or result[list(EXTRA_FEATURES)].isna().any().any():
        raise ValueError("Invalid climate-extreme component")
    return result


def _validate_frame(frame: pd.DataFrame) -> None:
    if tuple(sorted(int(value) for value in frame.observation_year.unique())) != ALLOWED_YEARS:
        raise ValueError("Extended model frame does not contain precisely T=2010-2021")
    if frame.observation_year.isin((2022, 2023, 2024)).any():
        raise ValueError("Final-test year entered extended model frame")
    if frame.duplicated(["cell_id", "observation_year"]).any():
        raise ValueError("Duplicate extended model analytical key")
    required = list(NINE_FEATURES) + [TARGET_COLUMN]
    if frame[required].isna().any().any() or not np.isfinite(frame[required].to_numpy(dtype="float64")).all():
        raise ValueError("Extended model frame contains non-finite values")
    ranges = {
        "warm_season_max_monthly_2m_temperature_c": (-20.0, 60.0),
        "warm_season_min_monthly_soil_water_layer1": (0.0, 1.0),
    }
    for column, (minimum, maximum) in ranges.items():
        values = frame[column].to_numpy(dtype="float64")
        if values.min() < minimum or values.max() > maximum:
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
            "feature_order": list(NINE_FEATURES),
            "final_test_rows_read": 0,
            "status": "validated_reused",
        }
    base = pd.read_parquet(EXTENDED_PANEL_PATH)
    base = base.loc[base.observation_year.isin(ALLOWED_YEARS)].copy()
    extremes = _monthly_extremes(ALLOWED_YEARS, progress)
    result = base.merge(
        extremes, on=["cell_id", "observation_year"], how="left", validate="one_to_one"
    ).sort_values(
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
        "feature_order": list(NINE_FEATURES),
        "final_test_rows_read": 0,
    }


def _save_model(name: str, model: Any, predictions: np.ndarray) -> dict[str, object]:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    path = MODEL_DIR / f"{name}.joblib"
    payload = {
        "model": model,
        "model_name": name,
        "feature_order": list(NINE_FEATURES),
        "train_years": list(TRAIN_YEARS),
        "validation_years": list(VALIDATION_YEARS),
        "random_seed": RANDOM_SEED,
        "temporal_rule": "predictors are T-only; target is T+1; final-test rows are absent",
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary model output requires inspection: {temporary}")
    joblib.dump(payload, temporary)
    os.replace(temporary, path)
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": _sha256(path), "prediction_sha256": _prediction_sha256(predictions)}


def refit_extended_models() -> dict[str, object]:
    """Fit the frozen historical baseline and nine-feature hurdle, then validate only T=2020-2021."""
    if not FEATURE_MATRIX_PATH.exists():
        raise FileNotFoundError("Build the extended nine-feature matrix first")
    frame = pd.read_parquet(FEATURE_MATRIX_PATH)
    _validate_frame(frame)
    train = frame.loc[frame.observation_year.isin(TRAIN_YEARS)].copy()
    validation = frame.loc[frame.observation_year.isin(VALIDATION_YEARS)].copy()
    if len(train) != 89112 * len(TRAIN_YEARS) or len(validation) != 89112 * len(VALIDATION_YEARS):
        raise ValueError("Unexpected extended split row count")
    X_train, X_validation = train.loc[:, NINE_FEATURES], validation.loc[:, NINE_FEATURES]
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
            "feature_order": list(NINE_FEATURES), "target": TARGET_COLUMN,
        },
        "row_counts": {"train": len(train), "validation": len(validation)},
        "models": {
            "historical_recurrence_baseline": {"definition": "training-period empirical mean target by prior-ten-year recurrence count", "artifact": historical_artifact},
            "nine_feature_hurdle": {"definition": "P(next-year burned share > 0) times conditional expected positive burned share", "artifact": hurdle_artifact,
                                    "parameters": {"occurrence": {"learning_rate": 0.08, "max_iter": 120, "max_leaf_nodes": 23, "min_samples_leaf": 120, "l2_regularization": 0.05}, "positive_share": {"learning_rate": 0.07, "max_iter": 150, "max_leaf_nodes": 23, "min_samples_leaf": 80, "l2_regularization": 0.05}}},
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
        "# Extended training-only model refit",
        "",
        "This controlled refit uses T=2010-2019 for fitting and T=2020-2021 for validation. T=2022-2024 were not opened or used.",
        "",
        "## Candidate comparison",
        "",
        "| Model | Validation MAE | Validation RMSE | Positive-row MAE | Positive-cell capture at 20% | Burned-share mass capture at 20% |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, label in (("historical_recurrence_baseline", "Historical recurrence baseline"), ("nine_feature_hurdle", "Nine-feature hurdle")):
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
        for name, label in (("historical_recurrence_baseline", "Historical recurrence baseline"), ("nine_feature_hurdle", "Nine-feature hurdle")):
            current = metrics[name]["by_validation_year"][str(year)]
            lines.append(
                f"| {year} | {label} | {current['mae_all']:.8f} | {current['rmse_all']:.8f} | {current['mae_positive']:.8f} | {current['capture_at_20_percent']:.4f} |"
            )
    lines.extend([
        "",
        "## Guardrails",
        "",
        "- The historical baseline is a training-only empirical mapping from the strict T-10 through T-1 recurrence count to expected next-year burned share.",
        "- The hurdle output is a continuous expected burned share, not a buyer-facing probability or decision threshold.",
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
