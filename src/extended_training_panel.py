"""Bounded backward extension of the train/validation panel to T=2010-2021.

The validated canonical panel remains immutable.  This module derives only the
new T=2010-2014 rows, reuses validated static components, and copies canonical
T=2015-2021 Parquet row groups without opening final-test row groups.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Callable
import warnings

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import shapely

from src import national_panel as canonical
from src.config import CLC, EXTENDED_TRAINING, EXTENDED_TRAINING_CLC, SPATIAL
from src.feature_contract import PREDICTOR_COLUMNS, TABLE_COLUMNS, TARGET_COLUMN, source_years, validate_feature_table
from src.representative_feature_pilot import ICNF_ROOT, _icnf_vsi_path, _read_grib_variable, jjas_total_precipitation_mm
from src.source_registry import CLC_2006_V2020_20U1, COP_DEM_GLO30


ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / "data/interim/extended_training_panel_2010_2021"
EARLY_ICNF_REPAIRED_DIR = BUILD_ROOT / "icnf_repaired_2000_2004"
EARLY_ICNF_BATCH_DIR = BUILD_ROOT / "icnf_components_2000_2004"
EARLY_ERA_BATCH_DIR = BUILD_ROOT / "era5_2010_2014"
EARLY_PANEL_BATCH_DIR = BUILD_ROOT / "panel_batches_2010_2014"
PANEL_PATH = ROOT / "data/processed/extended_train_validation_panel_2010_2021.parquet"
VALIDATION_PATH = ROOT / "data/processed/extended_train_validation_panel_2010_2021_validation.json"
REPORT_PATH = ROOT / "reports/validation/extended_train_validation_panel_2010_2021.md"

NEW_OBSERVATION_YEARS = tuple(range(2010, 2015))
OBSERVATION_YEARS = tuple(range(EXTENDED_TRAINING.predictor_start_year, EXTENDED_TRAINING.predictor_end_year + 1))
EARLY_ICNF_YEARS = tuple(range(2000, 2005))
CANONICAL_REUSED_YEARS = tuple(range(2015, 2022))


def extended_source_years(predictor_year: int) -> dict[str, int | tuple[int, ...]]:
    """Resolve source years under the separately governed backward extension."""
    return source_years(
        predictor_year,
        temporal_design=EXTENDED_TRAINING,
        clc_governance=EXTENDED_TRAINING_CLC,
    )


def _atomic_json(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary output requires inspection: {temporary}")
    temporary.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    os.replace(temporary, path)


def _manifest_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".json")


def _publish_parquet(
    frame: pd.DataFrame,
    path: Path,
    *,
    component: str,
    batch_id: str,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    existing = canonical._validate_existing_batch(path, len(frame))
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
        "sha256": canonical._sha256(temporary),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        **(metadata or {}),
    }
    os.replace(temporary, path)
    _atomic_json(manifest, _manifest_path(path))
    return manifest | {"status": "created"}


def _early_repaired_path(year: int) -> Path:
    return EARLY_ICNF_REPAIRED_DIR / f"icnf_{year}_repaired.gpkg"


def _early_icnf_batch_path(batch_id: str) -> Path:
    return EARLY_ICNF_BATCH_DIR / f"icnf_early_{batch_id}.parquet"


def _early_era_batch_path(batch_id: str) -> Path:
    return EARLY_ERA_BATCH_DIR / f"era5_early_{batch_id}.parquet"


def _early_panel_batch_path(batch_id: str) -> Path:
    return EARLY_PANEL_BATCH_DIR / f"panel_early_{batch_id}.parquet"


def _grid_catalog() -> dict[str, object]:
    """Reuse the immutable, validated canonical grid catalog."""
    return canonical.load_grid_catalog()


def prepare_early_icnf_years(progress: Callable[[str], None] = print) -> dict[str, object]:
    """Repair only 2000-2004 derived geometries; raw ZIP remains untouched."""
    combined = None
    results: dict[int, dict[str, object]] = {}
    for year in EARLY_ICNF_YEARS:
        path = _early_repaired_path(year)
        layer = f"icnf_{year}_repaired"
        if path.exists():
            manifest = _manifest_path(path)
            if not manifest.exists():
                raise FileExistsError(f"Incomplete early ICNF output: {path}")
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            if canonical._sha256(path) != payload["sha256"]:
                raise ValueError(f"Early repaired ICNF checksum changed: {path}")
            results[year] = payload | {"status": "reused"}
            progress(f"Early ICNF {year}: reused {payload['row_count']} features")
            continue
        if combined is None:
            combined = pyogrio.read_dataframe(
                _icnf_vsi_path(ICNF_ROOT / "ardida_2000_2008.zip"), columns=["Ano"]
            )
        source = combined.loc[combined.Ano.astype(int) == year].copy()
        repaired, repair_log = canonical._repair_icnf_frame(source, year)
        results[year] = canonical._publish_gpkg(
            repaired,
            path,
            layer=layer,
            metadata={
                "year": year,
                "raw_archive": "data/raw/wildfire/icnf_burned_areas/ardida_2000_2008.zip",
                "raw_year_filter": year,
                "repair_log": repair_log,
            },
        )
        progress(
            f"Early ICNF {year}: {len(source)} input, {repair_log['repaired_count']} repaired, "
            f"{repair_log['rejected_count']} rejected"
        )
    return {"years": results, "status": "complete"}


def derive_early_icnf_batch(batch_id: str) -> tuple[pd.DataFrame, dict[str, object]]:
    grid, geometries = canonical.load_grid_batch(batch_id)
    land = geometries["land_geometry"]
    contexts = geometries["context_geometry"]
    bbox = tuple(float(value) for value in shapely.bounds(shapely.union_all(contexts)))
    output: dict[str, object] = {"cell_id": grid.cell_id.to_numpy()}
    candidate_counts: dict[int, int] = {}
    for year in EARLY_ICNF_YEARS:
        path = _early_repaired_path(year)
        candidates = pyogrio.read_dataframe(path, layer=f"icnf_{year}_repaired", columns=[], bbox=bbox)
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


def build_early_icnf_batches(progress: Callable[[str], None] = print) -> dict[str, object]:
    catalog = _grid_catalog()
    created = reused = 0
    for number, batch in enumerate(catalog["batches"], start=1):
        batch_id = batch["batch_id"]
        path = _early_icnf_batch_path(batch_id)
        existing = canonical._validate_existing_batch(path, batch["row_count"])
        if existing:
            reused += 1
            continue
        try:
            frame, metadata = derive_early_icnf_batch(batch_id)
            _publish_parquet(frame, path, component="icnf_early", batch_id=batch_id, metadata=metadata)
        except Exception as error:
            raise canonical.BatchError(f"extended-icnf/{batch_id} failed: {error}") from error
        created += 1
        progress(f"Extended ICNF {batch_id}: {len(frame)} cells ({number}/{catalog['batch_count']})")
    return {"created": created, "reused": reused, "batch_count": catalog["batch_count"]}


def load_early_era5_grids() -> dict[int, dict[str, object]]:
    """Load the five newly validated annual 0.1-degree grids once per build."""
    result: dict[int, dict[str, object]] = {}
    for year in NEW_OBSERVATION_YEARS:
        path = ROOT / f"data/raw/climate/era5_land/era5_land_monthly_jjas_{year}_mainland_portugal.grib"
        latitude, longitude, temperature, months = _read_grib_variable(path, "2t")
        soil_lat, soil_lon, soil_water, soil_months = _read_grib_variable(path, "swvl1")
        precip_lat, precip_lon, precipitation, precip_months = _read_grib_variable(path, "tp")
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
            result[year] = {
                "latitude": latitude,
                "longitude": longitude,
                "warm_season_mean_2m_temperature_c": np.nanmean(temperature, axis=0) - 273.15,
                "warm_season_total_precipitation_mm": jjas_total_precipitation_mm(precipitation, months),
                "warm_season_mean_soil_water_layer1": np.nanmean(soil_water, axis=0),
                "source_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            }
    return result


def derive_early_era_batch(
    batch_id: str,
    grids: dict[int, dict[str, object]],
    fallback_mapping: pd.DataFrame,
) -> pd.DataFrame:
    grid = pd.read_parquet(canonical._grid_batch_path(batch_id))
    rows = []
    latitude_points = grid.centroid_latitude.to_numpy()
    longitude_points = grid.centroid_longitude.to_numpy()
    for year in NEW_OBSERVATION_YEARS:
        source = grids[year]
        lat_index = np.abs(source["latitude"][:, None] - latitude_points).argmin(axis=0)
        lon_index = np.abs(source["longitude"][:, None] - longitude_points).argmin(axis=0)
        values = {feature: np.asarray(source[feature][lat_index, lon_index], dtype="float64") for feature in PREDICTOR_COLUMNS[-3:]}
        mask = np.isnan(values["warm_season_mean_2m_temperature_c"])
        if not all(np.array_equal(np.isnan(value), mask) for value in values.values()):
            raise ValueError(f"ERA5 water mask differs across fields for {year}/{batch_id}")
        for position in np.flatnonzero(mask):
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


def build_early_era_batches(progress: Callable[[str], None] = print) -> dict[str, object]:
    catalog = _grid_catalog()
    grids = load_early_era5_grids()
    fallback = canonical._load_era5_fallback_mapping()
    created = reused = 0
    for number, batch in enumerate(catalog["batches"], start=1):
        batch_id = batch["batch_id"]
        path = _early_era_batch_path(batch_id)
        expected_rows = batch["row_count"] * len(NEW_OBSERVATION_YEARS)
        existing = canonical._validate_existing_batch(path, expected_rows)
        if existing:
            reused += 1
            continue
        try:
            frame = derive_early_era_batch(batch_id, grids, fallback)
            _publish_parquet(
                frame, path, component="era5_early", batch_id=batch_id,
                metadata={
                    "source_paths_by_year": {year: grids[year]["source_path"] for year in NEW_OBSERVATION_YEARS},
                    "assignment": "containing_valid_cell_else_accepted_nearest_valid_land_cell_no_interpolation",
                },
            )
        except Exception as error:
            raise canonical.BatchError(f"extended-era5/{batch_id} failed: {error}") from error
        created += 1
        progress(f"Extended ERA5 {batch_id}: {len(frame)} rows ({number}/{catalog['batch_count']})")
    return {"created": created, "reused": reused, "batch_count": catalog["batch_count"]}


def derive_early_panel_batch(batch_id: str) -> pd.DataFrame:
    grid = pd.read_parquet(canonical._grid_batch_path(batch_id), columns=["cell_id"])
    cell_ids = grid.cell_id.to_numpy()
    slope = pd.read_parquet(canonical._component_batch_path(canonical.SLOPE_BATCH_DIR, "slope", batch_id)).set_index("cell_id")
    clc = pd.read_parquet(
        canonical._component_batch_path(canonical.CLC_BATCH_DIR / "2006", "clc_2006", batch_id)
    ).set_index("cell_id")
    era = pd.read_parquet(_early_era_batch_path(batch_id)).set_index(["cell_id", "observation_year"])
    early_icnf = pd.read_parquet(_early_icnf_batch_path(batch_id)).set_index("cell_id")
    canonical_icnf = pd.read_parquet(
        canonical._component_batch_path(canonical.ICNF_BATCH_DIR, "icnf", batch_id)
    ).set_index("cell_id")
    icnf = pd.concat([early_icnf, canonical_icnf], axis=1)
    if icnf.columns.duplicated().any():
        raise ValueError(f"ICNF component year collision in {batch_id}")
    rows = []
    for year in NEW_OBSERVATION_YEARS:
        years = extended_source_years(year)
        history = years["history_years"]
        historical_count = icnf.loc[cell_ids, [f"context_{item}" for item in history]].sum(axis=1).astype("int8")
        climate = era.loc[(cell_ids, year), list(PREDICTOR_COLUMNS[-3:])]
        rows.append(pd.DataFrame({
            "cell_year_id": cell_ids + np.full(len(cell_ids), f"_{year}", dtype=object),
            "cell_id": cell_ids,
            "observation_year": np.full(len(cell_ids), year, dtype="int16"),
            "outcome_year": np.full(len(cell_ids), years["outcome_year"], dtype="int16"),
            "historical_fire_start_year": np.full(len(cell_ids), history[0], dtype="int16"),
            "historical_fire_end_year": np.full(len(cell_ids), history[-1], dtype="int16"),
            "climate_reference_year": np.full(len(cell_ids), year, dtype="int16"),
            "land_cover_reference_year": np.full(len(cell_ids), 2006, dtype="int16"),
            "land_cover_release_id": CLC_2006_V2020_20U1.release_id,
            "land_cover_release_date": CLC_2006_V2020_20U1.release_date,
            "terrain_release_id": COP_DEM_GLO30.release_id,
            "built_up_share": clc.loc[cell_ids, "built_up_share"].to_numpy(),
            "forest_shrub_share_2km": clc.loc[cell_ids, "forest_shrub_share_2km"].to_numpy(),
            "mean_slope_2km": slope.loc[cell_ids, "mean_slope_2km"].to_numpy(),
            "fire_years_previous_10y_2km": historical_count.to_numpy(),
            "warm_season_mean_2m_temperature_c": climate["warm_season_mean_2m_temperature_c"].to_numpy(),
            "warm_season_total_precipitation_mm": climate["warm_season_total_precipitation_mm"].to_numpy(),
            "warm_season_mean_soil_water_layer1": climate["warm_season_mean_soil_water_layer1"].to_numpy(),
            TARGET_COLUMN: icnf.loc[cell_ids, f"share_{years['outcome_year']}"] .to_numpy(),
        }, columns=TABLE_COLUMNS))
    frame = pd.concat(rows, ignore_index=True).sort_values(["observation_year", "cell_id"], kind="mergesort").reset_index(drop=True)
    validate_feature_table(
        frame,
        expected_years=NEW_OBSERVATION_YEARS,
        expected_cell_ids=tuple(cell_ids),
        source_year_resolver=extended_source_years,
    )
    return frame


def build_early_panel_batches(progress: Callable[[str], None] = print) -> dict[str, object]:
    catalog = _grid_catalog()
    created = reused = 0
    for number, batch in enumerate(catalog["batches"], start=1):
        batch_id = batch["batch_id"]
        path = _early_panel_batch_path(batch_id)
        expected_rows = batch["row_count"] * len(NEW_OBSERVATION_YEARS)
        existing = canonical._validate_existing_batch(path, expected_rows)
        if existing:
            reused += 1
            continue
        try:
            frame = derive_early_panel_batch(batch_id)
            _publish_parquet(
                frame, path, component="panel_early", batch_id=batch_id,
                metadata={"observation_years": NEW_OBSERVATION_YEARS},
            )
        except Exception as error:
            raise canonical.BatchError(f"extended-panel/{batch_id} failed: {error}") from error
        created += 1
        progress(f"Extended panel {batch_id}: {len(frame)} rows ({number}/{catalog['batch_count']})")
    return {"created": created, "reused": reused, "batch_count": catalog["batch_count"]}


def _canonical_row_group_audit() -> dict[str, object]:
    """Read metadata for all row groups but mark final-test data groups unopened."""
    parquet = pq.ParquetFile(canonical.NATIONAL_PANEL_PATH)
    field_index = parquet.schema_arrow.get_field_index("observation_year")
    groups = []
    for group_index in range(parquet.num_row_groups):
        statistics = parquet.metadata.row_group(group_index).column(field_index).statistics
        if statistics is None or statistics.min != statistics.max:
            raise ValueError(f"Canonical row group {group_index} lacks single-year statistics")
        year = int(statistics.min)
        groups.append({
            "row_group": group_index,
            "observation_year": year,
            "rows": parquet.metadata.row_group(group_index).num_rows,
            "read": year in CANONICAL_REUSED_YEARS,
        })
    final_read = [item for item in groups if item["observation_year"] >= 2022 and item["read"]]
    if final_read:
        raise ValueError("Extended builder would access final-test data")
    return {
        "groups": groups,
        "final_test_rows_read": 0,
        "unopened_final_test_row_groups": [item["row_group"] for item in groups if item["observation_year"] >= 2022],
    }


def _read_canonical_year(year: int) -> pd.DataFrame:
    if year not in CANONICAL_REUSED_YEARS:
        raise ValueError(f"Canonical reuse is forbidden for T={year}")
    audit = _canonical_row_group_audit()
    group = next(item for item in audit["groups"] if item["observation_year"] == year)
    return pq.ParquetFile(canonical.NATIONAL_PANEL_PATH).read_row_group(group["row_group"]).to_pandas()[list(TABLE_COLUMNS)]


def assemble_extended_panel(progress: Callable[[str], None] = print) -> dict[str, object]:
    catalog = _grid_catalog()
    expected_rows = catalog["cell_count"] * len(OBSERVATION_YEARS)
    if PANEL_PATH.exists():
        existing = _manifest_path(PANEL_PATH)
        if not existing.exists():
            raise FileExistsError(f"Extended panel exists without manifest: {PANEL_PATH}")
        manifest = json.loads(existing.read_text(encoding="utf-8"))
        if canonical._sha256(PANEL_PATH) != manifest["sha256"]:
            raise ValueError("Extended panel checksum changed")
        if pq.ParquetFile(PANEL_PATH).metadata.num_rows != expected_rows:
            raise ValueError("Extended panel row count changed")
        return manifest | {"status": "reused"}
    temporary = PANEL_PATH.with_suffix(".parquet.tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary extended panel requires inspection: {temporary}")
    PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    canonical_access = _canonical_row_group_audit()
    try:
        for year in OBSERVATION_YEARS:
            if year in NEW_OBSERVATION_YEARS:
                pieces = [
                    pd.read_parquet(_early_panel_batch_path(batch["batch_id"]), filters=[("observation_year", "==", year)])
                    for batch in catalog["batches"]
                ]
                frame = pd.concat(pieces, ignore_index=True).sort_values("cell_id", kind="mergesort")
            else:
                frame = _read_canonical_year(year).sort_values("cell_id", kind="mergesort")
            if len(frame) != catalog["cell_count"] or not frame.cell_id.is_unique:
                raise ValueError(f"Extended assembly lost or duplicated T={year} cells")
            table = pa.Table.from_pandas(frame[list(TABLE_COLUMNS)], preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(temporary, table.schema, compression="zstd")
            writer.write_table(table)
            progress(f"Assembled extended T={year}: {len(frame)} rows")
    except Exception:
        if writer is not None:
            writer.close()
        raise
    if writer is None:
        raise ValueError("Extended assembly wrote no rows")
    writer.close()
    if pq.ParquetFile(temporary).metadata.num_rows != expected_rows:
        raise ValueError("Extended temporary panel has unexpected row count")
    manifest = {
        "component": "extended_train_validation_panel",
        "row_count": expected_rows,
        "cell_count": catalog["cell_count"],
        "observation_years": OBSERVATION_YEARS,
        "newly_derived_years": NEW_OBSERVATION_YEARS,
        "canonical_reused_years": CANONICAL_REUSED_YEARS,
        "canonical_row_group_access": canonical_access,
        "ordering": "observation_year ascending, then cell_id ascending",
        "sha256": canonical._sha256(temporary),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    os.replace(temporary, PANEL_PATH)
    _atomic_json(manifest, _manifest_path(PANEL_PATH))
    return manifest | {"status": "created"}


def validate_extended_panel() -> dict[str, object]:
    started = time.perf_counter()
    catalog = _grid_catalog()
    parquet = pq.ParquetFile(PANEL_PATH)
    expected_rows = catalog["cell_count"] * len(OBSERVATION_YEARS)
    if parquet.metadata.num_rows != expected_rows or parquet.num_row_groups != len(OBSERVATION_YEARS):
        raise ValueError("Extended panel row or row-group count is incorrect")
    expected_ids = tuple(sorted(
        cell_id
        for batch in catalog["batches"]
        for cell_id in pd.read_parquet(ROOT / batch["path"], columns=["cell_id"]).cell_id
    ))
    year_metrics: dict[int, dict[str, object]] = {}
    canonical_regression: dict[int, dict[str, object]] = {}
    for row_group, year in enumerate(OBSERVATION_YEARS):
        frame = parquet.read_row_group(row_group).to_pandas()[list(TABLE_COLUMNS)]
        validate_feature_table(
            frame,
            expected_years=(year,),
            expected_cell_ids=expected_ids,
            source_year_resolver=extended_source_years,
        )
        if tuple(frame.cell_id) != expected_ids:
            raise ValueError(f"Extended panel ordering differs in T={year}")
        climate_missing = int(frame[list(PREDICTOR_COLUMNS[-3:])].isna().sum().sum())
        if climate_missing:
            raise ValueError(f"Climate missingness remains in extended T={year}")
        year_metrics[year] = canonical._year_metrics(frame, year)
        if year in CANONICAL_REUSED_YEARS:
            original = _read_canonical_year(year).sort_values("cell_id", kind="mergesort").reset_index(drop=True)
            pd.testing.assert_frame_equal(frame.reset_index(drop=True), original, check_exact=True, check_dtype=True)
            canonical_regression[year] = {"rows": len(frame), "identical": True}
    early_logs = {
        year: json.loads(_manifest_path(_early_repaired_path(year)).read_text(encoding="utf-8"))["repair_log"]
        for year in EARLY_ICNF_YEARS
    }
    metrics = {
        "validated_utc": datetime.now(timezone.utc).isoformat(),
        "panel_path": str(PANEL_PATH.relative_to(ROOT)).replace("\\", "/"),
        "panel_sha256": canonical._sha256(PANEL_PATH),
        "grid_cell_count": catalog["cell_count"],
        "observation_years": OBSERVATION_YEARS,
        "expected_row_count": expected_rows,
        "actual_row_count": parquet.metadata.num_rows,
        "duplicate_analytical_key_count": 0,
        "missing_predictor_or_target_values": 0,
        "newly_derived_years": NEW_OBSERVATION_YEARS,
        "canonical_reused_years": CANONICAL_REUSED_YEARS,
        "canonical_regression": canonical_regression,
        "final_test_access": _canonical_row_group_audit(),
        "temporal_contract": {
            "outcome_year_is_t_plus_1": True,
            "historical_window_is_t_minus_10_through_t_minus_1": True,
            "clc_assignment": {year: EXTENDED_TRAINING_CLC.reference_year(year) for year in OBSERVATION_YEARS},
            "outcome_information_used_by_predictors": False,
        },
        "year_metrics": year_metrics,
        "early_icnf_geometry_repair": early_logs,
        "annual_union_prevents_double_counting": True,
        "validation_runtime_seconds": round(time.perf_counter() - started, 3),
        "readiness": "Extended train/validation panel validated; refit may use T=2010-2019 only.",
    }
    _atomic_json(metrics, VALIDATION_PATH)
    return metrics


def write_validation_report(metrics: dict[str, object]) -> None:
    rows = []
    for year in OBSERVATION_YEARS:
        target = metrics["year_metrics"][year]["target"]
        rows.append(
            f"| {year} | {year + 1} | {target['positive_row_count']:,} | {target['zero_proportion']:.6f} | {target['mean']:.8f} | {target['maximum']:.6f} |"
        )
    REPORT_PATH.write_text(
        "# Extended T=2010-2021 train/validation panel validation\n\n"
        "**Extended train/validation panel validated; refit may use T=2010-2019 only.**\n\n"
        "The canonical T=2022-2024 final-test row groups were inspected only as Parquet metadata and were never read. "
        "T=2010-2014 were newly derived in bounded spatial tiles; T=2015-2021 were copied exactly from the validated canonical panel.\n\n"
        f"- Grid cells: {metrics['grid_cell_count']:,}.\n"
        f"- Rows: {metrics['actual_row_count']:,}.\n"
        f"- Newly derived years: {list(metrics['newly_derived_years'])}.\n"
        f"- Canonical regression rows: {sum(item['rows'] for item in metrics['canonical_regression'].values()):,}, all exact.\n"
        f"- Final-test rows read: {metrics['final_test_access']['final_test_rows_read']}.\n"
        "- All three climate fields are complete after the accepted static nearest-valid-land fallback; no value was set to zero.\n"
        "- ICNF uses the established derived-only `make_valid` policy and annual geometry unions before share intersection.\n\n"
        "## Target by predictor year\n\n"
        "| T | Outcome | Positive rows | Zero proportion | Mean burned share | Maximum |\n"
        "|---:|---:|---:|---:|---:|---:|\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )


def run_extended_panel_build(progress: Callable[[str], None] = print) -> dict[str, object]:
    """Execute restartable extension stages without touching canonical outputs."""
    started = time.perf_counter()
    result = {
        "early_icnf_repair": prepare_early_icnf_years(progress),
        "early_icnf_components": build_early_icnf_batches(progress),
        "early_era5": build_early_era_batches(progress),
        "early_panel_batches": build_early_panel_batches(progress),
        "assembly": assemble_extended_panel(progress),
    }
    metrics = validate_extended_panel()
    write_validation_report(metrics)
    result["validation"] = metrics
    result["runtime_seconds"] = round(time.perf_counter() - started, 3)
    return result
