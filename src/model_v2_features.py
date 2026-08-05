"""Bounded, train/validation-only feature extensions for V2 experiments.

The canonical seven-feature panel remains immutable.  This module derives a
small, explicit set of additions from the already validated intermediate
components and raw, governed source layers.  It never reads final-test panel
row groups and it does not change the feature contract used for the national
panel.
"""

from __future__ import annotations

import gc
import json
import os
import time
from pathlib import Path
from typing import Callable
import warnings

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds
from shapely.geometry import mapping

from src.clc_validation import CANONICAL_CLC_CLASS_MAPPING
from src.config import CLC, SPATIAL
from src.feature_contract import PREDICTOR_COLUMNS, TARGET_COLUMN
from src.model_selection import (
    MODEL_SELECTION_YEARS,
    PANEL_PATH,
    read_train_validation_rows,
    validate_model_selection_frame,
)
from src import national_panel as panel
from src.representative_feature_pilot import _read_grib_variable, era5_source_paths
from src.source_registry import CLC_PREPARED_PORTUGAL_LAYERS


ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / "data/interim/model_v2_features"
ICNF_EXTENSION_DIR = BUILD_ROOT / "icnf"
CLC_EXTENSION_DIR = BUILD_ROOT / "clc"
TERRAIN_EXTENSION_DIR = BUILD_ROOT / "terrain"
CLIMATE_EXTENSION_DIR = BUILD_ROOT / "climate"
FEATURE_MATRIX_PATH = ROOT / "data/processed/model_v2_train_validation_features.parquet"
FEATURE_MATRIX_MANIFEST_PATH = FEATURE_MATRIX_PATH.with_suffix(".parquet.json")

EXTRA_FEATURE_COLUMNS = (
    "years_since_last_context_fire_2km",
    "burned_share_previous_3y_1km",
    "burned_share_previous_10y_1km",
    "agricultural_share_2km",
    "mean_elevation_2km",
    "slope_standard_deviation_2km",
    "warm_season_max_monthly_2m_temperature_c",
    "warm_season_min_monthly_soil_water_layer1",
)

# The ordered groups deliberately avoid redundant 3/5-year context counts and
# near-duplicate maximum/share history summaries.  All groups retain the seven
# validated canonical predictors unchanged.
FEATURE_GROUPS = {
    "baseline_7": PREDICTOR_COLUMNS,
    "icnf_history_10": PREDICTOR_COLUMNS + EXTRA_FEATURE_COLUMNS[:3],
    "icnf_clc_11": PREDICTOR_COLUMNS + EXTRA_FEATURE_COLUMNS[:4],
    "icnf_clc_terrain_13": PREDICTOR_COLUMNS + EXTRA_FEATURE_COLUMNS[:6],
    "full_v2_15": PREDICTOR_COLUMNS + EXTRA_FEATURE_COLUMNS,
}

AGRICULTURAL_CLC_CODES = frozenset({
    "211", "212", "213", "221", "222", "223", "231", "241", "242", "243", "244",
})


def _path(directory: Path, component: str, batch_id: str) -> Path:
    return panel._component_batch_path(directory, component, batch_id)


def _history_extension_frame(icnf: pd.DataFrame, cell_ids: np.ndarray) -> pd.DataFrame:
    """Produce strict prior-only fire summaries for all model-selection years."""
    if not icnf.cell_id.is_unique:
        raise ValueError("ICNF component has duplicate cell identifiers")
    indexed = icnf.set_index("cell_id").loc[cell_ids]
    rows: list[pd.DataFrame] = []
    for year in MODEL_SELECTION_YEARS:
        context_years = list(range(year - 1, year - 11, -1))
        share_3_years = list(range(year - 3, year))
        share_10_years = list(range(year - 10, year))
        context = indexed[[f"context_{item}" for item in context_years]].to_numpy(dtype=bool)
        recency_values = np.arange(1, 11, dtype=np.int8)[:, None]
        years_since = np.where(context.T, recency_values, 11).min(axis=0).astype("int8")
        share_3 = indexed[[f"share_{item}" for item in share_3_years]].sum(axis=1).to_numpy(dtype="float64")
        share_10 = indexed[[f"share_{item}" for item in share_10_years]].sum(axis=1).to_numpy(dtype="float64")
        rows.append(pd.DataFrame({
            "cell_id": cell_ids,
            "observation_year": np.full(len(cell_ids), year, dtype="int16"),
            "years_since_last_context_fire_2km": years_since,
            "burned_share_previous_3y_1km": share_3,
            "burned_share_previous_10y_1km": share_10,
        }))
    return pd.concat(rows, ignore_index=True)


def derive_icnf_extension_batch(batch_id: str) -> pd.DataFrame:
    grid = pd.read_parquet(panel._grid_batch_path(batch_id), columns=["cell_id"])
    icnf = pd.read_parquet(_path(panel.ICNF_BATCH_DIR, "icnf", batch_id))
    return _history_extension_frame(icnf, grid.cell_id.to_numpy())


def build_icnf_extensions(progress: Callable[[str], None] = print) -> dict[str, int]:
    catalog = panel.load_grid_catalog()
    created = reused = 0
    for number, batch in enumerate(catalog["batches"], start=1):
        batch_id = batch["batch_id"]
        target = _path(ICNF_EXTENSION_DIR, "history", batch_id)
        expected = batch["row_count"] * len(MODEL_SELECTION_YEARS)
        if panel._validate_existing_batch(target, expected):
            reused += 1
            continue
        frame = derive_icnf_extension_batch(batch_id)
        panel._publish_parquet(frame, target, component="v2_icnf_history", batch_id=batch_id,
                               metadata={"years": MODEL_SELECTION_YEARS, "history_rule": "T-10 through T-1 only"})
        created += 1
        progress(f"V2 ICNF {batch_id}: {len(frame)} rows ({number}/{catalog['batch_count']})")
    return {"created": created, "reused": reused}


def derive_clc_extension_batch(batch_id: str, reference_year: int) -> tuple[pd.DataFrame, dict[str, object]]:
    grid, geometries = panel.load_grid_batch(batch_id)
    record = CLC_PREPARED_PORTUGAL_LAYERS[reference_year]
    code_field = record.validation_facts.class_code_field
    context = gpd.GeoSeries(geometries["context_geometry"], crs=SPATIAL.analysis_crs).to_crs(CLC.area_processing_crs)
    bbox = tuple(float(value) for value in context.total_bounds)
    candidates = pyogrio.read_dataframe(
        ROOT / record.prepared_path, layer=record.validation_facts.layer_name,
        columns=[code_field], bbox=bbox,
    )
    codes = candidates[code_field].astype(str).str.zfill(3)
    selected = candidates.loc[codes.isin(AGRICULTURAL_CLC_CODES)]
    if selected.empty:
        numerators = np.zeros(len(grid), dtype="float64")
    else:
        class_union = shapely.union_all(selected.geometry.to_numpy())
        numerators = shapely.area(shapely.intersection(context.to_numpy(), class_union))
    denominators = shapely.area(context.to_numpy())
    return pd.DataFrame({
        "cell_id": grid.cell_id.to_numpy(),
        "agricultural_share_2km": np.clip(numerators / denominators, 0.0, 1.0),
    }), {"reference_year": reference_year, "candidate_feature_count": len(candidates),
           "selected_agricultural_feature_count": len(selected), "area_processing_crs": CLC.area_processing_crs}


def build_clc_extensions(progress: Callable[[str], None] = print) -> dict[str, int]:
    catalog = panel.load_grid_catalog()
    created = reused = 0
    for reference_year in (2006, 2012, 2018):
        for number, batch in enumerate(catalog["batches"], start=1):
            batch_id = batch["batch_id"]
            target = _path(CLC_EXTENSION_DIR / str(reference_year), f"agricultural_{reference_year}", batch_id)
            if panel._validate_existing_batch(target, batch["row_count"]):
                reused += 1
                continue
            frame, metadata = derive_clc_extension_batch(batch_id, reference_year)
            panel._publish_parquet(frame, target, component=f"v2_agricultural_clc_{reference_year}",
                                   batch_id=batch_id, metadata=metadata)
            progress(f"V2 CLC {reference_year} {batch_id}: {len(frame)} cells, {metadata['candidate_feature_count']} candidates ({number}/{catalog['batch_count']})")
            # GDAL/Shapely allocations can otherwise accumulate across hundreds
            # of GeoPackage bbox reads in a constrained desktop process.
            del frame, metadata
            gc.collect()
            created += 1
    return {"created": created, "reused": reused}


def derive_terrain_extension_batch(batch_id: str) -> tuple[pd.DataFrame, dict[str, object]]:
    grid, geometries = panel.load_grid_batch(batch_id)
    contexts = geometries["context_geometry"]
    bounds = tuple(float(value) for value in shapely.bounds(shapely.union_all(contexts)))
    elevation, slope, transform, dem_tiles = panel._terrain_surfaces(bounds)
    means: list[float] = []
    standard_deviations: list[float] = []
    for cell_id, context in zip(grid.cell_id, contexts, strict=True):
        window = from_bounds(*context.bounds, transform=transform)
        col0, row0 = max(0, int(np.floor(window.col_off))), max(0, int(np.floor(window.row_off)))
        col1 = min(slope.shape[1], int(np.ceil(window.col_off + window.width)))
        row1 = min(slope.shape[0], int(np.ceil(window.row_off + window.height)))
        subset_transform = panel.rasterio.windows.transform(Window(col0, row0, col1-col0, row1-row0), transform)
        mask = geometry_mask([mapping(context)], out_shape=(row1-row0, col1-col0), transform=subset_transform, invert=True)
        values_elevation = elevation[row0:row1, col0:col1]
        values_slope = slope[row0:row1, col0:col1]
        finite = np.isfinite(values_elevation) & np.isfinite(values_slope) & mask
        if not finite.any():
            raise ValueError(f"No finite terrain pixels for {cell_id} in {batch_id}")
        means.append(float(values_elevation[finite].mean()))
        standard_deviations.append(float(values_slope[finite].std(ddof=0)))
    return pd.DataFrame({"cell_id": grid.cell_id.to_numpy(), "mean_elevation_2km": means,
                         "slope_standard_deviation_2km": standard_deviations}), {
        "dem_tiles": dem_tiles, "metric_resolution_metres": panel.DEM_RESOLUTION_METRES,
        "processing_crs": SPATIAL.analysis_crs,
    }


def build_terrain_extensions(progress: Callable[[str], None] = print) -> dict[str, int]:
    catalog = panel.load_grid_catalog()
    created = reused = 0
    for number, batch in enumerate(catalog["batches"], start=1):
        batch_id = batch["batch_id"]
        target = _path(TERRAIN_EXTENSION_DIR, "terrain", batch_id)
        if panel._validate_existing_batch(target, batch["row_count"]):
            reused += 1
            continue
        frame, metadata = derive_terrain_extension_batch(batch_id)
        panel._publish_parquet(frame, target, component="v2_terrain", batch_id=batch_id, metadata=metadata)
        created += 1
        progress(f"V2 terrain {batch_id}: {len(frame)} cells ({number}/{catalog['batch_count']})")
    return {"created": created, "reused": reused}


def _climate_extension_grids() -> dict[int, dict[str, np.ndarray]]:
    grids: dict[int, dict[str, np.ndarray]] = {}
    for year in MODEL_SELECTION_YEARS:
        path = era5_source_paths(year)["temperature_and_soil_water"]
        latitude, longitude, temperature, temperature_months = _read_grib_variable(path, "2t")
        soil_lat, soil_lon, soil, soil_months = _read_grib_variable(path, "swvl1")
        if not (temperature_months == soil_months == (6, 7, 8, 9) and
                np.array_equal(latitude, soil_lat) and np.array_equal(longitude, soil_lon)):
            raise ValueError(f"ERA5 monthly grids do not align for {year}")
        with warnings.catch_warnings(), np.errstate(invalid="ignore"):
            warnings.simplefilter("ignore", category=RuntimeWarning)
            grids[year] = {"latitude": latitude, "longitude": longitude,
                           "warm_season_max_monthly_2m_temperature_c": np.nanmax(temperature, axis=0) - 273.15,
                           "warm_season_min_monthly_soil_water_layer1": np.nanmin(soil, axis=0)}
    return grids


def derive_climate_extension_batch(batch_id: str, grids: dict[int, dict[str, np.ndarray]], fallback: pd.DataFrame) -> pd.DataFrame:
    grid = pd.read_parquet(panel._grid_batch_path(batch_id), columns=["cell_id", "centroid_latitude", "centroid_longitude"])
    rows = []
    for year in MODEL_SELECTION_YEARS:
        source = grids[year]
        lat_index = np.abs(source["latitude"][:, None] - grid.centroid_latitude.to_numpy()).argmin(axis=0)
        lon_index = np.abs(source["longitude"][:, None] - grid.centroid_longitude.to_numpy()).argmin(axis=0)
        temperature = source["warm_season_max_monthly_2m_temperature_c"][lat_index, lon_index].astype("float64")
        soil = source["warm_season_min_monthly_soil_water_layer1"][lat_index, lon_index].astype("float64")
        mask = np.isnan(temperature)
        if not np.array_equal(np.isnan(soil), mask):
            raise ValueError(f"ERA5 monthly-extension water mask differs for {year}/{batch_id}")
        for position in np.flatnonzero(mask):
            cell_id = grid.cell_id.iloc[position]
            if cell_id not in fallback.index:
                raise ValueError(f"No fallback mapping for {cell_id}")
            flat = int(fallback.loc[cell_id, "fallback_flat_index"])
            temperature[position] = float(source["warm_season_max_monthly_2m_temperature_c"].ravel()[flat])
            soil[position] = float(source["warm_season_min_monthly_soil_water_layer1"].ravel()[flat])
        if np.isnan(temperature).any() or np.isnan(soil).any():
            raise ValueError(f"ERA5 fallback left missing V2 climate data for {year}/{batch_id}")
        rows.append(pd.DataFrame({"cell_id": grid.cell_id.to_numpy(),
                                  "observation_year": np.full(len(grid), year, dtype="int16"),
                                  "warm_season_max_monthly_2m_temperature_c": temperature,
                                  "warm_season_min_monthly_soil_water_layer1": soil}))
    return pd.concat(rows, ignore_index=True)


def build_climate_extensions(progress: Callable[[str], None] = print) -> dict[str, int]:
    catalog = panel.load_grid_catalog()
    grids = _climate_extension_grids()
    fallback = panel._load_era5_fallback_mapping()
    created = reused = 0
    for number, batch in enumerate(catalog["batches"], start=1):
        batch_id = batch["batch_id"]
        target = _path(CLIMATE_EXTENSION_DIR, "climate", batch_id)
        expected = batch["row_count"] * len(MODEL_SELECTION_YEARS)
        if panel._validate_existing_batch(target, expected):
            reused += 1
            continue
        frame = derive_climate_extension_batch(batch_id, grids, fallback)
        panel._publish_parquet(frame, target, component="v2_climate", batch_id=batch_id,
                               metadata={"years": MODEL_SELECTION_YEARS, "source_rule": "JJAS of T only; monthly extrema"})
        created += 1
        progress(f"V2 climate {batch_id}: {len(frame)} rows ({number}/{catalog['batch_count']})")
    return {"created": created, "reused": reused}


def _read_all_batches(directory: Path, component: str, *, columns: list[str] | None = None) -> pd.DataFrame:
    catalog = panel.load_grid_catalog()
    frames = [pd.read_parquet(_path(directory, component, batch["batch_id"]), columns=columns)
              for batch in catalog["batches"]]
    return pd.concat(frames, ignore_index=True)


def assemble_v2_feature_matrix() -> dict[str, object]:
    """Join V2 additions to read-only training/validation canonical rows."""
    base, row_group_audit = read_train_validation_rows(PANEL_PATH)
    validate_model_selection_frame(base)
    result = base.copy()
    icnf = _read_all_batches(ICNF_EXTENSION_DIR, "history")
    climate = _read_all_batches(CLIMATE_EXTENSION_DIR, "climate")
    terrain = _read_all_batches(TERRAIN_EXTENSION_DIR, "terrain")
    clc_frames = {}
    for reference_year in (2006, 2012, 2018):
        clc_frames[reference_year] = _read_all_batches(
            CLC_EXTENSION_DIR / str(reference_year), f"agricultural_{reference_year}"
        ).set_index("cell_id")
    result = result.merge(icnf, on=["cell_id", "observation_year"], how="left", validate="one_to_one")
    result = result.merge(climate, on=["cell_id", "observation_year"], how="left", validate="one_to_one")
    result = result.merge(terrain, on="cell_id", how="left", validate="many_to_one")
    agricultural = np.empty(len(result), dtype="float64")
    for reference_year, frame in clc_frames.items():
        mask = result.land_cover_reference_year.eq(reference_year).to_numpy()
        agricultural[mask] = frame.loc[result.loc[mask, "cell_id"], "agricultural_share_2km"].to_numpy()
    result["agricultural_share_2km"] = agricultural
    result = result.sort_values(["observation_year", "cell_id"], kind="mergesort").reset_index(drop=True)
    validate_v2_feature_matrix(result)
    if FEATURE_MATRIX_PATH.exists() or FEATURE_MATRIX_MANIFEST_PATH.exists():
        raise FileExistsError("V2 feature matrix already exists; use explicit overwrite workflow after inspection")
    temporary = FEATURE_MATRIX_PATH.with_suffix(".parquet.tmp")
    result.to_parquet(temporary, index=False, compression="zstd")
    os.replace(temporary, FEATURE_MATRIX_PATH)
    manifest = {"row_count": len(result), "columns": list(result.columns),
                "feature_groups": {key: list(value) for key, value in FEATURE_GROUPS.items()},
                "model_selection_years": list(MODEL_SELECTION_YEARS), "final_test_rows_read": 0,
                "row_group_access": row_group_audit}
    FEATURE_MATRIX_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def validate_v2_feature_matrix(frame: pd.DataFrame) -> dict[str, object]:
    if tuple(sorted(frame.observation_year.unique())) != MODEL_SELECTION_YEARS:
        raise ValueError("V2 feature matrix must contain training/validation years only")
    if frame.duplicated(["cell_id", "observation_year"]).any():
        raise ValueError("Duplicate V2 analytical key")
    if frame[list(PREDICTOR_COLUMNS) + [TARGET_COLUMN] + list(EXTRA_FEATURE_COLUMNS)].isna().any().any():
        raise ValueError("V2 feature matrix contains missing values")
    ranges = {
        "years_since_last_context_fire_2km": (1.0, 11.0),
        "burned_share_previous_3y_1km": (0.0, 3.0),
        "burned_share_previous_10y_1km": (0.0, 10.0),
        "agricultural_share_2km": (0.0, 1.0),
        "mean_elevation_2km": (-200.0, 3500.0),
        "slope_standard_deviation_2km": (0.0, 90.0),
        "warm_season_max_monthly_2m_temperature_c": (-20.0, 60.0),
        "warm_season_min_monthly_soil_water_layer1": (0.0, 1.0),
    }
    for column, (lower, upper) in ranges.items():
        values = frame[column].to_numpy(dtype="float64")
        if not np.isfinite(values).all() or values.min() < lower - 1e-9 or values.max() > upper + 1e-9:
            raise ValueError(f"V2 range failure for {column}")
    return {"row_count": len(frame), "cell_count": int(frame.cell_id.nunique()),
            "years": list(MODEL_SELECTION_YEARS), "missing_values": 0}


def build_v2_features(progress: Callable[[str], None] = print) -> dict[str, object]:
    """Restartable orchestration of all selected V2 candidate feature groups."""
    started = time.perf_counter()
    components = {
        "icnf": build_icnf_extensions(progress),
        "clc": build_clc_extensions(progress),
        "terrain": build_terrain_extensions(progress),
        "climate": build_climate_extensions(progress),
    }
    assembled = assemble_v2_feature_matrix()
    return {"components": components, "assembled": assembled,
            "runtime_seconds": time.perf_counter() - started}
