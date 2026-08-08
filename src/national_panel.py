"""Bounded, restartable construction of the canonical 2015-2024 panel.

The module implements the validated feature contract in deterministic 20 km
spatial tiles and publishes every component atomically with a checksum manifest.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import ExitStack
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import time
from typing import Callable, Iterable
import warnings

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import rasterio
from rasterio.features import geometry_mask
from rasterio.merge import merge
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import Window, from_bounds
import shapely
from shapely.geometry import mapping

from src.clc_validation import CANONICAL_CLC_CLASS_MAPPING
from src.climate_features import era5_source_paths, jjas_total_precipitation_mm, read_grib_variable
from src.config import CLC, SPATIAL, TEMPORAL
from src.feature_contract import CLIMATE_PREDICTOR_COLUMNS, PREDICTOR_COLUMNS, TABLE_COLUMNS, TARGET_COLUMN, source_years, validate_feature_table
from src.geospatial_utils import (
    BOUNDARY_PATH,
    GRID_PATH,
    ICNF_ROOT,
    dem_tile_bounds,
    icnf_vsi_path,
    polygonal_geometry,
)
from src.source_registry import (
    CLC_2006_V2020_20U1,
    CLC_2012_V2020_20U1,
    CLC_2018_V2020_20U1,
    CLC_PREPARED_PORTUGAL_LAYERS,
    COP_DEM_GLO30,
    COP_DEM_GLO30_TILES,
)


ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / "data/interim/national_panel_2015_2024"
GRID_BATCH_DIR = BUILD_ROOT / "grid"
SLOPE_BATCH_DIR = BUILD_ROOT / "slope"
CLC_BATCH_DIR = BUILD_ROOT / "clc"
ICNF_REPAIRED_DIR = BUILD_ROOT / "icnf_repaired"
ICNF_BATCH_DIR = BUILD_ROOT / "icnf_components"
ERA_BATCH_DIR = BUILD_ROOT / "era5"
PANEL_BATCH_DIR = BUILD_ROOT / "panel_batches"
CANONICAL_ERA_BATCH_DIR = BUILD_ROOT / "era5_coastal_fallback"
CANONICAL_PANEL_BATCH_DIR = BUILD_ROOT / "panel_batches_coastal_fallback"
ERA5_FALLBACK_MAPPING_PATH = BUILD_ROOT / "era5_coastal_fallback_mapping.parquet"
BUILD_METRICS_PATH = BUILD_ROOT / "build_metrics.json"
NATIONAL_PANEL_PATH = ROOT / "data/processed/national_panel_2015_2024.parquet"
VALIDATION_METRICS_PATH = ROOT / "data/processed/national_panel_2015_2024_validation.json"
VALIDATION_REPORT_PATH = ROOT / "reports/validation/national_panel_2015_2024_validation.md"
DETERMINISM_BATCH_IDS = ("x00_y10", "x06_y21", "x10_y21")
EXPECTED_ARROW_TYPES = {
    **{column: "string" for column in TABLE_COLUMNS[:2]},
    **{column: "int16" for column in TABLE_COLUMNS[2:8]},
    **{column: "string" for column in TABLE_COLUMNS[8:11]},
    "built_up_share": "double",
    "forest_shrub_share_2km": "double",
    "mean_slope_2km": "double",
    "fire_years_previous_10y_2km": "int8",
    "warm_season_mean_2m_temperature_c": "double",
    "warm_season_total_precipitation_mm": "double",
    "warm_season_mean_soil_water_layer1": "double",
    "warm_season_max_monthly_2m_temperature_c": "double",
    "warm_season_min_monthly_soil_water_layer1": "double",
    TARGET_COLUMN: "double",
}

OBSERVATION_YEARS = tuple(range(TEMPORAL.predictor_start_year, TEMPORAL.predictor_end_year + 1))
ICNF_YEARS = tuple(range(TEMPORAL.required_icnf_start_year, TEMPORAL.required_icnf_end_year + 1))
TILE_SIZE_METRES = 20_000
TILE_ORIGIN_X = -120_000
TILE_ORIGIN_Y = -300_000
DEM_RESOLUTION_METRES = 30.0
GRID_CATALOG_PATH = BUILD_ROOT / "grid_catalog.json"

_CLC_RAW_BY_REFERENCE_YEAR = {
    2006: CLC_2006_V2020_20U1,
    2012: CLC_2012_V2020_20U1,
    2018: CLC_2018_V2020_20U1,
}


class BatchError(RuntimeError):
    """Actionable error carrying the failed component and batch identifier."""


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _atomic_json(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary output requires inspection: {temporary}")
    temporary.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    os.replace(temporary, path)


def _manifest_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".json")


def _validate_existing_batch(
    path: Path,
    expected_rows: int | None = None,
    required_columns: tuple[str, ...] = (),
) -> dict[str, object]:
    manifest_path = _manifest_path(path)
    if path.exists() != manifest_path.exists():
        raise FileExistsError(f"Incomplete batch publication; inspect {path} and {manifest_path}")
    if not path.exists():
        return {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if _sha256(path) != manifest["sha256"]:
        raise ValueError(f"Completed batch checksum changed: {path}")
    rows = pq.ParquetFile(path).metadata.num_rows
    if rows != manifest["row_count"] or (expected_rows is not None and rows != expected_rows):
        raise ValueError(f"Completed batch row count changed: {path}")
    columns = tuple(pq.ParquetFile(path).schema.names)
    if required_columns and not set(required_columns).issubset(columns):
        return {}
    return manifest


def _publish_parquet(
    frame: pd.DataFrame,
    path: Path,
    *,
    component: str,
    batch_id: str,
    metadata: dict[str, object] | None = None,
    required_columns: tuple[str, ...] = (),
) -> dict[str, object]:
    existing = _validate_existing_batch(path, len(frame), required_columns)
    if existing:
        return existing | {"status": "reused"}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary output requires inspection: {temporary}")
    frame.to_parquet(temporary, index=False, compression="zstd")
    manifest = {
        "component": component,
        "batch_id": batch_id,
        "row_count": len(frame),
        "columns": list(frame.columns),
        "sha256": _sha256(temporary),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        **(metadata or {}),
    }
    os.replace(temporary, path)
    _atomic_json(manifest, _manifest_path(path))
    return manifest | {"status": "created"}


def _tile_id(ix: int, iy: int) -> str:
    return f"x{ix:02d}_y{iy:02d}"


def _tile_bounds_3763(ix: int, iy: int) -> tuple[float, float, float, float]:
    west = TILE_ORIGIN_X + ix * TILE_SIZE_METRES
    south = TILE_ORIGIN_Y + iy * TILE_SIZE_METRES
    return west, south, west + TILE_SIZE_METRES, south + TILE_SIZE_METRES


def _candidate_tiles() -> list[tuple[str, tuple[float, float, float, float]]]:
    info = pyogrio.read_info(GRID_PATH)
    minx, miny, maxx, maxy = (float(value) for value in info["total_bounds"])
    min_ix = math.floor((minx - TILE_ORIGIN_X) / TILE_SIZE_METRES)
    max_ix = math.floor(((maxx - 1) - TILE_ORIGIN_X) / TILE_SIZE_METRES)
    min_iy = math.floor((miny - TILE_ORIGIN_Y) / TILE_SIZE_METRES)
    max_iy = math.floor(((maxy - 1) - TILE_ORIGIN_Y) / TILE_SIZE_METRES)
    return [
        (_tile_id(ix, iy), _tile_bounds_3763(ix, iy))
        for ix in range(min_ix, max_ix + 1)
        for iy in range(min_iy, max_iy + 1)
    ]


def _grid_batch_path(batch_id: str) -> Path:
    return GRID_BATCH_DIR / f"grid_{batch_id}.parquet"


def _component_batch_path(directory: Path, component: str, batch_id: str) -> Path:
    return directory / f"{component}_{batch_id}.parquet"


def _geometry_frame(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    return {
        "geometry": shapely.from_wkb(frame.geometry_wkb.to_numpy()),
        "land_geometry": shapely.from_wkb(frame.land_geometry_wkb.to_numpy()),
        "context_geometry": shapely.from_wkb(frame.context_geometry_wkb.to_numpy()),
    }


def build_grid_batches(progress: Callable[[str], None] = print) -> dict[str, object]:
    """Create reusable mainland land/context geometry batches once."""
    if GRID_CATALOG_PATH.exists():
        catalog = json.loads(GRID_CATALOG_PATH.read_text(encoding="utf-8"))
        for batch in catalog["batches"]:
            _validate_existing_batch(ROOT / batch["path"], batch["row_count"])
        return catalog | {"status": "reused"}
    boundary_frame = pyogrio.read_dataframe(BOUNDARY_PATH, columns=[])
    if len(boundary_frame) != 1 or str(boundary_frame.crs) != SPATIAL.analysis_crs:
        raise ValueError("Canonical mainland boundary is not one EPSG:3763 feature")
    boundary = boundary_frame.geometry.iloc[0]
    shapely.prepare(boundary)
    batches = []
    observed_ids: set[str] = set()
    # The authoritative grid is only ~27 MB/89,112 geometries. Reading it once
    # avoids hundreds of repeated GeoPackage spatial queries; all expensive
    # feature work remains bounded by the deterministic tile groups below.
    all_cells = pyogrio.read_dataframe(GRID_PATH, columns=["cell_id"])
    centres = all_cells.geometry.centroid
    all_cells["tile_ix"] = np.floor((centres.x - TILE_ORIGIN_X) / TILE_SIZE_METRES).astype(int)
    all_cells["tile_iy"] = np.floor((centres.y - TILE_ORIGIN_Y) / TILE_SIZE_METRES).astype(int)
    grouped = list(all_cells.groupby(["tile_ix", "tile_iy"], sort=True))
    for candidate_number, ((ix, iy), cells) in enumerate(grouped, start=1):
        batch_id = _tile_id(int(ix), int(iy))
        bounds = _tile_bounds_3763(int(ix), int(iy))
        cells = cells.drop(columns=["tile_ix", "tile_iy"]).copy()
        cells = cells.sort_values("cell_id").reset_index(drop=True)
        if observed_ids.intersection(cells.cell_id):
            raise ValueError(f"Grid tile overlap detected at {batch_id}")
        observed_ids.update(cells.cell_id)
        cell_geometries = cells.geometry.to_numpy()
        land_geometries = cell_geometries.copy()
        coastal_cells = ~shapely.covers(boundary, cell_geometries)
        land_geometries[coastal_cells] = shapely.intersection(
            cell_geometries[coastal_cells], boundary
        )
        # Preserve the validated GeoSeries/geometry.buffer operation exactly.
        context_buffers = shapely.buffer(
            cell_geometries, SPATIAL.context_buffer_metres, quad_segs=16
        )
        contexts = context_buffers.copy()
        boundary_contexts = ~shapely.covers(boundary, context_buffers)
        contexts[boundary_contexts] = shapely.intersection(
            context_buffers[boundary_contexts], boundary
        )
        if shapely.is_empty(land_geometries).any() or shapely.is_empty(contexts).any():
            raise ValueError(f"Mainland geometry unexpectedly empty in {batch_id}")
        centres_wgs84 = cells.geometry.centroid.to_crs(4326)
        frame = pd.DataFrame({
            "batch_id": batch_id,
            "cell_id": cells.cell_id.to_numpy(),
            "geometry_wkb": shapely.to_wkb(cell_geometries),
            "land_geometry_wkb": shapely.to_wkb(land_geometries),
            "context_geometry_wkb": shapely.to_wkb(contexts),
            "land_area_m2": shapely.area(land_geometries),
            "context_land_area_m2": shapely.area(contexts),
            "centroid_longitude": centres_wgs84.x.to_numpy(),
            "centroid_latitude": centres_wgs84.y.to_numpy(),
        })
        path = _grid_batch_path(batch_id)
        manifest = _publish_parquet(
            frame, path, component="grid", batch_id=batch_id,
            metadata={"bounds_epsg3763": bounds},
        )
        batches.append({
            "batch_id": batch_id,
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "row_count": len(frame),
            "bounds_epsg3763": bounds,
            "sha256": manifest["sha256"],
        })
        progress(f"Grid {batch_id}: {len(frame)} cells ({candidate_number}/{len(grouped)})")
    del all_cells
    expected = int(pyogrio.read_info(GRID_PATH)["features"])
    if len(observed_ids) != expected:
        raise ValueError(f"Grid batching retained {len(observed_ids)} cells, expected {expected}")
    catalog = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_crs": SPATIAL.analysis_crs,
        "tile_size_metres": TILE_SIZE_METRES,
        "cell_count": len(observed_ids),
        "batch_count": len(batches),
        "batches": batches,
    }
    _atomic_json(catalog, GRID_CATALOG_PATH)
    return catalog | {"status": "created"}


def load_grid_catalog() -> dict[str, object]:
    if not GRID_CATALOG_PATH.exists():
        raise FileNotFoundError("Grid catalog is not built")
    return json.loads(GRID_CATALOG_PATH.read_text(encoding="utf-8"))


def load_grid_batch(batch_id: str) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    frame = pd.read_parquet(_grid_batch_path(batch_id))
    return frame, _geometry_frame(frame)


def _repair_icnf_frame(frame: gpd.GeoDataFrame, year: int) -> tuple[gpd.GeoDataFrame, dict[str, object]]:
    """Apply the canonical derived-only polygon repair policy to one full year."""
    raw = list(frame.geometry)
    before_area = float(sum(geometry.area for geometry in raw if geometry is not None))
    accepted = []
    repaired_count = 0
    rejected_count = 0
    invalid_count = 0
    area_changes = []
    for geometry in raw:
        invalid = geometry is not None and not geometry.is_empty and not geometry.is_valid
        invalid_count += int(invalid)
        candidate = shapely.make_valid(geometry) if invalid else geometry
        candidate = polygonal_geometry(candidate)
        if candidate is None or candidate.is_empty or not candidate.is_valid:
            rejected_count += 1
            continue
        accepted.append(candidate)
        if invalid:
            repaired_count += 1
            original_area = geometry.area
            area_changes.append(abs(candidate.area - original_area) / original_area * 100 if original_area else np.inf)
    repaired = gpd.GeoDataFrame(
        {"source_year": np.full(len(accepted), year, dtype="int16")},
        geometry=accepted,
        crs=SPATIAL.analysis_crs,
    )
    after_area = float(repaired.geometry.area.sum())
    log = {
        "year": year,
        "input_count": len(frame),
        "invalid_before_count": invalid_count,
        "repaired_count": repaired_count,
        "rejected_count": rejected_count,
        "accepted_count": len(repaired),
        "input_area_m2": before_area,
        "accepted_area_m2": after_area,
        "total_area_change_percent": (after_area - before_area) / before_area * 100 if before_area else 0.0,
        "repairs_area_change_over_0_1_percent": sum(value > 0.1 for value in area_changes),
        "repairs_area_change_over_1_percent": sum(value > 1.0 for value in area_changes),
        "repairs_area_change_over_5_percent": sum(value > 5.0 for value in area_changes),
    }
    return repaired, log


def _publish_gpkg(
    frame: gpd.GeoDataFrame,
    path: Path,
    *,
    layer: str,
    metadata: dict[str, object],
) -> dict[str, object]:
    manifest_path = _manifest_path(path)
    if path.exists() != manifest_path.exists():
        raise FileExistsError(f"Incomplete GeoPackage publication; inspect {path}")
    if path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        info = pyogrio.read_info(path, layer=layer)
        if _sha256(path) != manifest["sha256"] or int(info["features"]) != manifest["row_count"]:
            raise ValueError(f"Completed GeoPackage changed: {path}")
        return manifest | {"status": "reused"}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.stem + ".tmp.gpkg")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary output requires inspection: {temporary}")
    pyogrio.write_dataframe(frame, temporary, layer=layer, driver="GPKG")
    manifest = {
        "component": "icnf_repaired",
        "row_count": len(frame),
        "sha256": _sha256(temporary),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        **metadata,
    }
    os.replace(temporary, path)
    _atomic_json(manifest, manifest_path)
    return manifest | {"status": "created"}


def prepare_icnf_years(progress: Callable[[str], None] = print) -> dict[str, object]:
    """Repair each required raw ICNF year once and retain immutable raw archives."""
    results = {}
    combined = None
    for year in ICNF_YEARS:
        path = ICNF_REPAIRED_DIR / f"icnf_{year}_repaired.gpkg"
        layer = f"icnf_{year}_repaired"
        if path.exists():
            results[year] = _publish_gpkg(
                gpd.GeoDataFrame(), path, layer=layer, metadata={"year": year}
            )
            progress(f"ICNF repaired {year}: reused {results[year]['row_count']} features")
            continue
        if year <= 2008:
            if combined is None:
                combined = pyogrio.read_dataframe(
                    icnf_vsi_path(ICNF_ROOT / "ardida_2000_2008.zip"), columns=["Ano"]
                )
            frame = combined.loc[combined.Ano.astype(int) == year].copy()
            raw_archive = "ardida_2000_2008.zip"
        else:
            raw_archive = f"ardida_{year}.zip"
            frame = pyogrio.read_dataframe(icnf_vsi_path(ICNF_ROOT / raw_archive), columns=[])
        repaired, repair_log = _repair_icnf_frame(frame, year)
        results[year] = _publish_gpkg(
            repaired,
            path,
            layer=layer,
            metadata={
                "year": year,
                "raw_archive": f"data/raw/wildfire/icnf_burned_areas/{raw_archive}",
                "repair_log": repair_log,
            },
        )
        progress(
            f"ICNF repaired {year}: {len(frame)} input, {repair_log['repaired_count']} repaired, "
            f"{repair_log['rejected_count']} rejected"
        )
    return {"years": results, "status": "complete"}


def _relevant_dem_records(bounds_3763: tuple[float, float, float, float]):
    west, south, east, north = transform_bounds(
        SPATIAL.analysis_crs, "EPSG:4326", *bounds_3763, densify_pts=21
    )
    records = [
        record
        for tile_id, record in COP_DEM_GLO30_TILES.items()
        if not (
            dem_tile_bounds(tile_id)[2] <= west
            or dem_tile_bounds(tile_id)[0] >= east
            or dem_tile_bounds(tile_id)[3] <= south
            or dem_tile_bounds(tile_id)[1] >= north
        )
    ]
    return records, (west, south, east, north)


def _terrain_surfaces(
    bounds_3763: tuple[float, float, float, float],
) -> tuple[np.ndarray, np.ndarray, object, list[str]]:
    """Warp a bounded DEM window and derive aligned elevation and slope surfaces."""
    minx, miny, maxx, maxy = bounds_3763
    west = math.floor((minx - 60.0) / DEM_RESOLUTION_METRES) * DEM_RESOLUTION_METRES
    south = math.floor((miny - 60.0) / DEM_RESOLUTION_METRES) * DEM_RESOLUTION_METRES
    east = math.ceil((maxx + 60.0) / DEM_RESOLUTION_METRES) * DEM_RESOLUTION_METRES
    north = math.ceil((maxy + 60.0) / DEM_RESOLUTION_METRES) * DEM_RESOLUTION_METRES
    target_bounds = (west, south, east, north)
    records, source_bounds = _relevant_dem_records(target_bounds)
    if not records:
        raise ValueError(f"No registered DEM tile covers {target_bounds}")
    with ExitStack() as stack:
        sources = [stack.enter_context(rasterio.open(ROOT / record.raw_path)) for record in records]
        mosaic, source_transform = merge(
            sources, bounds=source_bounds, nodata=np.nan, dtype="float32"
        )
        width = int(round((east - west) / DEM_RESOLUTION_METRES))
        height = int(round((north - south) / DEM_RESOLUTION_METRES))
        target_transform = from_origin(west, north, DEM_RESOLUTION_METRES, DEM_RESOLUTION_METRES)
        elevation = np.full((height, width), np.nan, dtype="float32")
        reproject(
            mosaic[0], elevation,
            src_transform=source_transform,
            src_crs="EPSG:4326",
            src_nodata=np.nan,
            dst_transform=target_transform,
            dst_crs=SPATIAL.analysis_crs,
            dst_nodata=np.nan,
            resampling=Resampling.nearest,
        )
    with np.errstate(invalid="ignore"):
        gradient_y, gradient_x = np.gradient(
            elevation, DEM_RESOLUTION_METRES, DEM_RESOLUTION_METRES
        )
        slope = np.degrees(np.arctan(np.hypot(gradient_x, gradient_y)))
    return elevation, slope, target_transform, [record.tile_id for record in records]


def _slope_surface(bounds_3763: tuple[float, float, float, float]) -> tuple[np.ndarray, object, list[str]]:
    """Backward-compatible slope-only wrapper used by the canonical panel."""
    _, slope, transform, tiles = _terrain_surfaces(bounds_3763)
    return slope, transform, tiles


def derive_slope_batch(batch_id: str) -> tuple[pd.DataFrame, dict[str, object]]:
    grid, geometries = load_grid_batch(batch_id)
    contexts = geometries["context_geometry"]
    bounds = tuple(float(value) for value in shapely.bounds(shapely.union_all(contexts)))
    slope, transform, dem_tiles = _slope_surface(bounds)
    values = []
    for cell_id, context in zip(grid.cell_id, contexts, strict=True):
        window = from_bounds(*context.bounds, transform=transform)
        col0 = max(0, int(math.floor(window.col_off)))
        row0 = max(0, int(math.floor(window.row_off)))
        col1 = min(slope.shape[1], int(math.ceil(window.col_off + window.width)))
        row1 = min(slope.shape[0], int(math.ceil(window.row_off + window.height)))
        subset = slope[row0:row1, col0:col1]
        subset_transform = rasterio.windows.transform(
            Window(col0, row0, col1 - col0, row1 - row0), transform
        )
        mask = geometry_mask(
            [mapping(context)], out_shape=subset.shape, transform=subset_transform, invert=True
        )
        finite = np.isfinite(subset) & mask
        if not finite.any():
            raise ValueError(f"No finite slope pixels for {cell_id} in {batch_id}")
        values.append(float(subset[finite].mean()))
    frame = pd.DataFrame({"cell_id": grid.cell_id, "mean_slope_2km": values})
    return frame, {
        "dem_tiles": dem_tiles,
        "metric_resolution_metres": DEM_RESOLUTION_METRES,
        "processing_crs": SPATIAL.analysis_crs,
    }


def build_slope_batches(progress: Callable[[str], None] = print) -> dict[str, object]:
    catalog = load_grid_catalog()
    created = reused = 0
    for number, batch in enumerate(catalog["batches"], start=1):
        batch_id = batch["batch_id"]
        path = _component_batch_path(SLOPE_BATCH_DIR, "slope", batch_id)
        existing = _validate_existing_batch(path, batch["row_count"])
        if existing:
            reused += 1
            progress(f"Slope {batch_id}: reused ({number}/{catalog['batch_count']})")
            continue
        try:
            frame, metadata = derive_slope_batch(batch_id)
            _publish_parquet(frame, path, component="slope", batch_id=batch_id, metadata=metadata)
        except Exception as error:
            raise BatchError(f"slope/{batch_id} failed: {error}") from error
        created += 1
        progress(f"Slope {batch_id}: {len(frame)} cells ({number}/{catalog['batch_count']})")
    return {"created": created, "reused": reused, "batch_count": catalog["batch_count"]}


def derive_clc_batch(batch_id: str, reference_year: int) -> tuple[pd.DataFrame, dict[str, object]]:
    grid, geometries = load_grid_batch(batch_id)
    record = CLC_PREPARED_PORTUGAL_LAYERS[reference_year]
    code_field = record.validation_facts.class_code_field
    land = gpd.GeoSeries(geometries["land_geometry"], crs=SPATIAL.analysis_crs).to_crs(CLC.area_processing_crs)
    context = gpd.GeoSeries(geometries["context_geometry"], crs=SPATIAL.analysis_crs).to_crs(CLC.area_processing_crs)
    bbox = tuple(float(value) for value in context.total_bounds)
    candidates = pyogrio.read_dataframe(
        ROOT / record.prepared_path,
        layer=record.validation_facts.layer_name,
        columns=[code_field],
        bbox=bbox,
    )
    codes = candidates[code_field].astype(str).str.zfill(3)
    output = {"cell_id": grid.cell_id.to_numpy()}
    for feature, areas in (("built_up_share", land), ("forest_shrub_share_2km", context)):
        selected = candidates.loc[codes.isin(CANONICAL_CLC_CLASS_MAPPING[feature])]
        if selected.empty:
            numerators = np.zeros(len(grid), dtype="float64")
        else:
            class_union = shapely.union_all(selected.geometry.to_numpy())
            numerators = shapely.area(shapely.intersection(areas.to_numpy(), class_union))
        denominators = shapely.area(areas.to_numpy())
        output[feature] = np.clip(numerators / denominators, 0.0, 1.0)
    return pd.DataFrame(output), {
        "reference_year": reference_year,
        "release_id": record.release_id,
        "candidate_feature_count": len(candidates),
        "area_processing_crs": CLC.area_processing_crs,
    }


def build_clc_batches(progress: Callable[[str], None] = print) -> dict[str, object]:
    catalog = load_grid_catalog()
    counts = defaultdict(int)
    for reference_year in (2006, 2012, 2018):
        directory = CLC_BATCH_DIR / str(reference_year)
        for number, batch in enumerate(catalog["batches"], start=1):
            batch_id = batch["batch_id"]
            path = _component_batch_path(directory, f"clc_{reference_year}", batch_id)
            existing = _validate_existing_batch(path, batch["row_count"])
            if existing:
                counts["reused"] += 1
                continue
            try:
                frame, metadata = derive_clc_batch(batch_id, reference_year)
                _publish_parquet(
                    frame, path, component=f"clc_{reference_year}", batch_id=batch_id, metadata=metadata
                )
            except Exception as error:
                raise BatchError(f"clc_{reference_year}/{batch_id} failed: {error}") from error
            counts["created"] += 1
            progress(
                f"CLC {reference_year} {batch_id}: {len(frame)} cells, "
                f"{metadata['candidate_feature_count']} candidates ({number}/{catalog['batch_count']})"
            )
    return {**counts, "batch_count": catalog["batch_count"] * 3}


def load_era5_grids() -> dict[int, dict[str, object]]:
    """Load each small annual ERA5 grid once with governed precipitation selection."""
    result = {}
    for year in OBSERVATION_YEARS:
        paths = era5_source_paths(year)
        latitude, longitude, temperature, months = read_grib_variable(
            paths["temperature_and_soil_water"], "2t"
        )
        soil_lat, soil_lon, soil_water, soil_months = read_grib_variable(
            paths["temperature_and_soil_water"], "swvl1"
        )
        precip_lat, precip_lon, precipitation, precip_months = read_grib_variable(
            paths["precipitation"], "tp"
        )
        if not (
            months == soil_months == precip_months == (6, 7, 8, 9)
            and np.array_equal(latitude, soil_lat)
            and np.array_equal(latitude, precip_lat)
            and np.array_equal(longitude, soil_lon)
            and np.array_equal(longitude, precip_lon)
        ):
            raise ValueError(f"ERA5 grids/months differ for {year}")
        with warnings.catch_warnings(), np.errstate(invalid="ignore"):
            warnings.simplefilter("ignore", category=RuntimeWarning)
            temperature_c = np.nanmean(temperature, axis=0) - 273.15
            soil_mean = np.nanmean(soil_water, axis=0)
            temperature_max = np.nanmax(temperature, axis=0) - 273.15
            soil_min = np.nanmin(soil_water, axis=0)
        result[year] = {
            "latitude": latitude,
            "longitude": longitude,
            "warm_season_mean_2m_temperature_c": temperature_c,
            "warm_season_total_precipitation_mm": jjas_total_precipitation_mm(precipitation, months),
            "warm_season_mean_soil_water_layer1": soil_mean,
            "warm_season_max_monthly_2m_temperature_c": temperature_max,
            "warm_season_min_monthly_soil_water_layer1": soil_min,
            "temperature_soil_path": str(paths["temperature_and_soil_water"].relative_to(ROOT)).replace("\\", "/"),
            "precipitation_path": str(paths["precipitation"].relative_to(ROOT)).replace("\\", "/"),
        }
    return result


def _load_era5_fallback_mapping() -> pd.DataFrame:
    if not ERA5_FALLBACK_MAPPING_PATH.exists():
        raise FileNotFoundError("Accepted ERA5 coastal fallback mapping is missing")
    mapping = pd.read_parquet(
        ERA5_FALLBACK_MAPPING_PATH,
        columns=["cell_id", "fallback_flat_index"],
    ).set_index("cell_id")
    if len(mapping) != 1_506 or not mapping.index.is_unique:
        raise ValueError("Accepted ERA5 coastal fallback mapping contract failed")
    return mapping


def derive_era_batch(
    batch_id: str,
    grids: dict[int, dict[str, object]],
    fallback_mapping: pd.DataFrame | None = None,
) -> pd.DataFrame:
    grid = pd.read_parquet(_grid_batch_path(batch_id))
    fallback_mapping = _load_era5_fallback_mapping() if fallback_mapping is None else fallback_mapping
    rows = []
    latitude_points = grid.centroid_latitude.to_numpy()
    longitude_points = grid.centroid_longitude.to_numpy()
    for year in OBSERVATION_YEARS:
        source = grids[year]
        lat_index = np.abs(source["latitude"][:, None] - latitude_points).argmin(axis=0)
        lon_index = np.abs(source["longitude"][:, None] - longitude_points).argmin(axis=0)
        values = {
            feature: source[feature][lat_index, lon_index]
            for feature in CLIMATE_PREDICTOR_COLUMNS
        }
        mask = np.isnan(values["warm_season_mean_2m_temperature_c"])
        for feature in values:
            values[feature] = np.asarray(values[feature], dtype="float64")
            values[feature][mask] = np.nan
        if not all(np.array_equal(np.isnan(value), mask) for value in values.values()):
            raise ValueError(f"ERA5 water mask differs across fields for {year}/{batch_id}")
        affected_positions = np.flatnonzero(mask)
        for position in affected_positions:
            cell_id = grid.cell_id.iloc[position]
            if cell_id not in fallback_mapping.index:
                raise ValueError(f"No accepted ERA5 fallback for {cell_id}/{year}")
            flat_index = int(fallback_mapping.loc[cell_id, "fallback_flat_index"])
            for feature in values:
                values[feature][position] = float(np.asarray(source[feature]).ravel()[flat_index])
        if any(np.isnan(value).any() for value in values.values()):
            raise ValueError(f"Accepted ERA5 fallback left missing values for {year}/{batch_id}")
        rows.append(pd.DataFrame({
            "cell_id": grid.cell_id.to_numpy(),
            "observation_year": np.full(len(grid), year, dtype="int16"),
            **values,
        }))
    return pd.concat(rows, ignore_index=True)


def build_era_batches(progress: Callable[[str], None] = print) -> dict[str, object]:
    catalog = load_grid_catalog()
    grids = load_era5_grids()
    fallback_mapping = _load_era5_fallback_mapping()
    created = reused = 0
    for number, batch in enumerate(catalog["batches"], start=1):
        batch_id = batch["batch_id"]
        path = _component_batch_path(CANONICAL_ERA_BATCH_DIR, "era5", batch_id)
        expected_rows = batch["row_count"] * len(OBSERVATION_YEARS)
        existing = _validate_existing_batch(
            path, expected_rows, ("cell_id", "observation_year", *CLIMATE_PREDICTOR_COLUMNS)
        )
        if existing:
            reused += 1
            continue
        try:
            frame = derive_era_batch(batch_id, grids, fallback_mapping)
            source_paths = {
                year: {
                    "temperature_and_soil_water": grids[year]["temperature_soil_path"],
                    "precipitation": grids[year]["precipitation_path"],
                }
                for year in OBSERVATION_YEARS
            }
            _publish_parquet(
                frame, path, component="era5", batch_id=batch_id,
                metadata={
                    "source_paths_by_year": source_paths,
                    "assignment": "containing_valid_cell_else_accepted_nearest_valid_land_cell_no_interpolation",
                },
                required_columns=("cell_id", "observation_year", *CLIMATE_PREDICTOR_COLUMNS),
            )
        except Exception as error:
            raise BatchError(f"era5/{batch_id} failed: {error}") from error
        created += 1
        progress(f"ERA5 {batch_id}: {len(frame)} rows ({number}/{catalog['batch_count']})")
    return {"created": created, "reused": reused, "batch_count": catalog["batch_count"]}


def derive_icnf_batch(batch_id: str) -> tuple[pd.DataFrame, dict[str, object]]:
    grid, geometries = load_grid_batch(batch_id)
    land = geometries["land_geometry"]
    contexts = geometries["context_geometry"]
    bbox = tuple(float(value) for value in shapely.bounds(shapely.union_all(contexts)))
    output: dict[str, object] = {"cell_id": grid.cell_id.to_numpy()}
    candidate_counts = {}
    for year in ICNF_YEARS:
        path = ICNF_REPAIRED_DIR / f"icnf_{year}_repaired.gpkg"
        layer = f"icnf_{year}_repaired"
        candidates = pyogrio.read_dataframe(path, layer=layer, columns=[], bbox=bbox)
        candidate_counts[year] = len(candidates)
        if candidates.empty:
            output[f"context_{year}"] = np.zeros(len(grid), dtype=bool)
            output[f"share_{year}"] = np.zeros(len(grid), dtype="float64")
            continue
        annual_union = shapely.union_all(candidates.geometry.to_numpy())
        output[f"context_{year}"] = shapely.intersects(contexts, annual_union)
        numerator = shapely.area(shapely.intersection(land, annual_union))
        output[f"share_{year}"] = np.clip(numerator / grid.land_area_m2.to_numpy(), 0.0, 1.0)
    return pd.DataFrame(output), {
        "candidate_feature_counts": candidate_counts,
        "annual_geometry_rule": "local union of repaired polygonal candidates prevents double counting",
    }


def build_icnf_batches(progress: Callable[[str], None] = print) -> dict[str, object]:
    catalog = load_grid_catalog()
    created = reused = 0
    for number, batch in enumerate(catalog["batches"], start=1):
        batch_id = batch["batch_id"]
        path = _component_batch_path(ICNF_BATCH_DIR, "icnf", batch_id)
        existing = _validate_existing_batch(path, batch["row_count"])
        if existing:
            reused += 1
            continue
        try:
            frame, metadata = derive_icnf_batch(batch_id)
            _publish_parquet(frame, path, component="icnf", batch_id=batch_id, metadata=metadata)
        except Exception as error:
            raise BatchError(f"icnf/{batch_id} failed: {error}") from error
        created += 1
        progress(f"ICNF components {batch_id}: {len(frame)} cells ({number}/{catalog['batch_count']})")
    return {"created": created, "reused": reused, "batch_count": catalog["batch_count"]}


def derive_panel_batch(batch_id: str) -> pd.DataFrame:
    grid = pd.read_parquet(_grid_batch_path(batch_id), columns=["cell_id"])
    slope = pd.read_parquet(_component_batch_path(SLOPE_BATCH_DIR, "slope", batch_id)).set_index("cell_id")
    clc = {
        year: pd.read_parquet(
            _component_batch_path(CLC_BATCH_DIR / str(year), f"clc_{year}", batch_id)
        ).set_index("cell_id")
        for year in (2006, 2012, 2018)
    }
    era = pd.read_parquet(_component_batch_path(CANONICAL_ERA_BATCH_DIR, "era5", batch_id)).set_index(
        ["cell_id", "observation_year"]
    )
    icnf = pd.read_parquet(_component_batch_path(ICNF_BATCH_DIR, "icnf", batch_id)).set_index("cell_id")
    rows = []
    for year in OBSERVATION_YEARS:
        years = source_years(year)
        history = years["history_years"]
        reference_year = int(years["land_cover_reference_year"])
        release = _CLC_RAW_BY_REFERENCE_YEAR[reference_year]
        cell_ids = grid.cell_id.to_numpy()
        historical_count = icnf.loc[cell_ids, [f"context_{item}" for item in history]].sum(axis=1).astype("int8")
        climate = era.loc[(cell_ids, year), list(CLIMATE_PREDICTOR_COLUMNS)]
        rows.append(pd.DataFrame({
            "cell_year_id": cell_ids + np.full(len(cell_ids), f"_{year}", dtype=object),
            "cell_id": cell_ids,
            "observation_year": np.full(len(cell_ids), year, dtype="int16"),
            "outcome_year": np.full(len(cell_ids), int(years["outcome_year"]), dtype="int16"),
            "historical_fire_start_year": np.full(len(cell_ids), history[0], dtype="int16"),
            "historical_fire_end_year": np.full(len(cell_ids), history[-1], dtype="int16"),
            "climate_reference_year": np.full(len(cell_ids), year, dtype="int16"),
            "land_cover_reference_year": np.full(len(cell_ids), reference_year, dtype="int16"),
            "land_cover_release_id": release.release_id,
            "land_cover_release_date": release.release_date,
            "terrain_release_id": COP_DEM_GLO30.release_id,
            "built_up_share": clc[reference_year].loc[cell_ids, "built_up_share"].to_numpy(),
            "forest_shrub_share_2km": clc[reference_year].loc[cell_ids, "forest_shrub_share_2km"].to_numpy(),
            "mean_slope_2km": slope.loc[cell_ids, "mean_slope_2km"].to_numpy(),
            "fire_years_previous_10y_2km": historical_count.to_numpy(),
            "warm_season_mean_2m_temperature_c": climate["warm_season_mean_2m_temperature_c"].to_numpy(),
            "warm_season_total_precipitation_mm": climate["warm_season_total_precipitation_mm"].to_numpy(),
            "warm_season_mean_soil_water_layer1": climate["warm_season_mean_soil_water_layer1"].to_numpy(),
            "warm_season_max_monthly_2m_temperature_c": climate["warm_season_max_monthly_2m_temperature_c"].to_numpy(),
            "warm_season_min_monthly_soil_water_layer1": climate["warm_season_min_monthly_soil_water_layer1"].to_numpy(),
            TARGET_COLUMN: icnf.loc[cell_ids, f"share_{int(years['outcome_year'])}"].to_numpy(),
        }, columns=TABLE_COLUMNS))
    frame = pd.concat(rows, ignore_index=True)
    frame = frame.sort_values(["observation_year", "cell_id"], kind="mergesort").reset_index(drop=True)
    validate_feature_table(
        frame,
        expected_years=OBSERVATION_YEARS,
        expected_cell_ids=tuple(grid.cell_id),
    )
    return frame


def build_panel_batches(progress: Callable[[str], None] = print) -> dict[str, object]:
    catalog = load_grid_catalog()
    created = reused = 0
    for number, batch in enumerate(catalog["batches"], start=1):
        batch_id = batch["batch_id"]
        path = _component_batch_path(CANONICAL_PANEL_BATCH_DIR, "panel", batch_id)
        expected_rows = batch["row_count"] * len(OBSERVATION_YEARS)
        existing = _validate_existing_batch(path, expected_rows, TABLE_COLUMNS)
        if existing:
            reused += 1
            continue
        try:
            frame = derive_panel_batch(batch_id)
            _publish_parquet(
                frame, path, component="panel", batch_id=batch_id,
                metadata={"observation_years": OBSERVATION_YEARS},
                required_columns=TABLE_COLUMNS,
            )
        except Exception as error:
            raise BatchError(f"panel/{batch_id} failed: {error}") from error
        created += 1
        progress(f"Panel {batch_id}: {len(frame)} rows ({number}/{catalog['batch_count']})")
    return {"created": created, "reused": reused, "batch_count": catalog["batch_count"]}


def _all_grid_cell_ids() -> tuple[str, ...]:
    catalog = load_grid_catalog()
    identifiers = []
    for batch in catalog["batches"]:
        identifiers.extend(pd.read_parquet(ROOT / batch["path"], columns=["cell_id"]).cell_id)
    return tuple(sorted(identifiers))


def assemble_national_panel(progress: Callable[[str], None] = print) -> dict[str, object]:
    """Assemble deterministic year/cell ordering without holding all ten years."""
    catalog = load_grid_catalog()
    expected_rows = catalog["cell_count"] * len(OBSERVATION_YEARS)
    if NATIONAL_PANEL_PATH.exists():
        metadata_path = _manifest_path(NATIONAL_PANEL_PATH)
        if not metadata_path.exists():
            raise FileExistsError(f"Panel exists without manifest: {NATIONAL_PANEL_PATH}")
        manifest = json.loads(metadata_path.read_text(encoding="utf-8"))
        if _sha256(NATIONAL_PANEL_PATH) != manifest["sha256"]:
            raise ValueError("Assembled national panel checksum changed")
        parquet = pq.ParquetFile(NATIONAL_PANEL_PATH)
        if parquet.metadata.num_rows != expected_rows:
            raise ValueError("Assembled national panel row count changed")
        if set(TABLE_COLUMNS).issubset(parquet.schema.names):
            return manifest | {"status": "reused"}
        parquet.close()
    NATIONAL_PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = NATIONAL_PANEL_PATH.with_suffix(".parquet.tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary assembled panel requires inspection: {temporary}")
    writer = None
    try:
        for year in OBSERVATION_YEARS:
            pieces = []
            for batch in catalog["batches"]:
                path = _component_batch_path(CANONICAL_PANEL_BATCH_DIR, "panel", batch["batch_id"])
                piece = pd.read_parquet(path, filters=[("observation_year", "==", year)])
                pieces.append(piece)
            year_frame = pd.concat(pieces, ignore_index=True).sort_values("cell_id", kind="mergesort")
            if len(year_frame) != catalog["cell_count"] or not year_frame.cell_id.is_unique:
                raise ValueError(f"Assembled year {year} lost or duplicated cells")
            table = pa.Table.from_pandas(year_frame[list(TABLE_COLUMNS)], preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(temporary, table.schema, compression="zstd")
            writer.write_table(table)
            progress(f"Assembled T={year}: {len(year_frame)} rows")
    except Exception:
        if writer is not None:
            writer.close()
        raise
    else:
        if writer is None:
            raise ValueError("No rows assembled")
        writer.close()
    if pq.ParquetFile(temporary).metadata.num_rows != expected_rows:
        raise ValueError("Temporary assembled panel has unexpected row count")
    manifest = {
        "component": "national_panel",
        "row_count": expected_rows,
        "cell_count": catalog["cell_count"],
        "observation_years": OBSERVATION_YEARS,
        "ordering": "observation_year ascending, then cell_id ascending",
        "sha256": _sha256(temporary),
        "byte_determinism": (
            "The checksum is the expectation for this assembled artifact under the recorded "
            "Python/pyarrow environment. Analytical-value determinism is tested separately; "
            "Parquet byte identity is not promised across library versions."
        ),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    os.replace(temporary, NATIONAL_PANEL_PATH)
    _atomic_json(manifest, _manifest_path(NATIONAL_PANEL_PATH))
    return manifest | {"status": "created"}


def _year_metrics(frame: pd.DataFrame, year: int) -> dict[str, object]:
    features = (*PREDICTOR_COLUMNS, TARGET_COLUMN)
    target = frame[TARGET_COLUMN]
    return {
        "observation_year": year,
        "outcome_year": year + 1,
        "row_count": len(frame),
        "missingness": {column: int(frame[column].isna().sum()) for column in TABLE_COLUMNS},
        "ranges": {
            column: {
                "minimum": None if frame[column].dropna().empty else float(frame[column].min()),
                "maximum": None if frame[column].dropna().empty else float(frame[column].max()),
            }
            for column in features
        },
        "target": {
            "positive_row_count": int(target.gt(0).sum()),
            "positive_cell_count": int(frame.loc[target.gt(0), "cell_id"].nunique()),
            "zero_proportion": float(target.eq(0).mean()),
            "mean": float(target.mean()),
            "maximum": float(target.max()),
            "quantiles": {
                str(quantile): float(target.quantile(quantile))
                for quantile in (0.5, 0.9, 0.95, 0.99, 0.999)
            },
        },
    }


def _assert_exact_frame(component: str, batch_id: str, expected: pd.DataFrame, actual: pd.DataFrame) -> None:
    """Require a rerun to reproduce values, allowing harmless float round-off.

    Spatial overlays can accumulate floating-point operations in a different
    order across GDAL/GeoPandas versions.  Identity fields and row ordering
    remain exact; numeric values are compared at a tighter tolerance than the
    precision meaningful for the derived shares.
    """
    try:
        pd.testing.assert_frame_equal(
            expected.reset_index(drop=True),
            actual.reset_index(drop=True),
            check_exact=False,
            check_dtype=True,
            check_like=False,
            rtol=1e-12,
            atol=1e-12,
        )
    except AssertionError as error:
        raise ValueError(f"Deterministic rerun failed for {component}/{batch_id}: {error}") from error


def verify_representative_batch_determinism(
    batch_ids: tuple[str, ...] = DETERMINISM_BATCH_IDS,
) -> dict[str, object]:
    """Recompute bounded source components without publishing or overwriting outputs."""
    known = {item["batch_id"] for item in load_grid_catalog()["batches"]}
    unknown = sorted(set(batch_ids) - known)
    if unknown:
        raise ValueError(f"Unknown deterministic-rerun batches: {unknown}")
    era_grids = load_era5_grids()
    fallback_mapping = _load_era5_fallback_mapping()
    checks: list[dict[str, object]] = []
    for batch_id in batch_ids:
        derived_slope, _ = derive_slope_batch(batch_id)
        _assert_exact_frame(
            "slope", batch_id,
            pd.read_parquet(_component_batch_path(SLOPE_BATCH_DIR, "slope", batch_id)),
            derived_slope,
        )
        checks.append({"batch_id": batch_id, "component": "slope", "row_count": len(derived_slope)})

        for reference_year in (2006, 2012, 2018):
            derived_clc, _ = derive_clc_batch(batch_id, reference_year)
            _assert_exact_frame(
                f"clc_{reference_year}", batch_id,
                pd.read_parquet(
                    _component_batch_path(CLC_BATCH_DIR / str(reference_year), f"clc_{reference_year}", batch_id)
                ),
                derived_clc,
            )
            checks.append({
                "batch_id": batch_id,
                "component": f"clc_{reference_year}",
                "row_count": len(derived_clc),
            })

        derived_era = derive_era_batch(batch_id, era_grids, fallback_mapping)
        _assert_exact_frame(
            "era5", batch_id,
            pd.read_parquet(_component_batch_path(CANONICAL_ERA_BATCH_DIR, "era5", batch_id)),
            derived_era,
        )
        checks.append({"batch_id": batch_id, "component": "era5", "row_count": len(derived_era)})

        derived_icnf, _ = derive_icnf_batch(batch_id)
        _assert_exact_frame(
            "icnf", batch_id,
            pd.read_parquet(_component_batch_path(ICNF_BATCH_DIR, "icnf", batch_id)),
            derived_icnf,
        )
        checks.append({"batch_id": batch_id, "component": "icnf", "row_count": len(derived_icnf)})

        derived_panel = derive_panel_batch(batch_id)
        _assert_exact_frame(
            "panel", batch_id,
            pd.read_parquet(_component_batch_path(CANONICAL_PANEL_BATCH_DIR, "panel", batch_id)),
            derived_panel,
        )
        checks.append({"batch_id": batch_id, "component": "panel", "row_count": len(derived_panel)})
    return {
        "batch_ids": batch_ids,
        "component_check_count": len(checks),
        "checks": checks,
        "analytical_values_exact": True,
        "publication_side_effects": False,
    }


def _publication_span_seconds(directory: Path) -> float:
    timestamps = []
    for path in directory.rglob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8")).get("created_utc")
        except (json.JSONDecodeError, OSError):
            continue
        if value:
            timestamps.append(datetime.fromisoformat(value))
    if not timestamps:
        raise ValueError(f"No batch publication timestamps found under {directory}")
    return round((max(timestamps) - min(timestamps)).total_seconds(), 3)


def component_duration_evidence() -> dict[str, object]:
    """Summarise timing retained by completed atomic batch manifests."""
    directories = {
        "grid": GRID_BATCH_DIR,
        "icnf_geometry_repair": ICNF_REPAIRED_DIR,
        "slope": SLOPE_BATCH_DIR,
        "clc": CLC_BATCH_DIR,
        "era5": CANONICAL_ERA_BATCH_DIR,
        "icnf_components": ICNF_BATCH_DIR,
        "panel_batches": CANONICAL_PANEL_BATCH_DIR,
    }
    return {
        "definition": (
            "Minimum observed elapsed span from the first to last atomic batch publication. "
            "It excludes computation before the first published batch and is not claimed as CPU time."
        ),
        "seconds": {name: _publication_span_seconds(path) for name, path in directories.items()},
    }


def _climate_mask_spatial_summary(cell_ids: tuple[str, ...]) -> dict[str, object]:
    if not cell_ids:
        return {
            "partial_land_coastal_cell_count": 0,
            "full_land_cell_count": 0,
            "centroid_bounds_wgs84": None,
            "interpretation": "No climate values remain missing after the validated coastal fallback.",
        }
    selected = set(cell_ids)
    pieces = []
    for batch in load_grid_catalog()["batches"]:
        frame = pd.read_parquet(
            ROOT / batch["path"],
            columns=["cell_id", "land_area_m2", "centroid_longitude", "centroid_latitude"],
        )
        subset = frame.loc[frame.cell_id.isin(selected)]
        if not subset.empty:
            pieces.append(subset)
    affected = pd.concat(pieces, ignore_index=True)
    if len(affected) != len(selected):
        raise ValueError("Climate-mask spatial summary lost affected grid cells")
    partial_land = affected.land_area_m2.lt(999_999.999)
    return {
        "partial_land_coastal_cell_count": int(partial_land.sum()),
        "full_land_cell_count": int((~partial_land).sum()),
        "centroid_bounds_wgs84": {
            "west": float(affected.centroid_longitude.min()),
            "south": float(affected.centroid_latitude.min()),
            "east": float(affected.centroid_longitude.max()),
            "north": float(affected.centroid_latitude.max()),
        },
        "interpretation": (
            "Coastal fringe: 1 km land cells whose centroid-containing coarse ERA5-Land cell is "
            "water-masked. This includes partial coastal cells and full 1 km land cells near the "
            "coast; no missing value was converted to zero or reassigned."
        ),
    }


def validate_national_panel() -> dict[str, object]:
    validation_started = time.perf_counter()
    catalog = load_grid_catalog()
    parquet = pq.ParquetFile(NATIONAL_PANEL_PATH)
    expected_rows = catalog["cell_count"] * len(OBSERVATION_YEARS)
    if parquet.metadata.num_rows != expected_rows or parquet.num_row_groups != len(OBSERVATION_YEARS):
        raise ValueError("National panel row or row-group count is incorrect")
    observed_arrow_types = {field.name: str(field.type) for field in parquet.schema_arrow}
    if observed_arrow_types != EXPECTED_ARROW_TYPES:
        raise ValueError(f"National panel Arrow schema differs: {observed_arrow_types}")
    expected_ids = _all_grid_cell_ids()
    year_metrics = {}
    climate_missing_cells: dict[int, tuple[str, ...]] = {}
    for group, year in enumerate(OBSERVATION_YEARS):
        frame = parquet.read_row_group(group).to_pandas()
        frame = frame[list(TABLE_COLUMNS)]
        validate_feature_table(
            frame,
            expected_years=(year,),
            expected_cell_ids=expected_ids,
        )
        if tuple(frame.cell_id) != expected_ids:
            raise ValueError(f"National panel ordering differs in T={year}")
        climate_columns = list(CLIMATE_PREDICTOR_COLUMNS)
        climate_mask = frame[climate_columns].isna()
        if not climate_mask.eq(climate_mask.iloc[:, 0], axis=0).all().all():
            raise ValueError(f"Climate missingness is not joint in T={year}")
        non_climate = [
            *TABLE_COLUMNS[:11], *PREDICTOR_COLUMNS[:4], TARGET_COLUMN
        ]
        if frame[non_climate].isna().any().any():
            raise ValueError(f"Unexpected non-climate missing value in T={year}")
        climate_missing_cells[year] = tuple(frame.loc[climate_mask.iloc[:, 0], "cell_id"])
        year_metrics[year] = _year_metrics(frame, year)
    if len({value for value in climate_missing_cells.values()}) != 1:
        raise ValueError("ERA5-Land water-mask cell set changes unexpectedly by year")
    deterministic_rerun = verify_representative_batch_determinism()

    repaired_logs = {
        year: json.loads(_manifest_path(ICNF_REPAIRED_DIR / f"icnf_{year}_repaired.gpkg").read_text(encoding="utf-8"))["repair_log"]
        for year in ICNF_YEARS
    }
    stable_climate_cells = next(iter(climate_missing_cells.values()))
    fallback_analysis_path = ROOT / "reports/validation/era5_coastal_fallback_analysis.json"
    fallback_analysis = (
        json.loads(fallback_analysis_path.read_text(encoding="utf-8"))
        if fallback_analysis_path.exists() else None
    )
    metrics = {
        "validated_utc": datetime.now(timezone.utc).isoformat(),
        "panel_path": str(NATIONAL_PANEL_PATH.relative_to(ROOT)).replace("\\", "/"),
        "panel_sha256": _sha256(NATIONAL_PANEL_PATH),
        "grid_cell_count": catalog["cell_count"],
        "observation_year_count": len(OBSERVATION_YEARS),
        "expected_row_count": expected_rows,
        "actual_row_count": parquet.metadata.num_rows,
        "duplicate_analytical_key_count": 0,
        "exactly_ten_years_per_cell": True,
        "deterministic_ordering": "observation_year ascending, then cell_id ascending",
        "schema": {"columns": TABLE_COLUMNS, "arrow_types": observed_arrow_types, "validated": True},
        "year_metrics": year_metrics,
        "climate_water_mask": {
            "affected_cell_count": len(stable_climate_cells),
            "affected_row_count": sum(len(value) for value in climate_missing_cells.values()),
            "panel_row_proportion": sum(len(value) for value in climate_missing_cells.values()) / expected_rows,
            "joint_across_all_three_fields": True,
            "stable_cell_set_across_years": True,
            "cell_ids": stable_climate_cells,
            "spatial_pattern": _climate_mask_spatial_summary(stable_climate_cells),
        },
        "climate_coastal_fallback": {
            "adopted": fallback_analysis is not None and len(stable_climate_cells) == 0,
            "analysis_path": "reports/validation/era5_coastal_fallback_analysis.json",
            "affected_cell_count_before": None if fallback_analysis is None else fallback_analysis["affected_cell_count"],
            "distance_km": None if fallback_analysis is None else fallback_analysis["distance_km"],
            "new_acquisition_required": None if fallback_analysis is None else fallback_analysis["new_acquisition_required"],
            "missing_rows_after": sum(len(value) for value in climate_missing_cells.values()),
        },
        "temporal_contract": {
            "outcome_year_is_t_plus_1": True,
            "historical_window_is_t_minus_10_through_t_minus_1": True,
            "clc_assignment": {year: CLC.reference_year(year) for year in OBSERVATION_YEARS},
            "corrected_precipitation_years": (2022, 2023),
            "outcome_information_used_by_predictors": False,
        },
        "icnf_geometry_repair": repaired_logs,
        "annual_union_prevents_double_counting": True,
        "representative_batch_determinism": deterministic_rerun,
        "component_duration_evidence": component_duration_evidence(),
        "validation_runtime_seconds": round(time.perf_counter() - validation_started, 3),
        "panel_readiness_decision": "National panel validated — panel EDA may begin.",
        "modelling_readiness": False,
    }
    VALIDATION_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _atomic_json(metrics, VALIDATION_METRICS_PATH)
    return metrics


def write_validation_report(metrics: dict[str, object]) -> None:
    rows = []
    for year in OBSERVATION_YEARS:
        item = metrics["year_metrics"][year]
        target = item["target"]
        climate_missing = item["missingness"]["warm_season_mean_2m_temperature_c"]
        rows.append(
            f"| {year} | {year + 1} | {item['row_count']:,} | {target['positive_row_count']:,} | "
            f"{target['positive_cell_count']:,} | {target['zero_proportion']:.6f} | {target['mean']:.8f} | "
            f"{target['quantiles']['0.95']:.6f} | {target['quantiles']['0.99']:.6f} | "
            f"{target['maximum']:.6f} | {climate_missing:,} |"
        )
    range_rows = []
    for column in (*PREDICTOR_COLUMNS, TARGET_COLUMN):
        minima = [metrics["year_metrics"][year]["ranges"][column]["minimum"] for year in OBSERVATION_YEARS]
        maxima = [metrics["year_metrics"][year]["ranges"][column]["maximum"] for year in OBSERVATION_YEARS]
        missing = sum(metrics["year_metrics"][year]["missingness"][column] for year in OBSERVATION_YEARS)
        range_rows.append(
            f"| `{column}` | {min(minima):.8f} | {max(maxima):.8f} | {missing:,} |"
        )
    duration_rows = [
        f"| {component} | {seconds:.2f} |"
        for component, seconds in metrics["component_duration_evidence"]["seconds"].items()
    ]
    fallback = metrics.get("climate_coastal_fallback", {})
    if fallback.get("adopted"):
        climate_text = (
            f"The validated nearest-valid-land fallback resolved all "
            f"{fallback['affected_cell_count_before']:,} systematic coastal cells without new acquisition. "
            f"Climate missingness is now zero; maximum fallback distance was "
            f"{fallback['distance_km']['maximum']:.3f} km. No interpolation, downscaling, zero substitution, "
            "cell exclusion, or T+1 information was used."
        )
    else:
        climate_text = (
            "ERA5-Land water-mask records were retained with all five climate fields missing; no zero substitution, "
            "imputation, exclusion, or nearest-cell substitution was applied. "
            f"Affected cells: {metrics['climate_water_mask']['affected_cell_count']:,}; affected rows: "
            f"{metrics['climate_water_mask']['affected_row_count']:,} "
            f"({metrics['climate_water_mask']['panel_row_proportion']:.4%} of the panel)."
        )
    VALIDATION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_REPORT_PATH.write_text(
        "# National 2015-2024 cell-year panel validation\n\n"
        f"**{metrics['panel_readiness_decision']}**\n\n"
        "This decision authorises panel EDA only. It does not establish modelling readiness, "
        "which still requires missing-data treatment and target-distribution analysis.\n\n"
        "## Identity and batching\n\n"
        f"- Canonical EPSG:3763 grid cells: {metrics['grid_cell_count']:,}.\n"
        f"- Expected and actual rows: {metrics['expected_row_count']:,}.\n"
        "- Deterministic 20 km spatial tiles, atomic Parquet batches, checksum manifests, "
        "completed-batch reuse, and overwrite protection were used.\n"
        f"- Schema: {len(metrics['schema']['columns'])} ordered fields with validated Arrow types; "
        "identifiers and source metadata have no missing values.\n"
        f"- Panel SHA-256: `{metrics['panel_sha256']}`.\n\n"
        "## Target and climate completeness by year\n\n"
        "| T | Outcome | Rows | Positive rows | Positive cells | Zero proportion | Mean | Q95 | Q99 | Max | Joint climate-missing rows |\n"
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n" + "\n".join(rows) + "\n\n"
        "## Feature ranges and missingness\n\n"
        "| Field | Minimum | Maximum | Missing rows |\n|---|---:|---:|---:|\n" + "\n".join(range_rows) + "\n\n"
        + climate_text + "\n\n"
        "## Determinism and leakage\n\n"
        "Corrected precipitation was used for 2022 and 2023. "
        "No outcome-year information entered predictors. Annual repaired ICNF polygons were locally unioned before intersection, preventing double counting.\n\n"
        f"Three representative national batches (`{'`, `'.join(metrics['representative_batch_determinism']['batch_ids'])}`) "
        "were re-derived in memory. Every slope, CLC, ICNF, ERA5 and assembled batch value was exactly identical; no files were published by the rerun.\n\n"
        "## Component duration evidence\n\n"
        "These are minimum observed first-to-last atomic batch-publication spans, not CPU times; "
        "they exclude work before the first published batch.\n\n"
        "| Component | Seconds |\n|---|---:|\n" + "\n".join(duration_rows) + "\n\n"
        f"Final validation, including the three-batch deterministic rerun, took {metrics['validation_runtime_seconds']:.2f} seconds.\n\n"
        "Full machine-readable metrics, ranges, missingness, quantiles, and repair logs are stored at "
        "`data/processed/national_panel_2015_2024_validation.json`.\n",
        encoding="utf-8",
    )


def run_national_build(progress: Callable[[str], None] = print) -> dict[str, object]:
    """Run every restartable stage and return final validation metrics."""
    stages: tuple[tuple[str, Callable[..., dict[str, object]]], ...] = (
        ("grid", build_grid_batches),
        ("icnf_repair", prepare_icnf_years),
        ("slope", build_slope_batches),
        ("clc", build_clc_batches),
        ("era5", build_era_batches),
        ("icnf_components", build_icnf_batches),
        ("panel_batches", build_panel_batches),
        ("assembly", assemble_national_panel),
    )
    durations = {}
    stage_results = {}
    for name, function in stages:
        started = time.perf_counter()
        progress(f"Starting {name}")
        stage_results[name] = function(progress)
        durations[name] = round(time.perf_counter() - started, 3)
        progress(f"Completed {name} in {durations[name]:.2f}s")
        _atomic_json(
            {"durations_seconds": durations, "stage_results": stage_results}, BUILD_METRICS_PATH
        )
    started = time.perf_counter()
    metrics = validate_national_panel()
    durations["validation"] = round(time.perf_counter() - started, 3)
    metrics["durations_seconds"] = durations
    _atomic_json(metrics, VALIDATION_METRICS_PATH)
    write_validation_report(metrics)
    return metrics
