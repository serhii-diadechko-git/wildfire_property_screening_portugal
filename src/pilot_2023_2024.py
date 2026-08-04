"""Bounded-memory enrichment for the existing 2023 -> 2024 ICNF/CAOP pilot.

This module deliberately never reconstructs the CAOP grid and never loads the
CLC Portugal extract as a whole.  The existing pilot layer is read in feature
batches; each batch is transformed to EPSG:3035 and used as a GDAL bbox filter
when reading CLC.  Only that tile's candidate CLC polygons are resident.
"""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import json
import os
from pathlib import Path
import shutil
import time

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import shapely
import xarray as xr

from src.config import ERA5_LAND_CDS, PILOT_2023_TO_2024


ROOT = Path(__file__).resolve().parents[1]
BASE_GRID = ROOT / "data/processed/pilot_2023_to_2024/pilot_2023_to_2024_icnf_caop.gpkg"
CLC_2018 = ROOT / "data/interim/clc_2018_mainland.gpkg"
FEATURE_PARQUET = ROOT / "data/processed/pilot_2023_2024_features.parquet"
FEATURE_GPKG = ROOT / "data/processed/pilot_2023_2024_features.gpkg"
MAP_PATH = ROOT / "reports/figures/pilot_2024_observed_burned_share_enriched.png"
REPORT_PATH = ROOT / "reports/validation/pilot_2023_2024_validation.md"

CLC_GROUPS = {
    "built_up_share": {"111", "112", "121", "122", "123", "124", "131", "132", "133", "141", "142"},
    "forest_shrub_share": {"311", "312", "313", "321", "322", "323", "324"},
    "agricultural_share": {"211", "212", "213", "221", "222", "223", "231", "241", "242", "243", "244"},
}
FEATURE_COLUMNS = [
    "cell_id", "observation_year", "fire_years_previous_10y_2km",
    "built_up_share", "forest_shrub_share", "agricultural_share",
    "warm_season_mean_2m_temperature_c", "warm_season_total_precipitation_mm",
    "warm_season_mean_soil_water_layer1", "burned_share_next_year",
]


def _base_info() -> dict:
    info = pyogrio.read_info(BASE_GRID)
    if info["features"] != 89_112 or str(info["crs"]) != "EPSG:3763":
        raise ValueError("Existing pilot grid must be the validated 89,112-cell EPSG:3763 layer")
    return info


def _read_grid_batch(skip_features: int, max_features: int) -> gpd.GeoDataFrame:
    columns = ["cell_id", "observation_year", "fire_years_previous_10y_2km", "burned_share_next_year"]
    batch = pyogrio.read_dataframe(BASE_GRID, columns=columns, skip_features=skip_features, max_features=max_features)
    if batch.empty:
        return batch
    if not batch.cell_id.is_unique or not batch.burned_share_next_year.between(0, 1).all():
        raise ValueError("Existing pilot batch has duplicate cell_id or target outside [0, 1]")
    if set(batch.observation_year) != {PILOT_2023_TO_2024.predictor_year}:
        raise ValueError("Existing pilot batch has an unexpected predictor year")
    return batch


def _clc_shares(tile_3763: gpd.GeoDataFrame) -> tuple[pd.DataFrame, int, tuple[float, float, float, float]]:
    """Calculate three CLC shares with one bounded GeoPackage bbox read."""
    tile = tile_3763[["cell_id", "geometry"]].to_crs(3035)
    # One metre avoids losing edge-touching polygons to coordinate rounding.
    minx, miny, maxx, maxy = tile.total_bounds
    bbox = (float(minx - 1), float(miny - 1), float(maxx + 1), float(maxy + 1))
    candidates = pyogrio.read_dataframe(CLC_2018, columns=["Code_18"], bbox=bbox)
    shares = pd.DataFrame(0.0, index=tile_3763.cell_id.to_numpy(), columns=CLC_GROUPS)
    if candidates.empty:
        return shares, 0, bbox

    # Spatial join makes only actual cell/polygon pairs; intersections are then
    # evaluated for this tile alone, rather than using an all-Portugal overlay.
    pairs = gpd.sjoin(tile, candidates[["Code_18", "geometry"]], how="inner", predicate="intersects")
    if not pairs.empty:
        right_geometry = candidates.geometry.take(pairs.index_right.to_numpy()).array
        intersections = shapely.intersection(pairs.geometry.array, right_geometry)
        pairs["intersection_area_m2"] = shapely.area(intersections)
        pairs["Code_18"] = pairs["Code_18"].astype(str)
        denominator = tile.set_index("cell_id").geometry.area
        for feature, codes in CLC_GROUPS.items():
            numerator = (pairs.loc[pairs.Code_18.isin(codes)]
                         .groupby("cell_id")["intersection_area_m2"].sum())
            shares.loc[:, feature] = numerator.reindex(shares.index, fill_value=0.0).div(denominator.reindex(shares.index)).clip(0, 1)
    return shares, len(candidates), bbox


def _era5_context() -> tuple[dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]], dict[str, str]]:
    """Load the tiny four-month ERA5 grids once, not once per grid tile."""
    path = ROOT / ERA5_LAND_CDS.pilot_raw_output
    specifications = (
        ("2t", "warm_season_mean_2m_temperature_c", lambda values: np.nanmean(values, axis=0) - 273.15, "degrees_celsius"),
        # Monthly ERA5-Land total precipitation is average accumulation in m/day.
        ("tp", "warm_season_total_precipitation_mm", lambda values: np.nansum(values * np.array([30, 31, 31, 30])[:, None, None], axis=0) * 1000.0, "millimetres"),
        ("swvl1", "warm_season_mean_soil_water_layer1", lambda values: np.nanmean(values, axis=0), "m3_per_m3"),
    )
    grids: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    units: dict[str, str] = {}
    for short_name, feature, aggregate, unit in specifications:
        dataset = xr.open_dataset(path, engine="cfgrib", backend_kwargs={"indexpath": "", "filter_by_keys": {"shortName": short_name}})
        try:
            variable = next(iter(dataset.data_vars))
            grids[feature] = (dataset.latitude.values.copy(), dataset.longitude.values.copy(), aggregate(dataset[variable].values))
            units[feature] = unit
        finally:
            dataset.close()
    return grids, units


def _assign_era5(tile_3763: gpd.GeoDataFrame, grids: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]) -> pd.DataFrame:
    """Assign the ERA5-Land cell containing each 1 km cell centroid; no interpolation."""
    centres = tile_3763.geometry.centroid.to_crs(4326)
    result = pd.DataFrame(index=tile_3763.index)
    for feature, (latitude, longitude, values) in grids.items():
        # ERA5's regular 0.1-degree cell is represented by its centre coordinate.
        # Choosing the closest centre is the corresponding containing-cell lookup.
        lat_index = np.abs(latitude[:, None] - centres.y.to_numpy()).argmin(axis=0)
        lon_index = np.abs(longitude[:, None] - centres.x.to_numpy()).argmin(axis=0)
        result[feature] = values[lat_index, lon_index]
    # The land-mask water cells decode as zero for precipitation; align missingness.
    result.loc[result["warm_season_mean_2m_temperature_c"].isna(), "warm_season_total_precipitation_mm"] = np.nan
    return result


def smoke_test(tile_size: int = 256) -> dict[str, object]:
    """Run CLC+ERA5 logic for one bounded grid tile before a full execution."""
    _base_info()
    tile = _read_grid_batch(0, tile_size)
    started = time.perf_counter()
    shares, candidates, bbox = _clc_shares(tile)
    grids, units = _era5_context()
    climate = _assign_era5(tile, grids)
    result = {
        "tile_number": 1,
        "cell_count": len(tile),
        "candidate_clc_feature_count": candidates,
        "tile_bbox_epsg3035": bbox,
        "share_frame_bytes": int(shares.memory_usage(deep=True).sum()),
        "climate_frame_bytes": int(climate.memory_usage(deep=True).sum()),
        "era5_grid_value_counts": {key: int(value[2].size) for key, value in grids.items()},
        "era5_units": units,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
    }
    del tile, shares, climate, grids
    gc.collect()
    return result


def run_enrichment(tile_size: int = 256) -> tuple[dict[str, object], dict[str, object]]:
    """Create complete enriched outputs with grid and CLC data kept tile-bounded."""
    info = _base_info()
    smoke = smoke_test(tile_size)
    print(f"Smoke tile 1: {smoke['cell_count']} cells, {smoke['candidate_clc_feature_count']} CLC candidates, "
          f"share frame {smoke['share_frame_bytes']} bytes, climate frame {smoke['climate_frame_bytes']} bytes.", flush=True)

    FEATURE_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    FEATURE_GPKG.parent.mkdir(parents=True, exist_ok=True)
    MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    parquet_tmp = FEATURE_PARQUET.with_suffix(".parquet.tmp")
    gpkg_tmp = FEATURE_GPKG.with_name(FEATURE_GPKG.stem + "_tmp.gpkg")
    if parquet_tmp.exists() or gpkg_tmp.exists():
        raise FileExistsError("Previous temporary enrichment output exists; inspect it before retrying")

    grids, units = _era5_context()
    writer: pq.ParquetWriter | None = None
    observed_ids: set[str] = set()
    missing = {column: 0 for column in FEATURE_COLUMNS}
    target_min, target_max = float("inf"), float("-inf")
    map_x: list[np.ndarray] = []
    map_y: list[np.ndarray] = []
    map_target: list[np.ndarray] = []
    candidate_counts: list[int] = []
    start_all = time.perf_counter()
    try:
        for tile_number, start in enumerate(range(0, int(info["features"]), tile_size), start=1):
            started = time.perf_counter()
            tile = _read_grid_batch(start, tile_size)
            shares, candidate_count, _ = _clc_shares(tile)
            climate = _assign_era5(tile, grids)
            attributes = tile.drop(columns="geometry").copy()
            attributes = attributes.join(shares, on="cell_id").join(climate)
            attributes = attributes[FEATURE_COLUMNS]
            if attributes["burned_share_next_year"].isna().any() or not attributes["burned_share_next_year"].between(0, 1).all():
                raise ValueError("Invalid 2024 observed burned-share target")
            if attributes.cell_id.duplicated().any() or observed_ids.intersection(attributes.cell_id):
                raise ValueError("cell_id is not globally unique")
            observed_ids.update(attributes.cell_id)
            for column, count in attributes.isna().sum().items():
                missing[column] += int(count)
            target_min = min(target_min, float(attributes.burned_share_next_year.min()))
            target_max = max(target_max, float(attributes.burned_share_next_year.max()))
            candidate_counts.append(candidate_count)

            table = pa.Table.from_pandas(attributes, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(parquet_tmp, table.schema, compression="zstd")
            writer.write_table(table)
            output_tile = gpd.GeoDataFrame(attributes, geometry=tile.geometry, crs=tile.crs)
            pyogrio.write_dataframe(output_tile, gpkg_tmp, layer="pilot_2023_2024_features", driver="GPKG", append=tile_number > 1)
            centres = tile.geometry.centroid
            map_x.append(centres.x.to_numpy())
            map_y.append(centres.y.to_numpy())
            map_target.append(attributes.burned_share_next_year.to_numpy())
            elapsed = time.perf_counter() - started
            print(f"Tile {tile_number}: {len(tile)} cells, {candidate_count} candidate CLC features, {elapsed:.2f}s", flush=True)
            del tile, shares, climate, attributes, table, output_tile, centres
            gc.collect()
    except Exception:
        if writer is not None:
            writer.close()
        raise
    else:
        if writer is None:
            raise ValueError("No pilot rows were written")
        writer.close()

    output_info = pyogrio.read_info(gpkg_tmp)
    validation = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_grid": str(BASE_GRID.relative_to(ROOT)).replace("\\", "/"),
        "rows": len(observed_ids),
        "expected_rows": int(info["features"]),
        "unique_cell_id": len(observed_ids) == int(info["features"]),
        "output_crs": str(output_info["crs"]),
        "output_geometry_type": output_info["geometry_type"],
        "target_range": [target_min, target_max],
        "icnf_history_years": list(PILOT_2023_TO_2024.historical_fire_years),
        "icnf_2023_used": False,
        "clc_method": "per-tile EPSG:3035 polygon intersections; CLC read using GeoPackage bbox filter",
        "era5_method": "containing 0.1-degree ERA5-Land cell at 1 km cell centroid; no interpolation or downscaling",
        "units": units,
        "missingness": missing,
        "tile_size": tile_size,
        "tile_count": len(candidate_counts),
        "candidate_clc_features_per_tile": {"minimum": min(candidate_counts), "maximum": max(candidate_counts), "mean": round(float(np.mean(candidate_counts)), 2)},
        "elapsed_seconds": round(time.perf_counter() - start_all, 2),
        "smoke_test": smoke,
    }
    if validation["rows"] != validation["expected_rows"] or not validation["unique_cell_id"] or validation["target_range"][0] < 0 or validation["target_range"][1] > 1:
        raise ValueError("Output row or target validation failed")
    if any(missing.values()):
        raise ValueError(f"Unexpected feature missingness: {missing}")

    # Publish completed derived files only after their validation succeeds.
    os.replace(parquet_tmp, FEATURE_PARQUET)
    os.replace(gpkg_tmp, FEATURE_GPKG)
    fig, axis = plt.subplots(figsize=(8, 12))
    plot = axis.scatter(np.concatenate(map_x), np.concatenate(map_y), c=np.concatenate(map_target), s=0.35, cmap="YlOrRd", vmin=0, vmax=1, linewidths=0)
    fig.colorbar(plot, ax=axis, label="Observed ICNF burned share in 2024")
    axis.set_title("Observed 2024 ICNF burned share by 1 km mainland grid cell\n(Not a model prediction)")
    axis.set_axis_off()
    fig.savefig(MAP_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)
    REPORT_PATH.write_text(
        "# Enriched 2023 → 2024 pilot validation\n\n"
        "The map shows the observed 2024 ICNF burned-share target, not a model prediction. "
        "ICNF 2023 was not used. CLC is generalized 2018 landscape context; ERA5-Land is coarse regional context with no downscaling.\n\n"
        "```json\n" + json.dumps(validation, indent=2) + "\n```\n",
        encoding="utf-8",
    )
    return validation, smoke


def validate_existing_enriched_outputs(batch_size: int = 2_000) -> dict[str, object]:
    """Validate and document already-published derived outputs without loading them whole."""
    info = pyogrio.read_info(FEATURE_GPKG)
    if info["features"] != 89_112 or str(info["crs"]) != "EPSG:3763":
        raise ValueError("Enriched GeoPackage does not have the expected grid row count or CRS")
    observed_ids: set[str] = set()
    missing = {column: 0 for column in FEATURE_COLUMNS}
    target_min, target_max = float("inf"), float("-inf")
    x_values: list[np.ndarray] = []
    y_values: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    for start in range(0, int(info["features"]), batch_size):
        batch = pyogrio.read_dataframe(FEATURE_GPKG, skip_features=start, max_features=batch_size)
        absent = set(FEATURE_COLUMNS).difference(batch.columns)
        if absent:
            raise ValueError(f"Missing enriched feature columns: {sorted(absent)}")
        if batch.cell_id.duplicated().any() or observed_ids.intersection(batch.cell_id):
            raise ValueError("Enriched cell_id values are not unique")
        observed_ids.update(batch.cell_id)
        if not batch.burned_share_next_year.between(0, 1).all():
            raise ValueError("Observed 2024 target is outside [0, 1]")
        for share in CLC_GROUPS:
            # Floating point area division can exceed one by ~4e-13.
            if (batch[share] < -1e-9).any() or (batch[share] > 1 + 1e-9).any():
                raise ValueError(f"CLC share outside [0, 1]: {share}")
        for column, count in batch[FEATURE_COLUMNS].isna().sum().items():
            missing[column] += int(count)
        target_min = min(target_min, float(batch.burned_share_next_year.min()))
        target_max = max(target_max, float(batch.burned_share_next_year.max()))
        centres = batch.geometry.centroid
        x_values.append(centres.x.to_numpy())
        y_values.append(centres.y.to_numpy())
        targets.append(batch.burned_share_next_year.to_numpy())
        del batch, centres
        gc.collect()
    validation = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "rows": len(observed_ids),
        "expected_rows": 89_112,
        "unique_cell_id": len(observed_ids) == 89_112,
        "output_crs": str(info["crs"]),
        "output_geometry_type": info["geometry_type"],
        "target_range": [target_min, target_max],
        "icnf_history_years": list(PILOT_2023_TO_2024.historical_fire_years),
        "icnf_2023_used": False,
        "clc_method": "EPSG:3035 generalized landscape-area shares; current bounded pipeline uses per-tile GeoPackage bbox reads",
        "era5_method": "containing 0.1-degree ERA5-Land cell at grid-cell centroid; no interpolation or downscaling",
        "units": {"warm_season_mean_2m_temperature_c": "degrees_celsius", "warm_season_total_precipitation_mm": "millimetres", "warm_season_mean_soil_water_layer1": "m3_per_m3"},
        "missingness": missing,
        "era5_land_mask_note": "Coastal grid-cell centroids whose containing ERA5-Land cell is masked as water retain missing temperature/soil-water context; precipitation is present.",
    }
    fig, axis = plt.subplots(figsize=(8, 12))
    plot = axis.scatter(np.concatenate(x_values), np.concatenate(y_values), c=np.concatenate(targets), s=0.35, cmap="YlOrRd", vmin=0, vmax=1, linewidths=0)
    fig.colorbar(plot, ax=axis, label="Observed ICNF burned share in 2024")
    axis.set_title("Observed 2024 ICNF burned share by 1 km mainland grid cell\n(Not a model prediction)")
    axis.set_axis_off()
    MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(MAP_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        "# Enriched 2023 → 2024 pilot validation\n\n"
        "The map shows the observed 2024 ICNF burned-share target, not a model prediction. "
        "ICNF 2023 was not used. CLC is generalized 2018 landscape context; ERA5-Land is coarse regional context with no downscaling.\n\n"
        "```json\n" + json.dumps(validation, indent=2) + "\n```\n",
        encoding="utf-8",
    )
    return validation
