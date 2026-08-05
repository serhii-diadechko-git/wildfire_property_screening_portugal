"""Controlled canonical feature derivation for a small representative sample.

This module intentionally reuses the existing EPSG:3763 grid and processes only
ten declared cells.  It is an implementation gate, not a national-panel build.
Raw archives are opened read-only and ZIP members are extracted only to a system
temporary directory.
"""

from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path
import warnings
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import rasterio
from rasterio.features import geometry_mask
from rasterio.merge import merge
from rasterio.transform import array_bounds
from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_bounds
import shapely
from shapely.geometry import mapping
import xarray as xr

from src.clc_validation import CANONICAL_CLC_CLASS_MAPPING
from src.config import CLC, SPATIAL, TEMPORAL
from src.feature_contract import (
    FIELD_CONTRACTS,
    PREDICTOR_COLUMNS,
    TABLE_COLUMNS,
    TARGET_COLUMN,
    source_years,
    validate_feature_table,
)
from src.source_registry import (
    CLC_2006_V2020_20U1,
    CLC_2012_V2020_20U1,
    CLC_2018_V2020_20U1,
    CLC_PREPARED_PORTUGAL_LAYERS,
    COP_DEM_GLO30,
    COP_DEM_GLO30_TILES,
    ERA5_LAND_FULL_SCOPE_ARCHIVES,
    ERA5_LAND_PRECIPITATION_CORRECTIONS,
)


ROOT = Path(__file__).resolve().parents[1]
GRID_PATH = ROOT / "data/processed/pilot_2023_to_2024/pilot_2023_to_2024_icnf_caop.gpkg"
BOUNDARY_PATH = ROOT / "data/processed/reference/mainland_boundary_caop2025.gpkg"
ICNF_ROOT = ROOT / "data/raw/wildfire/icnf_burned_areas"
OUTPUT_DIR = ROOT / "data/processed/feature_derivation_pilot"
OUTPUT_PARQUET = OUTPUT_DIR / "representative_feature_pilot.parquet"
OUTPUT_GPKG = OUTPUT_DIR / "representative_feature_pilot.gpkg"
REPORT_PATH = ROOT / "reports/validation/representative_feature_derivation_pilot.md"
ERA5_FALLBACK_MAPPING_PATH = (
    ROOT / "data/interim/national_panel_2015_2024/era5_coastal_fallback_mapping.parquet"
)

PILOT_YEARS = (2015, 2016, 2019, 2023)
PILOT_CELL_REASONS = {
    "PT3763_002356": "high built-up share with valid ERA5 land context",
    "PT3763_080948": "high forest/shrub share",
    "PT3763_001564": "maximum prior-fire-year count in the existing 2023 feasibility artifact",
    "PT3763_000000": "coastal/boundary cell in an ERA5-Land water-mask coarse cell",
    "PT3763_037982": "wet northern forest context",
    "PT3763_040163": "dry southern forest context",
    "PT3763_034039": "contains the representative point of the largest repaired 2016 perimeter",
    "PT3763_039441": "contains the representative point of the largest repaired 2017 perimeter",
    "PT3763_053960": "contains the representative point of the largest repaired 2020 perimeter",
    "PT3763_043203": "contains the representative point of the largest repaired 2024 perimeter",
}
PILOT_CELL_IDS = tuple(PILOT_CELL_REASONS)

_CLC_RAW_BY_REFERENCE_YEAR = {
    2006: CLC_2006_V2020_20U1,
    2012: CLC_2012_V2020_20U1,
    2018: CLC_2018_V2020_20U1,
}


def era5_source_paths(predictor_year: int) -> dict[str, Path]:
    """Select the annual GRIBs, including mandatory corrected precipitation."""
    if predictor_year not in ERA5_LAND_FULL_SCOPE_ARCHIVES:
        raise ValueError(f"No registered ERA5-Land file for {predictor_year}")
    annual = ERA5_LAND_FULL_SCOPE_ARCHIVES[predictor_year]
    precipitation = ERA5_LAND_PRECIPITATION_CORRECTIONS.get(predictor_year, annual)
    if predictor_year in (2022, 2023) and precipitation is annual:
        raise ValueError(f"Corrected precipitation source is mandatory for {predictor_year}")
    return {
        "temperature_and_soil_water": ROOT / annual.raw_path,
        "precipitation": ROOT / precipitation.raw_path,
    }


def jjas_total_precipitation_mm(values_m_per_day: np.ndarray, months: tuple[int, ...]) -> np.ndarray:
    """Convert monthly mean daily precipitation (m/day) to a true JJAS total."""
    days = {6: 30, 7: 31, 8: 31, 9: 30}
    if months != (6, 7, 8, 9):
        raise ValueError(f"Expected ordered JJAS months, found {months}")
    weights = np.asarray([days[month] for month in months], dtype="float64")[:, None, None]
    all_missing = np.isnan(values_m_per_day).all(axis=0)
    totals = np.nansum(values_m_per_day * weights, axis=0) * 1000.0
    totals[all_missing] = np.nan
    return totals


def _read_grib_variable(path: Path, short_name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[int, ...]]:
    dataset = xr.open_dataset(
        path,
        engine="cfgrib",
        backend_kwargs={"indexpath": "", "filter_by_keys": {"shortName": short_name}},
    )
    try:
        variable = next(iter(dataset.data_vars))
        values = np.asarray(dataset[variable].values, dtype="float64")
        time_coordinate = "time" if "time" in dataset.coords else "valid_time"
        months = tuple(int(str(value.astype("datetime64[M]"))[-2:]) for value in dataset[time_coordinate].values)
        return (
            np.asarray(dataset.latitude.values, dtype="float64"),
            np.asarray(dataset.longitude.values, dtype="float64"),
            values,
            months,
        )
    finally:
        dataset.close()


def derive_era5_context(predictor_year: int, cells: gpd.GeoDataFrame) -> pd.DataFrame:
    """Assign containing-cell context, then the accepted static nearest-land fallback."""
    paths = era5_source_paths(predictor_year)
    latitude, longitude, temperature_k, months = _read_grib_variable(
        paths["temperature_and_soil_water"], "2t"
    )
    soil_lat, soil_lon, soil_water, soil_months = _read_grib_variable(
        paths["temperature_and_soil_water"], "swvl1"
    )
    precip_lat, precip_lon, precipitation, precip_months = _read_grib_variable(
        paths["precipitation"], "tp"
    )
    if not (
        months == soil_months == precip_months == (6, 7, 8, 9)
        and np.array_equal(latitude, soil_lat)
        and np.array_equal(latitude, precip_lat)
        and np.array_equal(longitude, soil_lon)
        and np.array_equal(longitude, precip_lon)
    ):
        raise ValueError(f"ERA5-Land variable grids/months do not align for {predictor_year}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        grids = {
            "warm_season_mean_2m_temperature_c": np.nanmean(temperature_k, axis=0) - 273.15,
            "warm_season_total_precipitation_mm": jjas_total_precipitation_mm(precipitation, months),
            "warm_season_mean_soil_water_layer1": np.nanmean(soil_water, axis=0),
        }
    centres = cells.geometry.centroid.to_crs(4326)
    lat_index = np.abs(latitude[:, None] - centres.y.to_numpy()).argmin(axis=0)
    lon_index = np.abs(longitude[:, None] - centres.x.to_numpy()).argmin(axis=0)
    result = pd.DataFrame(index=cells.cell_id)
    for feature, values in grids.items():
        result[feature] = values[lat_index, lon_index]
    mask = result["warm_season_mean_2m_temperature_c"].isna()
    result.loc[mask, list(grids)] = np.nan
    if not result.isna().eq(mask, axis=0).all().all():
        raise ValueError(f"ERA5-Land water mask is inconsistent for {predictor_year}")
    if mask.any():
        if not ERA5_FALLBACK_MAPPING_PATH.exists():
            raise FileNotFoundError("Accepted ERA5 coastal fallback mapping is missing")
        fallback = pd.read_parquet(
            ERA5_FALLBACK_MAPPING_PATH,
            columns=["cell_id", "fallback_flat_index"],
        ).set_index("cell_id")
        affected_ids = result.index[mask]
        missing_mapping = affected_ids.difference(fallback.index)
        if len(missing_mapping):
            raise ValueError(f"No accepted ERA5 fallback for cells: {list(missing_mapping[:5])}")
        for cell_id in affected_ids:
            flat_index = int(fallback.loc[cell_id, "fallback_flat_index"])
            for feature, values in grids.items():
                result.loc[cell_id, feature] = float(np.asarray(values).ravel()[flat_index])
    if result.isna().any().any():
        raise ValueError(f"Accepted ERA5 coastal fallback left missing values for {predictor_year}")
    return result


def _read_sample_cells() -> tuple[gpd.GeoDataFrame, object]:
    pieces = []
    for cell_id in PILOT_CELL_IDS:
        part = pyogrio.read_dataframe(GRID_PATH, columns=["cell_id"], where=f"cell_id = '{cell_id}'")
        if len(part) != 1:
            raise ValueError(f"Expected exactly one existing grid cell for {cell_id}")
        pieces.append(part)
    cells = gpd.GeoDataFrame(pd.concat(pieces, ignore_index=True), crs=SPATIAL.analysis_crs)
    cells = cells.set_index("cell_id", drop=False).loc[list(PILOT_CELL_IDS)].reset_index(drop=True)
    if str(cells.crs) != SPATIAL.analysis_crs or not cells.cell_id.is_unique:
        raise ValueError("Representative cells do not preserve the canonical grid contract")
    boundary_frame = pyogrio.read_dataframe(BOUNDARY_PATH, columns=[])
    if len(boundary_frame) != 1 or str(boundary_frame.crs) != SPATIAL.analysis_crs:
        raise ValueError("Canonical mainland boundary contract failed")
    boundary = boundary_frame.geometry.iloc[0]
    cells["land_geometry"] = [geometry.intersection(boundary) for geometry in cells.geometry]
    cells["context_geometry"] = [
        geometry.buffer(SPATIAL.context_buffer_metres).intersection(boundary)
        for geometry in cells.geometry
    ]
    if any(geometry.is_empty for geometry in cells.land_geometry) or any(
        geometry.is_empty for geometry in cells.context_geometry
    ):
        raise ValueError("Representative sample unexpectedly lost mainland geometry")
    return cells, boundary


def _polygonal_geometry(geometry):
    if geometry is None or geometry.is_empty:
        return None
    if geometry.geom_type in ("Polygon", "MultiPolygon"):
        return geometry
    if geometry.geom_type == "GeometryCollection":
        parts = [_polygonal_geometry(part) for part in geometry.geoms]
        parts = [part for part in parts if part is not None and not part.is_empty]
        if parts:
            merged = shapely.union_all(parts)
            return merged if merged.geom_type in ("Polygon", "MultiPolygon") else None
    return None


def _icnf_vsi_path(archive_path: Path) -> str:
    """Return a GDAL /vsizip path so immutable raw ZIPs need no extraction."""
    required_suffixes = (".shp", ".shx", ".dbf", ".prj")
    with zipfile.ZipFile(archive_path) as archive:
        members = [member for member in archive.namelist() if member.lower().endswith(required_suffixes)]
        suffixes = {Path(member).suffix.lower() for member in members}
        if not set(required_suffixes).issubset(suffixes):
            raise ValueError(f"Required Shapefile sidecars missing from {archive_path}")
        shapefiles = [member for member in members if member.lower().endswith(".shp")]
        if len(shapefiles) != 1:
            raise ValueError(f"Expected exactly one Shapefile in {archive_path}")
    return f"/vsizip/{archive_path.resolve().as_posix()}/{shapefiles[0]}"


def _repair_year(frame: gpd.GeoDataFrame, year: int, sample_extent) -> tuple[object, dict[str, object]]:
    input_count = len(frame)
    raw_geometries = list(frame.geometry)
    before_area = float(sum(geometry.area for geometry in raw_geometries if geometry is not None))
    invalid_before = [geometry is not None and not geometry.is_empty and not geometry.is_valid for geometry in raw_geometries]
    accepted = []
    area_change_percentages = []
    repaired_count = 0
    rejected_count = 0
    after_area = 0.0
    for geometry, was_invalid in zip(raw_geometries, invalid_before, strict=True):
        candidate = shapely.make_valid(geometry) if was_invalid else geometry
        candidate = _polygonal_geometry(candidate)
        if candidate is None or candidate.is_empty or not candidate.is_valid:
            rejected_count += 1
            continue
        accepted.append(candidate)
        after_area += candidate.area
        if was_invalid:
            repaired_count += 1
            original_area = geometry.area
            change = abs(candidate.area - original_area) / original_area * 100 if original_area else np.inf
            area_change_percentages.append(change)
    local = [geometry for geometry in accepted if geometry.intersects(sample_extent)]
    annual_union = shapely.union_all(local) if local else shapely.GeometryCollection()
    log = {
        "year": year,
        "input_count": input_count,
        "invalid_before_count": int(sum(invalid_before)),
        "repaired_count": repaired_count,
        "rejected_count": rejected_count,
        "accepted_count": len(accepted),
        "sample_candidate_count": len(local),
        "input_area_m2": before_area,
        "accepted_area_m2": after_area,
        "total_area_change_percent": (after_area - before_area) / before_area * 100 if before_area else 0.0,
        "repairs_area_change_over_0_1_percent": sum(value > 0.1 for value in area_change_percentages),
        "repairs_area_change_over_1_percent": sum(value > 1.0 for value in area_change_percentages),
        "repairs_area_change_over_5_percent": sum(value > 5.0 for value in area_change_percentages),
    }
    return annual_union, log


def load_icnf_annual_geometries(
    years: tuple[int, ...], sample_extent
) -> tuple[dict[int, object], dict[int, dict[str, object]]]:
    """Repair immutable annual sources in memory and union per year for the sample."""
    annual: dict[int, object] = {}
    logs: dict[int, dict[str, object]] = {}
    early_years = tuple(year for year in years if 2000 <= year <= 2008)
    if early_years:
        path = _icnf_vsi_path(ICNF_ROOT / "ardida_2000_2008.zip")
        combined = pyogrio.read_dataframe(path, columns=["Ano"])
        for year in early_years:
            frame = combined.loc[combined.Ano.astype(int) == year].copy()
            annual[year], logs[year] = _repair_year(frame, year, sample_extent)
    for year in years:
        if year in annual:
            continue
        archive_path = ICNF_ROOT / f"ardida_{year}.zip"
        if not archive_path.is_file():
            raise FileNotFoundError(f"Missing required immutable ICNF archive: {archive_path}")
        path = _icnf_vsi_path(archive_path)
        frame = pyogrio.read_dataframe(path, columns=[])
        annual[year], logs[year] = _repair_year(frame, year, sample_extent)
    return annual, logs


def derive_icnf_features(
    cells: gpd.GeoDataFrame, predictor_years: tuple[int, ...]
) -> tuple[dict[int, pd.DataFrame], dict[int, dict[str, object]]]:
    required_years = tuple(sorted({
        year
        for predictor_year in predictor_years
        for year in (*TEMPORAL.historical_years(predictor_year), TEMPORAL.outcome_year(predictor_year))
    }))
    sample_extent = shapely.union_all(cells.context_geometry.to_numpy())
    annual, logs = load_icnf_annual_geometries(required_years, sample_extent)
    result = {}
    for predictor_year in predictor_years:
        history_years = TEMPORAL.historical_years(predictor_year)
        outcome_year = TEMPORAL.outcome_year(predictor_year)
        rows = []
        for row in cells.itertuples(index=False):
            history_count = sum(
                not annual[year].is_empty and annual[year].intersects(row.context_geometry)
                for year in history_years
            )
            burned = annual[outcome_year]
            numerator = 0.0 if burned.is_empty else row.land_geometry.intersection(burned).area
            denominator = row.land_geometry.area
            rows.append((row.cell_id, history_count, min(1.0, max(0.0, numerator / denominator))))
        result[predictor_year] = pd.DataFrame(
            rows,
            columns=["cell_id", "fire_years_previous_10y_2km", TARGET_COLUMN],
        ).set_index("cell_id")
    return result, logs


def derive_clc_shares(
    cells: gpd.GeoDataFrame, reference_year: int
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Area-weight the cell and outward-buffer CLC shares in EPSG:3035."""
    record = CLC_PREPARED_PORTUGAL_LAYERS[reference_year]
    path = ROOT / record.prepared_path
    code_field = record.validation_facts.class_code_field
    transformed = gpd.GeoDataFrame(
        {
            "cell_id": cells.cell_id,
            "land_geometry": gpd.GeoSeries(cells.land_geometry, crs=SPATIAL.analysis_crs).to_crs(CLC.area_processing_crs),
            "context_geometry": gpd.GeoSeries(cells.context_geometry, crs=SPATIAL.analysis_crs).to_crs(CLC.area_processing_crs),
        },
        geometry="land_geometry",
        crs=CLC.area_processing_crs,
    )
    rows = []
    candidate_counts = {}
    for row in transformed.itertuples(index=False):
        bbox = tuple(float(value) for value in row.context_geometry.bounds)
        candidates = pyogrio.read_dataframe(
            path,
            layer=record.validation_facts.layer_name,
            columns=[code_field],
            bbox=bbox,
        )
        candidate_counts[row.cell_id] = len(candidates)
        codes = candidates[code_field].astype(str).str.zfill(3)
        values = {}
        for feature, area_geometry in (
            ("built_up_share", row.land_geometry),
            ("forest_shrub_share_2km", row.context_geometry),
        ):
            selected = candidates.loc[codes.isin(CANONICAL_CLC_CLASS_MAPPING[feature])]
            numerator = 0.0
            if not selected.empty:
                class_union = shapely.union_all(selected.geometry.to_numpy())
                numerator = area_geometry.intersection(class_union).area
            values[feature] = min(1.0, max(0.0, numerator / area_geometry.area))
        rows.append((row.cell_id, values["built_up_share"], values["forest_shrub_share_2km"]))
    return (
        pd.DataFrame(rows, columns=["cell_id", "built_up_share", "forest_shrub_share_2km"]).set_index("cell_id"),
        candidate_counts,
    )


def _tile_bounds(tile_id: str) -> tuple[float, float, float, float]:
    latitude = int(tile_id[1:3])
    longitude = -int(tile_id.split("W", 1)[1].split("_", 1)[0])
    return longitude, latitude, longitude + 1, latitude + 1


def derive_mean_slope_2km(cells: gpd.GeoDataFrame) -> tuple[pd.Series, dict[str, object]]:
    """Calculate sample mean slope after warping GLO-30 elevations to metric EPSG:3763."""
    values = {}
    diagnostics = {}
    for row in cells.itertuples(index=False):
        geometry = row.context_geometry
        west, south, east, north = transform_bounds(
            SPATIAL.analysis_crs, "EPSG:4326", *geometry.bounds, densify_pts=21
        )
        relevant = [
            record
            for tile_id, record in COP_DEM_GLO30_TILES.items()
            if not (
                _tile_bounds(tile_id)[2] <= west
                or _tile_bounds(tile_id)[0] >= east
                or _tile_bounds(tile_id)[3] <= south
                or _tile_bounds(tile_id)[1] >= north
            )
        ]
        if not relevant:
            raise ValueError(f"No registered DEM tile covers {row.cell_id}")
        with ExitStack() as stack:
            sources = [stack.enter_context(rasterio.open(ROOT / record.raw_path)) for record in relevant]
            mosaic, source_transform = merge(
                sources,
                bounds=(west, south, east, north),
                nodata=np.nan,
                dtype="float32",
            )
            source_bounds = array_bounds(mosaic.shape[1], mosaic.shape[2], source_transform)
            target_transform, target_width, target_height = calculate_default_transform(
                "EPSG:4326",
                SPATIAL.analysis_crs,
                mosaic.shape[2],
                mosaic.shape[1],
                *source_bounds,
                resolution=30.0,
            )
            elevation = np.full((target_height, target_width), np.nan, dtype="float32")
            reproject(
                mosaic[0],
                elevation,
                src_transform=source_transform,
                src_crs="EPSG:4326",
                src_nodata=np.nan,
                dst_transform=target_transform,
                dst_crs=SPATIAL.analysis_crs,
                dst_nodata=np.nan,
                resampling=Resampling.nearest,
            )
        land_mask = geometry_mask(
            [mapping(geometry)],
            out_shape=elevation.shape,
            transform=target_transform,
            invert=True,
        )
        elevation[~land_mask] = np.nan
        with np.errstate(invalid="ignore"):
            gradient_y, gradient_x = np.gradient(elevation, 30.0, 30.0)
            slope = np.degrees(np.arctan(np.hypot(gradient_x, gradient_y)))
        finite = np.isfinite(slope) & land_mask
        if not finite.any():
            raise ValueError(f"No finite metric slope pixels for {row.cell_id}")
        values[row.cell_id] = float(slope[finite].mean())
        diagnostics[row.cell_id] = {
            "dem_tiles": [record.tile_id for record in relevant],
            "metric_pixel_count": int(finite.sum()),
            "metric_resolution_metres": 30.0,
        }
    return pd.Series(values, name="mean_slope_2km"), diagnostics


def derive_representative_pilot() -> tuple[gpd.GeoDataFrame, dict[str, object]]:
    """Derive all canonical fields once, without writing output files."""
    cells, _ = _read_sample_cells()
    slope, slope_diagnostics = derive_mean_slope_2km(cells)
    icnf_by_year, repair_logs = derive_icnf_features(cells, PILOT_YEARS)
    clc_by_reference = {}
    clc_candidates = {}
    for reference_year in sorted({CLC.reference_year(year) for year in PILOT_YEARS}):
        clc_by_reference[reference_year], clc_candidates[reference_year] = derive_clc_shares(cells, reference_year)
    climate_by_year = {year: derive_era5_context(year, cells) for year in PILOT_YEARS}

    rows = []
    geometries = []
    for predictor_year in PILOT_YEARS:
        years = source_years(predictor_year)
        reference_year = int(years["land_cover_reference_year"])
        release = _CLC_RAW_BY_REFERENCE_YEAR[reference_year]
        for cell in cells.itertuples(index=False):
            cell_id = cell.cell_id
            history = years["history_years"]
            row = {
                "cell_year_id": f"{cell_id}_{predictor_year}",
                "cell_id": cell_id,
                "observation_year": predictor_year,
                "outcome_year": int(years["outcome_year"]),
                "historical_fire_start_year": history[0],
                "historical_fire_end_year": history[-1],
                "climate_reference_year": predictor_year,
                "land_cover_reference_year": reference_year,
                "land_cover_release_id": release.release_id,
                "land_cover_release_date": release.release_date,
                "terrain_release_id": COP_DEM_GLO30.release_id,
                "built_up_share": float(clc_by_reference[reference_year].loc[cell_id, "built_up_share"]),
                "forest_shrub_share_2km": float(clc_by_reference[reference_year].loc[cell_id, "forest_shrub_share_2km"]),
                "mean_slope_2km": float(slope.loc[cell_id]),
                "fire_years_previous_10y_2km": int(icnf_by_year[predictor_year].loc[cell_id, "fire_years_previous_10y_2km"]),
                "warm_season_mean_2m_temperature_c": float(climate_by_year[predictor_year].loc[cell_id, "warm_season_mean_2m_temperature_c"]),
                "warm_season_total_precipitation_mm": float(climate_by_year[predictor_year].loc[cell_id, "warm_season_total_precipitation_mm"]),
                "warm_season_mean_soil_water_layer1": float(climate_by_year[predictor_year].loc[cell_id, "warm_season_mean_soil_water_layer1"]),
                TARGET_COLUMN: float(icnf_by_year[predictor_year].loc[cell_id, TARGET_COLUMN]),
            }
            rows.append(row)
            geometries.append(cell.geometry)
    table = pd.DataFrame(rows, columns=TABLE_COLUMNS)
    integer_types = {
        "observation_year": "int16",
        "outcome_year": "int16",
        "historical_fire_start_year": "int16",
        "historical_fire_end_year": "int16",
        "climate_reference_year": "int16",
        "land_cover_reference_year": "int16",
        "fire_years_previous_10y_2km": "int8",
    }
    table = table.astype(integer_types)
    pilot = gpd.GeoDataFrame(table, geometry=geometries, crs=SPATIAL.analysis_crs)
    validation = validate_feature_table(
        table,
        expected_years=PILOT_YEARS,
        expected_cell_ids=PILOT_CELL_IDS,
    )
    validation.update({
        "crs": str(pilot.crs),
        "sample_reasons": PILOT_CELL_REASONS,
        "clc_candidate_counts": clc_candidates,
        "slope_diagnostics": slope_diagnostics,
        "icnf_geometry_repair": repair_logs,
        "source_year_alignment": {
            year: source_years(year) for year in PILOT_YEARS
        },
    })
    return pilot, validation


def _summary(table: pd.DataFrame) -> dict[str, dict[str, float | int | None]]:
    result = {}
    for column in (*PREDICTOR_COLUMNS, TARGET_COLUMN):
        values = table[column]
        result[column] = {
            "minimum": None if values.dropna().empty else float(values.min()),
            "maximum": None if values.dropna().empty else float(values.max()),
            "mean": None if values.dropna().empty else float(values.mean()),
            "missing": int(values.isna().sum()),
            "zero": int(values.eq(0).sum()),
        }
    return result


def run_representative_pilot() -> dict[str, object]:
    """Run twice for determinism, validate, and publish only the controlled sample."""
    first, validation = derive_representative_pilot()
    second, second_validation = derive_representative_pilot()
    pd.testing.assert_frame_equal(
        first.drop(columns="geometry").sort_values(["cell_id", "observation_year"]).reset_index(drop=True),
        second.drop(columns="geometry").sort_values(["cell_id", "observation_year"]).reset_index(drop=True),
        check_exact=True,
    )
    if validation["row_count"] != second_validation["row_count"]:
        raise ValueError("Repeated pilot run changed row count")
    validation["deterministic_repeated_run"] = True
    validation["statistics"] = _summary(first)
    validation["created_utc"] = datetime.now(timezone.utc).isoformat()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    attributes = first.drop(columns="geometry")
    attributes.to_parquet(OUTPUT_PARQUET, index=False)
    pyogrio.write_dataframe(first, OUTPUT_GPKG, layer="representative_feature_pilot", driver="GPKG")
    reopened = pyogrio.read_dataframe(OUTPUT_GPKG)
    reopened_validation = validate_feature_table(
        reopened.drop(columns="geometry"),
        expected_years=PILOT_YEARS,
        expected_cell_ids=PILOT_CELL_IDS,
    )
    if str(reopened.crs) != SPATIAL.analysis_crs:
        raise ValueError("Published pilot GeoPackage lost EPSG:3763")
    validation["reopened_output_validation"] = reopened_validation

    contract_rows = [
        f"| `{name}` | {contract.dtype} | {contract.unit} | {contract.minimum} to {contract.maximum} | {contract.missing_rule} | {contract.source_year_rule} |"
        for name, contract in FIELD_CONTRACTS.items()
    ]
    REPORT_PATH.write_text(
        "# Representative canonical feature-derivation pilot\n\n"
        "This is a controlled implementation/data-contract sample, not the national panel and not a model output. "
        "It uses the existing canonical grid without rebuilding it.\n\n"
        "## Feature contract\n\n"
        "Uniqueness key: `cell_id` x `observation_year`. Geometry remains EPSG:3763 in the GeoPackage and is separate from the analytical Parquet table.\n\n"
        "| Field | Type | Unit | Allowed range | Missing rule | Source-year rule |\n"
        "|---|---|---|---|---|---|\n" + "\n".join(contract_rows) + "\n\n"
        "## Validation\n\n```json\n" + json.dumps(validation, indent=2, default=str) + "\n```\n",
        encoding="utf-8",
    )
    return validation
