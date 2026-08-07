"""Versioned annual forecasting model and preflight contract.

This module separates two deliberate stages:

* refit the already selected nine-feature specification on every *labelled*
  row available at a given annual cutoff; and
* score the next calendar year only when all T-only predictor inputs exist.

It never creates an observed target for a future scoring year.  In particular,
the 2026 score requires T=2025 ERA5-Land JJAS inputs, while ICNF 2026 and 2027
must not be read by the scoring path.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any
import warnings

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pyogrio
from threadpoolctl import threadpool_limits

from src.climate_features import era5_source_paths, jjas_total_precipitation_mm, read_grib_variable
from src.config import OPERATIONAL_FORECAST
from src.feature_contract import CLIMATE_PREDICTOR_COLUMNS, PREDICTOR_COLUMNS, TARGET_COLUMN
from src.modeling import HurdleHistGradientRegressor, RANDOM_SEED
from src import national_panel as panel
from src.source_registry import (
    CLC_2018_V2020_20U1,
    CLC_PREPARED_PORTUGAL_LAYERS,
    COP_DEM_GLO30,
    ERA5_LAND_AVAILABLE_ARCHIVES,
    EXTENDED_TRAINING_ICNF_ARCHIVES,
)


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_EVALUATION_DIR = ROOT / "data/processed/extended_model_selection_2010_2021"
DEVELOPMENT_MATRIX_PATH = HISTORICAL_EVALUATION_DIR / "nine_feature_train_validation_matrix.parquet"
FINAL_TEST_MATRIX_PATH = HISTORICAL_EVALUATION_DIR / "final_temporal_test_nine_feature_matrix.parquet"
OUTPUT_DIR = ROOT / "data/processed/final_model_2010_2024"
LABELED_PANEL_PATH = OUTPUT_DIR / "nine_feature_labeled_panel_2010_2024.parquet"
PANEL_MANIFEST_PATH = OUTPUT_DIR / "nine_feature_labeled_panel_2010_2024.json"
MODEL_PATH = OUTPUT_DIR / "nine_feature_hurdle.joblib"
MODEL_METADATA_PATH = OUTPUT_DIR / "model_metadata.json"
PREFLIGHT_PATH = OUTPUT_DIR / "forecast_2026_preflight.json"
REPORT_PATH = ROOT / "reports/validation/operational_forecast_readiness.md"
FORECAST_VALIDATION_REPORT_PATH = ROOT / "reports/validation/operational_forecast_2026_validation.md"
FORECAST_OUTPUT_DIR = ROOT / "data/processed/operational_forecasts"
SPATIAL_OUTPUT_DIR = ROOT / "data/processed/spatial_outputs"

LABELED_YEARS = tuple(range(2010, 2025))
CURRENT_FORECAST_YEAR = OPERATIONAL_FORECAST.current_forecast_year


def _forecast_paths(forecast_year: int) -> dict[str, Path]:
    """Stable, separate paths for one annual forecast run."""
    stem = f"forecast_{forecast_year}"
    return {
        "matrix": FORECAST_OUTPUT_DIR / f"{stem}_nine_feature_matrix.parquet",
        "scores": FORECAST_OUTPUT_DIR / f"{stem}_scores.parquet",
        "manifest": FORECAST_OUTPUT_DIR / f"{stem}_manifest.json",
        "gpkg": SPATIAL_OUTPUT_DIR / f"estimated_comparative_wildfire_exposure_{forecast_year}.gpkg",
    }


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary output requires inspection: {temporary}")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    """Publish a derived Parquet artifact only after its temporary write succeeds."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary Parquet requires inspection: {temporary}")
    frame.to_parquet(temporary, index=False, compression="zstd")
    os.replace(temporary, path)


def _write_forecast_geopackage(scores: pd.DataFrame, paths: dict[str, Path], forecast_year: int) -> dict[str, Any]:
    """Publish one spatial score layer from canonical geometry and a score table."""
    grid = pyogrio.read_dataframe(panel.GRID_PATH, columns=["cell_id"])
    spatial = grid.merge(scores, on="cell_id", how="inner", validate="one_to_one")
    if len(spatial) != len(scores) or str(spatial.crs) != "EPSG:3763":
        raise ValueError("QGIS forecast layer failed its canonical-grid join")
    paths["gpkg"].parent.mkdir(parents=True, exist_ok=True)
    temporary_gpkg = paths["gpkg"].with_name(paths["gpkg"].stem + "_temporary.gpkg")
    if temporary_gpkg.exists():
        raise FileExistsError(f"Stale temporary GeoPackage requires inspection: {temporary_gpkg}")
    layer = f"estimated_comparative_exposure_{forecast_year}"
    pyogrio.write_dataframe(spatial, temporary_gpkg, layer=layer, driver="GPKG")
    info = pyogrio.read_info(temporary_gpkg, layer=layer)
    if info["features"] != len(scores) or str(info["crs"]) != "EPSG:3763":
        raise ValueError("Temporary forecast GeoPackage failed validation")
    os.replace(temporary_gpkg, paths["gpkg"])
    return {"path": paths["gpkg"].relative_to(ROOT).as_posix(), "layer": layer, "crs": "EPSG:3763", "feature_count": len(spatial)}


def _source_years(path: Path) -> tuple[int, ...]:
    years = pd.read_parquet(path, columns=["observation_year"])["observation_year"]
    return tuple(sorted(int(year) for year in years.unique()))


def _validate_source_matrix(path: Path, expected_years: tuple[int, ...]) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Required validated source matrix is missing: {path}")
    parquet = pq.ParquetFile(path)
    required = set(PREDICTOR_COLUMNS) | {TARGET_COLUMN, "cell_id", "cell_year_id", "observation_year", "outcome_year"}
    missing = required.difference(parquet.schema.names)
    if missing:
        raise ValueError(f"Source matrix lacks required fields: {sorted(missing)}")
    years = _source_years(path)
    if years != expected_years:
        raise ValueError(f"Unexpected years in {path.name}: {years}")


def build_labeled_nine_feature_panel() -> dict[str, Any]:
    """Concatenate the validated development and final-test matrices safely.

    This is a no-recalculation operation: all existing target values are copied
    byte-for-byte at value level from the validated source matrices.  The two
    inputs cover consecutive years and are already deterministically ordered.
    """
    sources = (
        (DEVELOPMENT_MATRIX_PATH, tuple(range(2010, 2022))),
        (FINAL_TEST_MATRIX_PATH, tuple(range(2022, 2025))),
    )
    for path, years in sources:
        _validate_source_matrix(path, years)
    expected_rows = sum(pq.ParquetFile(path).metadata.num_rows for path, _ in sources)

    if LABELED_PANEL_PATH.exists() or PANEL_MANIFEST_PATH.exists():
        if not (LABELED_PANEL_PATH.exists() and PANEL_MANIFEST_PATH.exists()):
            raise FileExistsError("Incomplete labelled-panel output requires inspection")
        manifest = json.loads(PANEL_MANIFEST_PATH.read_text(encoding="utf-8"))
        if _sha256(LABELED_PANEL_PATH) != manifest["sha256"]:
            raise ValueError("Existing labelled panel checksum changed")
        if pq.ParquetFile(LABELED_PANEL_PATH).metadata.num_rows != expected_rows:
            raise ValueError("Existing labelled panel row count changed")
        if _source_years(LABELED_PANEL_PATH) != LABELED_YEARS:
            raise ValueError("Existing labelled panel years changed")
        return manifest | {"status": "validated_reused"}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporary = LABELED_PANEL_PATH.with_suffix(".parquet.tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary output requires inspection: {temporary}")
    writer: pq.ParquetWriter | None = None
    try:
        for path, _ in sources:
            source = pq.ParquetFile(path)
            for row_group in range(source.num_row_groups):
                table = source.read_row_group(row_group)
                if writer is None:
                    writer = pq.ParquetWriter(temporary, table.schema, compression="zstd")
                elif table.schema != writer.schema:
                    raise ValueError("Validated nine-feature matrices have incompatible schemas")
                writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()
    if not temporary.exists():
        raise RuntimeError("Labelled-panel write did not produce an output")
    if pq.ParquetFile(temporary).metadata.num_rows != expected_rows:
        raise ValueError("Labelled-panel row count mismatch")
    if _source_years(temporary) != LABELED_YEARS:
        raise ValueError("Labelled-panel year range mismatch")
    os.replace(temporary, LABELED_PANEL_PATH)
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "path": LABELED_PANEL_PATH.relative_to(ROOT).as_posix(),
        "sha256": _sha256(LABELED_PANEL_PATH),
        "row_count": expected_rows,
        "observation_years": list(LABELED_YEARS),
        "target": TARGET_COLUMN,
        "feature_order": list(PREDICTOR_COLUMNS),
        "sources": [
            {"path": path.relative_to(ROOT).as_posix(), "sha256": _sha256(path), "years": list(years)}
            for path, years in sources
        ],
        "target_lineage": "Copied from validated ICNF T+1 labels; no target recalculation performed.",
    }
    _atomic_json(manifest, PANEL_MANIFEST_PATH)
    return manifest | {"status": "created"}


def refit_operational_model() -> dict[str, Any]:
    """Refit the frozen selected specification through observed outcome 2025."""
    panel_manifest = build_labeled_nine_feature_panel()
    columns = ["observation_year", *PREDICTOR_COLUMNS, TARGET_COLUMN]
    frame = pd.read_parquet(LABELED_PANEL_PATH, columns=columns)
    if tuple(sorted(int(year) for year in frame.observation_year.unique())) != LABELED_YEARS:
        raise ValueError("Operational refit does not have exactly T=2010-2024 labels")
    if frame[list(PREDICTOR_COLUMNS) + [TARGET_COLUMN]].isna().any().any():
        raise ValueError("Operational refit source contains missing model values")
    if not np.isfinite(frame[list(PREDICTOR_COLUMNS) + [TARGET_COLUMN]].to_numpy(dtype="float64")).all():
        raise ValueError("Operational refit source contains non-finite model values")
    model = HurdleHistGradientRegressor()
    with threadpool_limits(limits=1, user_api="openmp"):
        model.fit(frame.loc[:, PREDICTOR_COLUMNS], frame[TARGET_COLUMN])
    sample = frame.loc[:999, PREDICTOR_COLUMNS]
    expected = model.predict(sample)
    if MODEL_PATH.exists() and MODEL_METADATA_PATH.exists():
        existing_metadata = json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))
        existing_payload = joblib.load(MODEL_PATH)
        existing_panel = existing_metadata.get("labelled_panel", {})
        same_lineage = (
            existing_panel.get("sha256") == panel_manifest.get("sha256")
            and existing_payload.get("feature_order") == list(PREDICTOR_COLUMNS)
            and existing_payload.get("training_predictor_years") == list(LABELED_YEARS)
            and existing_payload.get("target") == TARGET_COLUMN
        )
        if same_lineage:
            existing = np.asarray(existing_payload["model"].predict(sample), dtype="float64")
            if np.array_equal(expected, existing):
                return existing_metadata | {"status": "validated_reused"}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporary = MODEL_PATH.with_suffix(".joblib.tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary output requires inspection: {temporary}")
    payload = {
        "model": model,
        "model_name": "nine_feature_hurdle",
        "feature_order": list(PREDICTOR_COLUMNS),
        "training_predictor_years": list(LABELED_YEARS),
        "training_observed_outcome_years": list(range(2011, 2026)),
        "target": TARGET_COLUMN,
        "random_seed": RANDOM_SEED,
        "selection_evidence": "reports/validation/final_temporal_test_2022_2024.md",
        "specification_status": "frozen before final test; refit only after final test was recorded",
        "output_interpretation": "continuous comparative estimated burned share; not a probability, safety guarantee, or purchase recommendation",
    }
    joblib.dump(payload, temporary)
    os.replace(temporary, MODEL_PATH)
    reloaded = joblib.load(MODEL_PATH)["model"].predict(sample)
    if not np.array_equal(expected, reloaded):
        raise ValueError("Reloaded operational model changes predictions")
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model_path": MODEL_PATH.relative_to(ROOT).as_posix(),
        "model_sha256": _sha256(MODEL_PATH),
        "row_count": len(frame),
        "training_predictor_years": list(LABELED_YEARS),
        "training_observed_outcome_years": list(range(2011, 2026)),
        "feature_order": list(PREDICTOR_COLUMNS),
        "target": TARGET_COLUMN,
        "selection_evidence": payload["selection_evidence"],
        "reload_sample_predictions_identical": True,
        "next_operational_forecast_year": CURRENT_FORECAST_YEAR,
        "forecast_prerequisite": "validated T=2025 ERA5-Land JJAS inputs",
        "labelled_panel": panel_manifest,
    }
    _atomic_json(metadata, MODEL_METADATA_PATH)
    return metadata


def forecast_preflight(forecast_year: int = CURRENT_FORECAST_YEAR) -> dict[str, Any]:
    """Verify input availability for a future score without deriving values."""
    predictor_year = OPERATIONAL_FORECAST.predictor_year(forecast_year)
    latest_label = OPERATIONAL_FORECAST.latest_labeled_predictor_year(forecast_year)
    history_years = OPERATIONAL_FORECAST.history_years(forecast_year)
    required_icnf_years = (*history_years, latest_label + 1)
    missing: list[dict[str, str]] = []

    climate = ERA5_LAND_AVAILABLE_ARCHIVES.get(predictor_year)
    if climate is None:
        missing.append({"kind": "ERA5-Land JJAS", "year": str(predictor_year), "reason": "no validated source-registry record"})
    elif not (ROOT / climate.raw_path).is_file():
        missing.append({"kind": "ERA5-Land JJAS", "year": str(predictor_year), "reason": f"registered file missing: {climate.raw_path}"})

    for year in sorted(set(required_icnf_years)):
        record = EXTENDED_TRAINING_ICNF_ARCHIVES.get(year)
        if record is None:
            missing.append({"kind": "ICNF annual burned area", "year": str(year), "reason": "no source-registry record"})
        elif not (ROOT / record.raw_path).is_file():
            missing.append({"kind": "ICNF annual burned area", "year": str(year), "reason": f"registered file missing: {record.raw_path}"})

    clc_record = CLC_PREPARED_PORTUGAL_LAYERS[2018]
    for required_path, label in (
        (ROOT / clc_record.prepared_path, "prepared CLC 2018 Portugal layer"),
        (panel.GRID_CATALOG_PATH, "canonical grid catalogue"),
        (panel.ERA5_FALLBACK_MAPPING_PATH, "accepted ERA5 coastal fallback map"),
        (MODEL_PATH, "refitted nine-feature model"),
    ):
        if not required_path.is_file():
            missing.append({"kind": label, "year": "n/a", "reason": f"missing: {required_path.relative_to(ROOT)}"})

    result = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_year": forecast_year,
        "predictor_year": predictor_year,
        "latest_labeled_predictor_year": latest_label,
        "latest_observed_outcome_year": OPERATIONAL_FORECAST.latest_observed_outcome_year(forecast_year),
        "historical_fire_years": list(history_years),
        "feature_count": OPERATIONAL_FORECAST.feature_count,
        "target_present_in_scoring_input": False,
        "status": "ready_for_feature_derivation" if not missing else "blocked_missing_inputs",
        "missing_inputs": missing,
        "prohibited_sources": [f"ICNF {forecast_year}", f"ERA5-Land {forecast_year}", "any observed outcome after the scoring cutoff"],
    }
    _atomic_json(result, PREFLIGHT_PATH)
    return result


def _load_scoring_climate_grids(predictor_year: int) -> dict[str, np.ndarray]:
    """Read a small annual ERA5 grid once; all cell assignment stays bounded."""
    paths = era5_source_paths(predictor_year)
    latitude, longitude, temperature, months = read_grib_variable(paths["temperature_and_soil_water"], "2t")
    soil_lat, soil_lon, soil, soil_months = read_grib_variable(paths["temperature_and_soil_water"], "swvl1")
    precip_lat, precip_lon, precipitation, precip_months = read_grib_variable(paths["precipitation"], "tp")
    if not (
        months == soil_months == precip_months == (6, 7, 8, 9)
        and np.array_equal(latitude, soil_lat) and np.array_equal(latitude, precip_lat)
        and np.array_equal(longitude, soil_lon) and np.array_equal(longitude, precip_lon)
    ):
        raise ValueError(f"ERA5-Land grid/month mismatch for scoring T={predictor_year}")
    with warnings.catch_warnings(), np.errstate(invalid="ignore"):
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return {
            "latitude": latitude,
            "longitude": longitude,
            "warm_season_mean_2m_temperature_c": np.nanmean(temperature, axis=0) - 273.15,
            "warm_season_total_precipitation_mm": jjas_total_precipitation_mm(precipitation, months),
            "warm_season_mean_soil_water_layer1": np.nanmean(soil, axis=0),
            "warm_season_max_monthly_2m_temperature_c": np.nanmax(temperature, axis=0) - 273.15,
            "warm_season_min_monthly_soil_water_layer1": np.nanmin(soil, axis=0),
        }


def _derive_scoring_batch(batch_id: str, predictor_year: int, climate: dict[str, np.ndarray], fallback: pd.DataFrame) -> pd.DataFrame:
    """Build one deterministic spatial batch without a target column."""
    grid = pd.read_parquet(
        panel._grid_batch_path(batch_id), columns=["cell_id", "centroid_latitude", "centroid_longitude"]
    )
    cell_ids = grid.cell_id.to_numpy()
    slope = pd.read_parquet(panel._component_batch_path(panel.SLOPE_BATCH_DIR, "slope", batch_id)).set_index("cell_id")
    clc = pd.read_parquet(
        panel._component_batch_path(panel.CLC_BATCH_DIR / "2018", "clc_2018", batch_id)
    ).set_index("cell_id")
    icnf = pd.read_parquet(panel._component_batch_path(panel.ICNF_BATCH_DIR, "icnf", batch_id)).set_index("cell_id")
    history = OPERATIONAL_FORECAST.history_years(predictor_year + 1)
    historical_count = icnf.loc[cell_ids, [f"context_{year}" for year in history]].sum(axis=1).astype("int8").to_numpy()

    latitudes = grid.centroid_latitude.to_numpy()
    longitudes = grid.centroid_longitude.to_numpy()
    lat_index = np.abs(climate["latitude"][:, None] - latitudes).argmin(axis=0)
    lon_index = np.abs(climate["longitude"][:, None] - longitudes).argmin(axis=0)
    climate_columns = CLIMATE_PREDICTOR_COLUMNS
    assigned = {
        name: np.asarray(climate[name])[lat_index, lon_index].astype("float64")
        for name in climate_columns
    }
    masked = np.isnan(assigned["warm_season_mean_2m_temperature_c"])
    for name in climate_columns[1:]:
        if not np.array_equal(np.isnan(assigned[name]), masked):
            raise ValueError(f"ERA5 water mask differs across fields for scoring {batch_id}")
    method = np.full(len(grid), "containing_valid_era5_land_cell", dtype=object)
    for position in np.flatnonzero(masked):
        cell_id = cell_ids[position]
        if cell_id not in fallback.index:
            raise ValueError(f"No accepted ERA5 fallback for scoring {cell_id}")
        flat_index = int(fallback.loc[cell_id, "fallback_flat_index"])
        for name in climate_columns:
            assigned[name][position] = float(np.asarray(climate[name]).ravel()[flat_index])
        method[position] = "nearest_valid_era5_land_cell"
    if any(np.isnan(values).any() for values in assigned.values()):
        raise ValueError(f"ERA5 fallback left missing scoring climate values in {batch_id}")
    return pd.DataFrame({
        "cell_year_id": cell_ids + np.full(len(cell_ids), f"_{predictor_year}", dtype=object),
        "cell_id": cell_ids,
        "observation_year": np.full(len(cell_ids), predictor_year, dtype="int16"),
        "outcome_year": np.full(len(cell_ids), predictor_year + 1, dtype="int16"),
        "historical_fire_start_year": np.full(len(cell_ids), history[0], dtype="int16"),
        "historical_fire_end_year": np.full(len(cell_ids), history[-1], dtype="int16"),
        "climate_reference_year": np.full(len(cell_ids), predictor_year, dtype="int16"),
        "land_cover_reference_year": np.full(len(cell_ids), 2018, dtype="int16"),
        "land_cover_release_id": CLC_2018_V2020_20U1.release_id,
        "land_cover_release_date": CLC_2018_V2020_20U1.release_date,
        "terrain_release_id": COP_DEM_GLO30.release_id,
        "built_up_share": clc.loc[cell_ids, "built_up_share"].to_numpy(dtype="float64"),
        "forest_shrub_share_2km": clc.loc[cell_ids, "forest_shrub_share_2km"].to_numpy(dtype="float64"),
        "mean_slope_2km": slope.loc[cell_ids, "mean_slope_2km"].to_numpy(dtype="float64"),
        "fire_years_previous_10y_2km": historical_count,
        **assigned,
        "climate_assignment_method": method,
    }).sort_values("cell_id", kind="mergesort").reset_index(drop=True)


def _validate_scoring_matrix(frame: pd.DataFrame, forecast_year: int, expected_cells: int) -> None:
    predictor_year = OPERATIONAL_FORECAST.predictor_year(forecast_year)
    if len(frame) != expected_cells or not frame.cell_id.is_unique:
        raise ValueError("Scoring matrix does not contain exactly one row per canonical cell")
    if TARGET_COLUMN in frame.columns:
        raise ValueError("Scoring matrix must not contain an unknown future target")
    if not frame.observation_year.eq(predictor_year).all() or not frame.outcome_year.eq(forecast_year).all():
        raise ValueError("Scoring temporal alignment is invalid")
    if not frame.historical_fire_start_year.eq(predictor_year - 10).all() or not frame.historical_fire_end_year.eq(predictor_year - 1).all():
        raise ValueError("Scoring fire-history window is invalid")
    if not frame.climate_reference_year.eq(predictor_year).all() or not frame.land_cover_reference_year.eq(2018).all():
        raise ValueError("Scoring source years are invalid")
    if frame[list(PREDICTOR_COLUMNS)].isna().any().any() or not np.isfinite(frame[list(PREDICTOR_COLUMNS)].to_numpy(dtype="float64")).all():
        raise ValueError("Scoring features contain missing or non-finite values")
    for column in ("built_up_share", "forest_shrub_share_2km"):
        if not frame[column].between(0.0, 1.0).all():
            raise ValueError(f"Scoring {column} is outside [0, 1]")
    if not frame.mean_slope_2km.between(0.0, 90.0).all():
        raise ValueError("Scoring slope is outside [0, 90]")
    if not frame.fire_years_previous_10y_2km.between(0, 10).all():
        raise ValueError("Scoring fire-history count is outside [0, 10]")


def build_scoring_matrix(forecast_year: int = CURRENT_FORECAST_YEAR, progress=print) -> dict[str, Any]:
    """Derive the unlabelled nine-feature matrix in bounded spatial batches."""
    preflight = forecast_preflight(forecast_year)
    if preflight["status"] != "ready_for_feature_derivation":
        raise RuntimeError(f"Forecast {forecast_year} is not ready: {preflight['missing_inputs']}")
    paths = _forecast_paths(forecast_year)
    if paths["matrix"].exists():
        frame = pd.read_parquet(paths["matrix"])
        _validate_scoring_matrix(frame, forecast_year, panel.load_grid_catalog()["cell_count"])
        return {"path": paths["matrix"].relative_to(ROOT).as_posix(), "sha256": _sha256(paths["matrix"]), "row_count": len(frame), "status": "validated_reused"}
    climate = _load_scoring_climate_grids(preflight["predictor_year"])
    fallback = panel._load_era5_fallback_mapping()
    catalog = panel.load_grid_catalog()
    frames: list[pd.DataFrame] = []
    for number, batch in enumerate(catalog["batches"], start=1):
        frame = _derive_scoring_batch(batch["batch_id"], preflight["predictor_year"], climate, fallback)
        frames.append(frame)
        progress(f"Forecast {forecast_year} features {batch['batch_id']}: {len(frame)} cells ({number}/{catalog['batch_count']})")
    result = pd.concat(frames, ignore_index=True).sort_values("cell_id", kind="mergesort").reset_index(drop=True)
    _validate_scoring_matrix(result, forecast_year, catalog["cell_count"])
    paths["matrix"].parent.mkdir(parents=True, exist_ok=True)
    temporary = paths["matrix"].with_suffix(".parquet.tmp")
    result.to_parquet(temporary, index=False, compression="zstd")
    os.replace(temporary, paths["matrix"])
    return {"path": paths["matrix"].relative_to(ROOT).as_posix(), "sha256": _sha256(paths["matrix"]), "row_count": len(result), "status": "created"}


def score_forecast(forecast_year: int = CURRENT_FORECAST_YEAR) -> dict[str, Any]:
    """Apply the saved fixed model and create table plus one QGIS-ready layer."""
    matrix = build_scoring_matrix(forecast_year)
    paths = _forecast_paths(forecast_year)
    if paths["scores"].exists() or paths["gpkg"].exists():
        raise FileExistsError(f"Forecast {forecast_year} output already exists; inspect rather than overwrite")
    payload = joblib.load(MODEL_PATH)
    if tuple(payload["feature_order"]) != PREDICTOR_COLUMNS:
        raise ValueError("Saved operational model feature order differs from scoring contract")
    frame = pd.read_parquet(paths["matrix"])
    predictions = np.asarray(payload["model"].predict(frame.loc[:, PREDICTOR_COLUMNS]), dtype="float64")
    if not np.isfinite(predictions).all() or predictions.min() < 0.0 or predictions.max() > 1.0:
        raise ValueError("Operational model produced invalid continuous burned-share estimates")
    scores = frame[["cell_id", "observation_year", "outcome_year", "climate_assignment_method"]].copy()
    scores = scores.rename(columns={"observation_year": "prediction_input_year", "outcome_year": "forecast_year"})
    scores["predicted_burned_share_next_year"] = predictions
    # Higher predicted share means higher percentile. Ties receive the same
    # average percentile rather than an arbitrary order by cell identifier.
    scores["predicted_exposure_percentile"] = scores["predicted_burned_share_next_year"].rank(method="average", pct=True)
    scores["model_sha256"] = _sha256(MODEL_PATH)
    scores["score_status"] = "scored_comparative_estimate"
    _atomic_parquet(scores, paths["scores"])
    spatial_output = _write_forecast_geopackage(scores, paths, forecast_year)
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_year": forecast_year,
        "prediction_input_year": forecast_year - 1,
        "target_present": False,
        "feature_matrix": matrix,
        "score_table": {"path": paths["scores"].relative_to(ROOT).as_posix(), "sha256": _sha256(paths["scores"]), "row_count": len(scores)},
        "spatial_output": spatial_output,
        "model": {"path": MODEL_PATH.relative_to(ROOT).as_posix(), "sha256": _sha256(MODEL_PATH), "feature_order": list(PREDICTOR_COLUMNS)},
        "input_sources": {
            "era5_land": {
                "year": forecast_year - 1,
                "path": ERA5_LAND_AVAILABLE_ARCHIVES[forecast_year - 1].raw_path,
                "sha256": ERA5_LAND_AVAILABLE_ARCHIVES[forecast_year - 1].sha256,
            },
            "icnf_historical_years": list(OPERATIONAL_FORECAST.history_years(forecast_year)),
            "clc_reference_year": 2018,
            "terrain_release_id": COP_DEM_GLO30.release_id,
        },
        "prediction_summary": {
            "minimum": float(predictions.min()), "median": float(np.median(predictions)),
            "mean": float(predictions.mean()), "maximum": float(predictions.max()),
            "zero_count": int((predictions == 0.0).sum()),
        },
        "interpretation": "continuous comparative estimated burned share; not a probability, safety guarantee, or purchase recommendation",
    }
    _atomic_json(manifest, paths["manifest"])
    return manifest


def _reconcile_score_model_provenance(
    *, paths: dict[str, Path], manifest: dict[str, Any], scores: pd.DataFrame, forecast_year: int, current_model_sha256: str
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Update only model-provenance fields after exact prediction equivalence.

    A deterministic refit can serialize to different bytes across runs even
    when every prediction is identical.  This recovery is intentionally narrow:
    callers must prove equality before it updates the score checksum, manifest,
    and QGIS attribute table.  No score value, raw input, or model setting is
    changed.
    """
    recorded_checksums = sorted(str(value) for value in scores.model_sha256.dropna().unique())
    if len(recorded_checksums) != 1:
        raise ValueError("Forecast score table has multiple model checksums")
    reconciled = scores.copy()
    reconciled["model_sha256"] = current_model_sha256
    _atomic_parquet(reconciled, paths["scores"])
    spatial_output = _write_forecast_geopackage(reconciled, paths, forecast_year)
    updated_manifest = dict(manifest)
    updated_model = dict(updated_manifest.get("model", {}))
    updated_model["sha256"] = current_model_sha256
    updated_manifest["model"] = updated_model
    updated_score_table = dict(updated_manifest.get("score_table", {}))
    updated_score_table["sha256"] = _sha256(paths["scores"])
    updated_score_table["row_count"] = len(reconciled)
    updated_manifest["score_table"] = updated_score_table
    updated_manifest["spatial_output"] = spatial_output
    updated_manifest["model_provenance_reconciliation"] = {
        "reconciled_utc": datetime.now(timezone.utc).isoformat(),
        "current_model_sha256": current_model_sha256,
        "reason": "current serialized-model checksum was recorded only after exact prediction equivalence was verified",
        "score_values_changed": False,
    }
    _atomic_json(updated_manifest, paths["manifest"])
    return updated_manifest, reconciled


def validate_forecast_artifacts(forecast_year: int = CURRENT_FORECAST_YEAR) -> dict[str, Any]:
    """Validate a completed annual score without rebuilding its inputs."""
    paths = _forecast_paths(forecast_year)
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(f"Missing forecast artifact: {path}")
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    matrix = pd.read_parquet(paths["matrix"])
    _validate_scoring_matrix(matrix, forecast_year, panel.load_grid_catalog()["cell_count"])
    scores = pd.read_parquet(paths["scores"])
    required_score_columns = {
        "cell_id", "prediction_input_year", "forecast_year", "climate_assignment_method",
        "predicted_burned_share_next_year", "predicted_exposure_percentile", "model_sha256", "score_status",
    }
    if set(scores.columns) != required_score_columns or len(scores) != len(matrix) or not scores.cell_id.is_unique:
        raise ValueError("Forecast score table schema/identity mismatch")
    if not scores.forecast_year.eq(forecast_year).all() or not scores.prediction_input_year.eq(forecast_year - 1).all():
        raise ValueError("Forecast score table has incorrect temporal fields")
    if scores.isna().any().any() or not scores.predicted_burned_share_next_year.between(0.0, 1.0).all():
        raise ValueError("Forecast score table has missing/out-of-range estimates")
    if not scores.predicted_exposure_percentile.between(0.0, 1.0).all():
        raise ValueError("Forecast percentile is outside [0, 1]")
    current_model_sha256 = _sha256(MODEL_PATH)
    payload = joblib.load(MODEL_PATH)
    reloaded_predictions = np.asarray(payload["model"].predict(matrix.loc[:, PREDICTOR_COLUMNS]), dtype="float64")
    ordered_scores = scores.set_index("cell_id").loc[matrix.cell_id, "predicted_burned_share_next_year"].to_numpy(dtype="float64")
    if not np.array_equal(reloaded_predictions, ordered_scores):
        raise ValueError("Reloaded model does not reproduce the published forecast values")
    model_checksum_reconciled = False
    provenance_mismatch = (
        not scores.model_sha256.eq(current_model_sha256).all()
        or manifest.get("model", {}).get("sha256") != current_model_sha256
        or manifest.get("score_table", {}).get("sha256") != _sha256(paths["scores"])
        or "previous_model_sha256" in manifest.get("model_provenance_reconciliation", {})
    )
    if provenance_mismatch:
        manifest, scores = _reconcile_score_model_provenance(
            paths=paths,
            manifest=manifest,
            scores=scores,
            forecast_year=forecast_year,
            current_model_sha256=current_model_sha256,
        )
        model_checksum_reconciled = True
    if manifest.get("model", {}).get("sha256") != current_model_sha256:
        raise ValueError("Forecast manifest model checksum mismatch")
    if manifest.get("score_table", {}).get("sha256") != _sha256(paths["scores"]):
        raise ValueError("Forecast manifest score-table checksum mismatch")
    spatial_info = pyogrio.read_info(paths["gpkg"], layer=manifest["spatial_output"]["layer"])
    if spatial_info["features"] != len(matrix) or str(spatial_info["crs"]) != "EPSG:3763":
        raise ValueError("Forecast GeoPackage CRS or feature count mismatch")
    return {
        "forecast_year": forecast_year,
        "row_count": len(matrix),
        "target_present": TARGET_COLUMN in matrix.columns,
        "matrix_missing_values": int(matrix.isna().sum().sum()),
        "score_missing_values": int(scores.isna().sum().sum()),
        "model_reload_predictions_identical": True,
        "model_checksum_reconciled": model_checksum_reconciled,
        "spatial_layer": manifest["spatial_output"],
        "prediction_summary": manifest["prediction_summary"],
        "climate_assignment_counts": scores.climate_assignment_method.value_counts().sort_index().to_dict(),
        "matrix_sha256": _sha256(paths["matrix"]),
        "scores_sha256": _sha256(paths["scores"]),
    }


def write_forecast_validation_report(validation: dict[str, Any]) -> None:
    """Record exactly what was published, without creating a future outcome claim."""
    summary = validation["prediction_summary"]
    spatial = validation["spatial_layer"]
    lines = [
        "# Operational forecast 2026 validation",
        "",
        "## Contract",
        "",
        "- Forecast year: 2026; predictor/input year: 2025.",
        "- The scoring matrix contains the nine fixed predictors and intentionally contains no observed `burned_share_next_year` target.",
        "- ICNF history is 2015-2024 only; no ICNF 2026 or 2027 record was read for scoring.",
        "- ERA5-Land context is validated JJAS 2025, assigned by containing valid coarse cell or the existing nearest-valid-land fallback. It is not downscaled or interpolated.",
        "",
        "## Published artifacts",
        "",
        f"- Feature matrix: `data/processed/operational_forecasts/forecast_2026_nine_feature_matrix.parquet` ({validation['row_count']:,} rows; SHA-256 `{validation['matrix_sha256']}`).",
        f"- Score table: `data/processed/operational_forecasts/forecast_2026_scores.parquet` ({validation['row_count']:,} rows; SHA-256 `{validation['scores_sha256']}`).",
        f"- QGIS-ready layer: `{spatial['path']}`, layer `{spatial['layer']}`, {spatial['feature_count']:,} EPSG:3763 features.",
        "",
        "## Validation",
        "",
        f"- Unique cells/rows: {validation['row_count']:,}; target present: {validation['target_present']}; matrix missing values: {validation['matrix_missing_values']}; score missing values: {validation['score_missing_values']}.",
        f"- Reloaded model predictions identical to published scores: {validation['model_reload_predictions_identical']}.",
        f"- Model-provenance checksum reconciled after exact prediction equivalence: {validation['model_checksum_reconciled']}.",
        f"- Climate assignment counts: {validation['climate_assignment_counts']}.",
        f"- Estimated burned-share summary: min {summary['minimum']:.6f}; median {summary['median']:.6f}; mean {summary['mean']:.6f}; max {summary['maximum']:.6f}; exact-zero estimates {summary['zero_count']:,}.",
        "",
        "## Interpretation and limitation",
        "",
        "This is a year-specific comparative estimated burned share for broad 1 km mainland cells. It is not a probability, property-level forecast, safety guarantee, insurance estimate, or purchase recommendation. The fixed model underpredicted the high observed outcome associated with T=2024 during final evaluation; use ranks and estimates cautiously alongside the historical recurrence layer and official/local information.",
    ]
    FORECAST_VALIDATION_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_operational_forecast(forecast_year: int = CURRENT_FORECAST_YEAR) -> dict[str, Any]:
    """Create an annual score once, or revalidate the immutable published result.

    A rerun deliberately never overwrites a published score.  If all four
    artifacts exist it performs the same validation and reload check instead;
    a partial set is an actionable failure rather than an invitation to mix
    runs.
    """
    paths = _forecast_paths(forecast_year)
    present = {name: path.is_file() for name, path in paths.items()}
    if any(present.values()) and not all(present.values()):
        absent = [name for name, exists in present.items() if not exists]
        raise RuntimeError(
            f"Forecast {forecast_year} has incomplete artifacts; missing {absent}. "
            "Inspect the prior run before attempting recovery."
        )
    manifest = (
        json.loads(paths["manifest"].read_text(encoding="utf-8"))
        if all(present.values())
        else score_forecast(forecast_year)
    )
    validation = validate_forecast_artifacts(forecast_year)
    # Validation may have reconciled derived provenance after proving exact
    # prediction equality, so return the persisted manifest rather than a
    # stale pre-validation copy.
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    write_forecast_validation_report(validation)
    return {"status": "validated_reused" if all(present.values()) else "created_and_validated", "manifest": manifest, "validation": validation}


def write_readiness_report(model_metadata: dict[str, Any], preflight: dict[str, Any]) -> None:
    missing = preflight["missing_inputs"]
    paths = _forecast_paths(preflight["forecast_year"])
    scored = preflight["status"] == "ready_for_feature_derivation" and all(path.is_file() for path in paths.values())
    status = "scored_and_validated" if scored else preflight["status"]
    lines = [
        "# Operational annual forecast readiness",
        "",
        "## Fixed model",
        "",
        f"- Model: fixed nine-feature hurdle refit on predictor years T={LABELED_YEARS[0]}-{LABELED_YEARS[-1]}, with observed ICNF outcomes 2011-2025.",
        f"- Artifact: `{model_metadata['model_path']}` (SHA-256 `{model_metadata['model_sha256']}`).",
        "- Model selection remains the completed frozen T=2022-2024 final temporal test; no post-test tuning occurred.",
        "",
        f"## {preflight['forecast_year']} scoring contract",
        "",
        f"- Predictor year: T={preflight['predictor_year']}; estimated outcome year: {preflight['forecast_year']}.",
        f"- ICNF historical-fire years: {min(preflight['historical_fire_years'])}-{max(preflight['historical_fire_years'])} only.",
        "- The scoring matrix has all nine predictors and intentionally has no `burned_share_next_year` value.",
        "- ERA5-Land remains coarse containing-cell context, with the accepted nearest-valid-land fallback where required; it is not interpolated or downscaled.",
        "",
        "## Current readiness",
        "",
        f"**Status: `{status}`.**",
    ]
    if missing:
        lines.extend(["", "### Required before deriving the score", "", "| Source | Year | Reason |", "|---|---:|---|"])
        lines.extend(f"| {item['kind']} | {item['year']} | {item['reason']} |" for item in missing)
    elif scored:
        lines.append(
            f"All sources passed validation and the {preflight['forecast_year']} matrix, score table, and QGIS-ready GeoPackage were published. See `operational_forecast_{preflight['forecast_year']}_validation.md`."
        )
    else:
        lines.append("All sources are present; derive the scoring matrix and publish the forecast GeoPackage only after its validations pass.")
    lines.extend([
        "",
        "## Annual rebuild rule",
        "",
        "For forecast year Y, freeze the selected specification, refit only through labelled predictor year Y-2 (whose observed target is Y-1), derive predictors from Y-1, then score Y. Record every source checksum and do not calculate or use the unknown target for Y.",
        "",
        "## Annual score artifacts",
        "",
        f"- `data/processed/operational_forecasts/forecast_{preflight['forecast_year']}_nine_feature_matrix.parquet`: one unlabelled row per 1 km cell, with all nine predictors and source metadata.",
        f"- `data/processed/operational_forecasts/forecast_{preflight['forecast_year']}_scores.parquet`: `cell_id`, forecast/input years, continuous estimate, rank metadata, model checksum, and score status.",
        f"- `data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_{preflight['forecast_year']}.gpkg`: one EPSG:3763 geometry per canonical cell joined to the score table; it does not repeat the complete cell-year panel.",
        "",
        "## Buyer-facing interpretation",
        "",
        "A published score may compare broad 1 km mainland cells by estimated wildfire exposure for the stated year. It is not a property-level forecast, probability, safety guarantee, insurance quote, or buy/do-not-buy recommendation. Historical recurrence remains contextual evidence alongside, not a substitute for, the forecast layer.",
    ])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_current_operational_preparation() -> dict[str, Any]:
    """Build the reusable model and write the gated current-year readiness record."""
    model_metadata = refit_operational_model()
    preflight = forecast_preflight(CURRENT_FORECAST_YEAR)
    write_readiness_report(model_metadata, preflight)
    return {"model": model_metadata, "preflight": preflight, "report": REPORT_PATH.relative_to(ROOT).as_posix()}
