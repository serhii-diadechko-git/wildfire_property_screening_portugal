"""Diagnose and apply a deterministic nearest-valid ERA5-Land coastal fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pyproj import Transformer
import pyogrio
from scipy.spatial import cKDTree
import shapely

from src.feature_contract import CLIMATE_PREDICTOR_COLUMNS, PREDICTOR_COLUMNS
from src.national_panel import (
    BUILD_ROOT,
    NATIONAL_PANEL_PATH,
    OBSERVATION_YEARS,
    PANEL_BATCH_DIR,
    ROOT,
    TABLE_COLUMNS,
    _atomic_json,
    _component_batch_path,
    _manifest_path,
    _publish_parquet,
    _sha256,
    load_era5_grids,
    load_grid_catalog,
)
from src.reporting import write_json_if_changed, write_text_if_changed


CLIMATE_COLUMNS = CLIMATE_PREDICTOR_COLUMNS
MAPPING_PATH = BUILD_ROOT / "era5_coastal_fallback_mapping.parquet"
ANALYSIS_JSON_PATH = ROOT / "reports/validation/era5_coastal_fallback_analysis.json"
ANALYSIS_REPORT_PATH = ROOT / "reports/validation/era5_coastal_fallback_analysis.md"
QA_GPKG_PATH = ROOT / "data/processed/spatial_qa/era5_land_coastal_fallback_qa.gpkg"
QA_LAYER = "era5_coastal_fallback_qa"
ERA_FALLBACK_BATCH_DIR = BUILD_ROOT / "era5_coastal_fallback"
PANEL_FALLBACK_BATCH_DIR = BUILD_ROOT / "panel_batches_coastal_fallback"
PREVIOUS_EVIDENCE_DIR = BUILD_ROOT / "pre_coastal_fallback"
NINE_FEATURE_EVIDENCE_DIR = PREVIOUS_EVIDENCE_DIR / "nine_feature_contract"
SNAPSHOT_GPKG_PATH = ROOT / "data/processed/spatial_qa/national_panel_snapshot_2024.gpkg"
SNAPSHOT_LAYER = "national_panel_snapshot_2024"


def _grid_lookup() -> pd.DataFrame:
    pieces = []
    for batch in load_grid_catalog()["batches"]:
        pieces.append(pd.read_parquet(
            ROOT / batch["path"],
            columns=[
                "cell_id", "geometry_wkb", "land_area_m2",
                "centroid_longitude", "centroid_latitude",
            ],
        ))
    return pd.concat(pieces, ignore_index=True).sort_values("cell_id").reset_index(drop=True)


def _stable_valid_mask(grids: dict[int, dict[str, object]]) -> np.ndarray:
    masks = []
    latitude = longitude = None
    for year in OBSERVATION_YEARS:
        source = grids[year]
        if latitude is None:
            latitude = source["latitude"]
            longitude = source["longitude"]
        elif not (
            np.array_equal(latitude, source["latitude"])
            and np.array_equal(longitude, source["longitude"])
        ):
            raise ValueError(f"ERA5 coordinate grid changes in {year}")
        masks.append(np.logical_and.reduce([
            np.isfinite(np.asarray(source[column], dtype="float64"))
            for column in CLIMATE_COLUMNS
        ]))
    first = masks[0]
    if not all(np.array_equal(first, mask) for mask in masks[1:]):
        raise ValueError("ERA5-Land valid-land mask changes across observation years")
    return first


def _distance_summary(values: pd.Series) -> dict[str, float]:
    return {
        "minimum": float(values.min()),
        "median": float(values.median()),
        "mean": float(values.mean()),
        "p90": float(values.quantile(0.90)),
        "p95": float(values.quantile(0.95)),
        "p99": float(values.quantile(0.99)),
        "maximum": float(values.max()),
    }


def _distance_bands(values: pd.Series) -> dict[str, int]:
    bands = pd.cut(
        values,
        bins=[-np.inf, 10, 20, 30, 50, np.inf],
        labels=["under_10_km", "10_to_under_20_km", "20_to_under_30_km", "30_to_under_50_km", "50_km_or_more"],
        right=False,
    )
    return {str(key): int(value) for key, value in bands.value_counts(sort=False).items()}


def _local_consistency(
    mapping: pd.DataFrame,
    grids: dict[int, dict[str, object]],
    tree: cKDTree,
    valid_flat_indices: np.ndarray,
    cell_xy: np.ndarray,
) -> dict[str, object]:
    ordered = mapping.sort_values("distance_km")
    selected_positions = sorted(set(
        [0, len(ordered) // 4, len(ordered) // 2, 3 * len(ordered) // 4, len(ordered) - 1]
        + list(range(max(0, len(ordered) - 5), len(ordered)))
    ))
    sample = ordered.iloc[selected_positions].copy()
    sample_indices = sample.index.to_numpy()
    _, neighbors = tree.query(cell_xy[sample_indices], k=5)
    diagnostics = []
    maximum_absolute_difference = {column: 0.0 for column in CLIMATE_COLUMNS}
    for sample_row, neighbor_positions in zip(sample.itertuples(), np.atleast_2d(neighbors), strict=True):
        row_differences = {column: [] for column in CLIMATE_COLUMNS}
        fallback_flat = int(sample_row.fallback_flat_index)
        for year in OBSERVATION_YEARS:
            for column in CLIMATE_COLUMNS:
                flattened = np.asarray(grids[year][column], dtype="float64").ravel()
                selected = float(flattened[fallback_flat])
                local = flattened[valid_flat_indices[np.asarray(neighbor_positions, dtype=int)]]
                difference = abs(selected - float(np.median(local)))
                row_differences[column].append(difference)
                maximum_absolute_difference[column] = max(maximum_absolute_difference[column], difference)
        diagnostics.append({
            "cell_id": sample_row.cell_id,
            "cell_centroid_latitude": sample_row.cell_lat,
            "cell_centroid_longitude": sample_row.cell_lon,
            "distance_km": sample_row.distance_km,
            "fallback_latitude": sample_row.fallback_lat,
            "fallback_longitude": sample_row.fallback_lon,
            "maximum_absolute_difference_from_five_nearest_land_cell_median": {
                column: float(max(values)) for column, values in row_differences.items()
            },
        })
    return {
        "sample_cell_count": len(diagnostics),
        "years_compared": OBSERVATION_YEARS,
        "comparison": "fallback value versus median of five nearest valid ERA5-Land cells",
        "maximum_absolute_difference_across_sample": maximum_absolute_difference,
        "cells": diagnostics,
    }


def analyse_coastal_fallback() -> tuple[pd.DataFrame, dict[str, object]]:
    """Build the static mapping and distance/extent/consistency evidence only."""
    grids = load_era5_grids()
    valid_mask = _stable_valid_mask(grids)
    latitude = np.asarray(grids[OBSERVATION_YEARS[0]]["latitude"], dtype="float64")
    longitude = np.asarray(grids[OBSERVATION_YEARS[0]]["longitude"], dtype="float64")
    lon_mesh, lat_mesh = np.meshgrid(longitude, latitude)
    flat_valid = np.flatnonzero(valid_mask.ravel())

    transformer = Transformer.from_crs(4326, 3763, always_xy=True)
    valid_x, valid_y = transformer.transform(lon_mesh.ravel()[flat_valid], lat_mesh.ravel()[flat_valid])
    tree = cKDTree(np.column_stack([valid_x, valid_y]))

    grid = _grid_lookup()
    cell_x, cell_y = transformer.transform(
        grid.centroid_longitude.to_numpy(), grid.centroid_latitude.to_numpy()
    )
    cell_xy = np.column_stack([cell_x, cell_y])
    lat_index = np.abs(latitude[:, None] - grid.centroid_latitude.to_numpy()).argmin(axis=0)
    lon_index = np.abs(longitude[:, None] - grid.centroid_longitude.to_numpy()).argmin(axis=0)
    containing_valid = valid_mask[lat_index, lon_index]
    affected_positions = np.flatnonzero(~containing_valid)
    if len(affected_positions) != 1_506:
        raise ValueError(f"Expected 1,506 containing-cell mask cases, found {len(affected_positions)}")

    distances_m, nearest_positions = tree.query(cell_xy[affected_positions], k=1)
    fallback_flat = flat_valid[np.asarray(nearest_positions, dtype=int)]
    fallback_lat_index, fallback_lon_index = np.unravel_index(fallback_flat, valid_mask.shape)
    if not valid_mask[fallback_lat_index, fallback_lon_index].all():
        raise ValueError("Nearest fallback includes a non-land ERA5 cell")
    on_source_boundary = (
        (fallback_lat_index == 0) | (fallback_lat_index == len(latitude) - 1)
        | (fallback_lon_index == 0) | (fallback_lon_index == len(longitude) - 1)
    )
    affected = grid.iloc[affected_positions].copy().reset_index(drop=True)
    mapping = pd.DataFrame({
        "cell_id": affected.cell_id,
        "land_class": np.where(affected.land_area_m2.lt(999_999.999), "partial_land_coastal", "full_land_coastal"),
        "cell_lat": affected.centroid_latitude,
        "cell_lon": affected.centroid_longitude,
        "orig_era_lat": latitude[lat_index[affected_positions]],
        "orig_era_lon": longitude[lon_index[affected_positions]],
        "fallback_lat": latitude[fallback_lat_index],
        "fallback_lon": longitude[fallback_lon_index],
        "distance_km": distances_m / 1000.0,
        "fallback_flat_index": fallback_flat.astype("int32"),
        "source_on_request_boundary": on_source_boundary,
        "assignment_method": "nearest_valid_era5_land_cell",
    })
    mapping.index = affected_positions
    local_consistency = _local_consistency(mapping, grids, tree, flat_valid, cell_xy)
    mapping = mapping.reset_index(drop=True).sort_values("cell_id").reset_index(drop=True)

    top = mapping.nlargest(10, "distance_km")[
        ["cell_id", "land_class", "cell_lat", "cell_lon", "fallback_lat", "fallback_lon", "distance_km"]
    ].to_dict(orient="records")
    metrics = {
        "source_extent": {
            "north": float(latitude.max()), "west": float(longitude.min()),
            "south": float(latitude.min()), "east": float(longitude.max()),
            "shape": (len(latitude), len(longitude)),
            "valid_land_source_cell_count": int(valid_mask.sum()),
            "masked_source_cell_count": int((~valid_mask).sum()),
            "mask_invariant_across_2015_2024": True,
        },
        "affected_cell_count": len(mapping),
        "distance_km": _distance_summary(mapping.distance_km),
        "distance_bands": _distance_bands(mapping.distance_km),
        "selected_source_on_request_boundary_count": int(mapping.source_on_request_boundary.sum()),
        "all_selected_sources_valid_across_years_and_variables": True,
        "largest_distance_cases": top,
        "local_climate_consistency": local_consistency,
        "new_acquisition_required": bool(mapping.source_on_request_boundary.any()),
        "mapping_rule": (
            "Use the centroid-containing ERA5-Land cell when valid; otherwise assign the "
            "geographically nearest valid ERA5-Land land-cell centre in EPSG:3763."
        ),
    }
    return mapping, metrics


def publish_analysis(mapping: pd.DataFrame, metrics: dict[str, object]) -> None:
    MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_parquet(MAPPING_PATH.with_suffix(".parquet.tmp"), index=False)
    os.replace(MAPPING_PATH.with_suffix(".parquet.tmp"), MAPPING_PATH)
    write_json_if_changed(ANALYSIS_JSON_PATH, metrics)

    grid = _grid_lookup().set_index("cell_id").loc[mapping.cell_id]
    spatial = gpd.GeoDataFrame(
        mapping.drop(columns="fallback_flat_index").copy(),
        geometry=shapely.from_wkb(grid.geometry_wkb.to_numpy()),
        crs="EPSG:3763",
    )
    QA_GPKG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = QA_GPKG_PATH.with_name(QA_GPKG_PATH.stem + ".tmp.gpkg")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary QA GeoPackage: {temporary}")
    pyogrio.write_dataframe(spatial, temporary, layer=QA_LAYER, driver="GPKG")
    reopened = pyogrio.read_dataframe(temporary, layer=QA_LAYER)
    if len(reopened) != 1_506 or str(reopened.crs) != "EPSG:3763":
        raise ValueError("Published coastal QA GeoPackage failed row/CRS validation")
    os.replace(temporary, QA_GPKG_PATH)

    stats = metrics["distance_km"]
    band_rows = "\n".join(
        f"| {name.replace('_', ' ')} | {count:,} |" for name, count in metrics["distance_bands"].items()
    )
    top_rows = "\n".join(
        f"| `{row['cell_id']}` | {row['land_class']} | {row['cell_lat']:.5f} | {row['cell_lon']:.5f} | "
        f"{row['fallback_lat']:.2f} | {row['fallback_lon']:.2f} | {row['distance_km']:.3f} |"
        for row in metrics["largest_distance_cases"]
    )
    write_text_if_changed(
        ANALYSIS_REPORT_PATH,
        "# ERA5-Land coastal fallback analysis\n\n"
        "This is a spatial land-mask/grid-alignment diagnosis. It does not change raw GRIBs or interpolate/downscale climate data.\n\n"
        f"Affected canonical cells: {len(mapping):,}. ERA5 source grid: 55 x 37; valid land cells: "
        f"{metrics['source_extent']['valid_land_source_cell_count']:,}. The land mask is invariant across T=2015-2024.\n\n"
        "## Nearest valid land-cell distance\n\n"
        f"Minimum {stats['minimum']:.3f} km; median {stats['median']:.3f} km; mean {stats['mean']:.3f} km; "
        f"P90 {stats['p90']:.3f} km; P95 {stats['p95']:.3f} km; P99 {stats['p99']:.3f} km; maximum {stats['maximum']:.3f} km.\n\n"
        "| Distance band | Cells |\n|---|---:|\n" + band_rows + "\n\n"
        f"Selected fallback sources on the CDS request boundary: {metrics['selected_source_on_request_boundary_count']}. "
        f"Additional acquisition required: {metrics['new_acquisition_required']}.\n\n"
        "## Largest-distance cases\n\n"
        "| Cell | Land class | Cell lat | Cell lon | Source lat | Source lon | Distance km |\n"
        "|---|---|---:|---:|---:|---:|---:|\n" + top_rows + "\n\n"
        "Local climate comparisons are recorded in the machine-readable JSON.\n",
    )


def run_analysis() -> dict[str, object]:
    mapping, metrics = analyse_coastal_fallback()
    publish_analysis(mapping, metrics)
    return metrics


def _mapping_index() -> pd.DataFrame:
    if not MAPPING_PATH.exists():
        raise FileNotFoundError("Run the coastal fallback analysis before applying it")
    mapping = pd.read_parquet(MAPPING_PATH).set_index("cell_id")
    if len(mapping) != 1_506 or not mapping.index.is_unique:
        raise ValueError("Coastal fallback mapping contract failed")
    return mapping


def build_fallback_era_batches(progress=print) -> dict[str, int]:
    """Copy direct assignments exactly and fill only mapped water-mask cases."""
    from src.national_panel import ERA_BATCH_DIR

    mapping = _mapping_index()
    grids = load_era5_grids()
    catalog = load_grid_catalog()
    created = reused = 0
    for number, batch in enumerate(catalog["batches"], start=1):
        batch_id = batch["batch_id"]
        source_path = _component_batch_path(ERA_BATCH_DIR, "era5", batch_id)
        output_path = _component_batch_path(ERA_FALLBACK_BATCH_DIR, "era5", batch_id)
        source = pd.read_parquet(source_path)
        affected_ids = source.cell_id.drop_duplicates().loc[
            source.cell_id.drop_duplicates().isin(mapping.index)
        ]
        if len(affected_ids):
            for cell_id in affected_ids:
                fallback_flat = int(mapping.loc[cell_id, "fallback_flat_index"])
                cell_mask = source.cell_id.eq(cell_id)
                for year in OBSERVATION_YEARS:
                    row_mask = cell_mask & source.observation_year.eq(year)
                    for column in CLIMATE_COLUMNS:
                        value = float(np.asarray(grids[year][column]).ravel()[fallback_flat])
                        if not np.isfinite(value):
                            raise ValueError(f"Fallback source invalid for {cell_id}/{year}/{column}")
                        source.loc[row_mask, column] = value
        if source[list(CLIMATE_COLUMNS)].isna().any().any():
            raise ValueError(f"Fallback ERA batch remains missing: {batch_id}")
        result = _publish_parquet(
            source,
            output_path,
            component="era5_containing_or_nearest_valid_land",
            batch_id=batch_id,
            required_columns=("cell_id", "observation_year", *CLIMATE_COLUMNS),
            metadata={
                "direct_assignment": "containing_era5_land_cell_when_valid",
                "fallback_assignment": "nearest_valid_era5_land_cell_for_static_mapped_water_mask",
                "fallback_cell_count": len(affected_ids),
            },
        )
        if result["status"] == "created":
            created += 1
        else:
            reused += 1
        progress(f"ERA5 fallback {batch_id}: {len(affected_ids)} mapped cells ({number}/{catalog['batch_count']})")
    return {"created": created, "reused": reused, "batch_count": catalog["batch_count"]}


def build_fallback_panel_batches(progress=print) -> dict[str, int]:
    """Replace climate fields only; require all other analytical values to be exact."""
    catalog = load_grid_catalog()
    created = reused = 0
    non_climate = [column for column in TABLE_COLUMNS if column not in CLIMATE_COLUMNS]
    for number, batch in enumerate(catalog["batches"], start=1):
        batch_id = batch["batch_id"]
        old = pd.read_parquet(_component_batch_path(PANEL_BATCH_DIR, "panel", batch_id))
        climate = pd.read_parquet(
            _component_batch_path(ERA_FALLBACK_BATCH_DIR, "era5", batch_id)
        ).set_index(["cell_id", "observation_year"])
        updated = old.copy()
        keys = pd.MultiIndex.from_frame(updated[["cell_id", "observation_year"]])
        for column in CLIMATE_COLUMNS:
            updated[column] = climate.loc[keys, column].to_numpy()
        pd.testing.assert_frame_equal(old[non_climate], updated[non_climate], check_exact=True)
        if updated[list(CLIMATE_COLUMNS)].isna().any().any():
            raise ValueError(f"Updated panel batch remains climate-missing: {batch_id}")
        output_path = _component_batch_path(PANEL_FALLBACK_BATCH_DIR, "panel", batch_id)
        result = _publish_parquet(
            updated,
            output_path,
            component="panel_coastal_climate_resolved",
            batch_id=batch_id,
            required_columns=TABLE_COLUMNS,
            metadata={"non_climate_values_exactly_preserved": True},
        )
        if result["status"] == "created":
            created += 1
        else:
            reused += 1
        progress(f"Panel fallback {batch_id}: {len(updated)} rows ({number}/{catalog['batch_count']})")
    return {"created": created, "reused": reused, "batch_count": catalog["batch_count"]}


def _archive_previous_evidence() -> dict[str, str]:
    """Archive the current direct-assignment panel for this schema version.

    The earlier direct-assignment evidence remains untouched as historical
    validation evidence. The current contract needs its own snapshot because
    fallback validation compares every non-climate analytical value exactly.
    """
    NINE_FEATURE_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        NATIONAL_PANEL_PATH: NINE_FEATURE_EVIDENCE_DIR / "national_panel_containing_cell.parquet",
        _manifest_path(NATIONAL_PANEL_PATH): NINE_FEATURE_EVIDENCE_DIR / "national_panel_containing_cell.parquet.json",
        ROOT / "data/processed/national_panel_2015_2024_validation.json": NINE_FEATURE_EVIDENCE_DIR / "national_panel_containing_cell_validation.json",
        ROOT / "reports/validation/national_panel_2015_2024_validation.md": NINE_FEATURE_EVIDENCE_DIR / "national_panel_containing_cell_validation.md",
    }
    for source, destination in paths.items():
        if destination.exists():
            continue
        if not source.exists():
            raise FileNotFoundError(f"Previous validation evidence missing: {source}")
        shutil.copy2(source, destination)
    previous_manifest = json.loads(paths[_manifest_path(NATIONAL_PANEL_PATH)].read_text(encoding="utf-8"))
    if _sha256(paths[NATIONAL_PANEL_PATH]) != previous_manifest["sha256"]:
        raise ValueError("Archived containing-cell panel checksum differs")
    return {
        "panel": str(paths[NATIONAL_PANEL_PATH].relative_to(ROOT)).replace("\\", "/"),
        "panel_sha256": previous_manifest["sha256"],
        "validation_json": str(paths[ROOT / "data/processed/national_panel_2015_2024_validation.json"].relative_to(ROOT)).replace("\\", "/"),
        "validation_report": str(paths[ROOT / "reports/validation/national_panel_2015_2024_validation.md"].relative_to(ROOT)).replace("\\", "/"),
    }


def assemble_fallback_panel(progress=print) -> dict[str, object]:
    """Atomically replace the canonical Parquet after archiving prior evidence."""
    archive = _archive_previous_evidence()
    catalog = load_grid_catalog()
    temporary = NATIONAL_PANEL_PATH.with_name(NATIONAL_PANEL_PATH.stem + ".coastal-fallback.tmp.parquet")
    if temporary.exists():
        raise FileExistsError(f"Stale panel temporary output: {temporary}")
    writer = None
    try:
        for year in OBSERVATION_YEARS:
            pieces = [
                pd.read_parquet(
                    _component_batch_path(PANEL_FALLBACK_BATCH_DIR, "panel", batch["batch_id"]),
                    filters=[("observation_year", "==", year)],
                )
                for batch in catalog["batches"]
            ]
            frame = pd.concat(pieces, ignore_index=True).sort_values("cell_id", kind="mergesort")
            if len(frame) != catalog["cell_count"] or not frame.cell_id.is_unique:
                raise ValueError(f"Fallback assembly lost or duplicated T={year} cells")
            table = pa.Table.from_pandas(frame[list(TABLE_COLUMNS)], preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(temporary, table.schema, compression="zstd")
            writer.write_table(table)
            progress(f"Assembled fallback T={year}: {len(frame)} rows")
    finally:
        if writer is not None:
            writer.close()
    expected = catalog["cell_count"] * len(OBSERVATION_YEARS)
    if pq.ParquetFile(temporary).metadata.num_rows != expected:
        raise ValueError("Fallback panel has an unexpected row count")
    manifest = {
        "component": "national_panel_containing_or_nearest_valid_era5_land",
        "row_count": expected,
        "cell_count": catalog["cell_count"],
        "observation_years": OBSERVATION_YEARS,
        "ordering": "observation_year ascending, then cell_id ascending",
        "climate_assignment": "containing valid ERA5-Land cell; otherwise static nearest valid land cell",
        "previous_evidence": archive,
        "sha256": _sha256(temporary),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    os.replace(temporary, NATIONAL_PANEL_PATH)
    _atomic_json(manifest, _manifest_path(NATIONAL_PANEL_PATH))
    return manifest


def validate_fallback_panel() -> dict[str, object]:
    """Validate the canonical, single-pipeline coastal climate assignment.

    The national builder now applies the approved direct-or-nearest-valid rule
    while deriving ERA5 batches.  It no longer rewrites a separately built,
    separately built interim panel, so validation checks the one canonical panel directly.
    The older pre-fallback snapshot remains historical evidence only.
    """
    new_file = pq.ParquetFile(NATIONAL_PANEL_PATH)
    mapping_ids = set(_mapping_index().index)
    updated_rows = 0
    for group, year in enumerate(OBSERVATION_YEARS):
        new = new_file.read_row_group(group).to_pandas()[list(TABLE_COLUMNS)]
        if len(new) != 89_112 or not new.cell_id.is_unique:
            raise ValueError(f"Canonical fallback panel identity failed in T={year}")
        affected = new.cell_id.isin(mapping_ids)
        if int(affected.sum()) != 1_506:
            raise ValueError(f"Unexpected mapped count in T={year}")
        if new[list(CLIMATE_COLUMNS)].isna().any().any():
            raise ValueError(f"Fallback panel still has climate missingness in T={year}")
        updated_rows += int(affected.sum())
    return {
        "row_count": new_file.metadata.num_rows,
        "updated_climate_row_count": updated_rows,
        "climate_missing_count_after": 0,
        "canonical_climate_contract_validated": True,
        "assignment_pipeline": "direct_or_nearest_valid_era5_land_in_national_panel_builder",
        "panel_sha256": _sha256(NATIONAL_PANEL_PATH),
    }


def create_2024_snapshot() -> dict[str, object]:
    panel = pq.ParquetFile(NATIONAL_PANEL_PATH).read_row_group(
        OBSERVATION_YEARS.index(2024)
    ).to_pandas()
    mapping_ids = set(_mapping_index().index)
    panel["climate_assignment"] = np.where(
        panel.cell_id.isin(mapping_ids), "nearest_valid_land_fallback", "containing_valid_cell"
    )
    grid = _grid_lookup().set_index("cell_id").loc[panel.cell_id]
    columns = ["cell_id", "observation_year", "outcome_year", *PREDICTOR_COLUMNS, "burned_share_next_year", "climate_assignment"]
    spatial = gpd.GeoDataFrame(
        panel[columns].copy(),
        geometry=shapely.from_wkb(grid.geometry_wkb.to_numpy()),
        crs="EPSG:3763",
    )
    SNAPSHOT_GPKG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = SNAPSHOT_GPKG_PATH.with_name(SNAPSHOT_GPKG_PATH.stem + ".tmp.gpkg")
    if temporary.exists():
        raise FileExistsError(f"Stale snapshot temporary output: {temporary}")
    pyogrio.write_dataframe(spatial, temporary, layer=SNAPSHOT_LAYER, driver="GPKG")
    reopened = pyogrio.read_dataframe(temporary, layer=SNAPSHOT_LAYER)
    if len(reopened) != 89_112 or str(reopened.crs) != "EPSG:3763":
        raise ValueError("T=2024 snapshot failed GeoPackage validation")
    os.replace(temporary, SNAPSHOT_GPKG_PATH)
    return {
        "path": str(SNAPSHOT_GPKG_PATH.relative_to(ROOT)).replace("\\", "/"),
        "layer": SNAPSHOT_LAYER,
        "feature_count": len(reopened),
        "crs": "EPSG:3763",
        "columns": columns,
    }


def ensure_spatial_qa_outputs() -> dict[str, object]:
    """Create/reuse the spatial QA layers referenced by both tracked QGIS projects.

    The mapping and the snapshot are derived artifacts, not input data.  This
    function makes their production explicit after the national panel exists,
    so a clean reproduction leaves every QGIS datasource resolvable even when
    PyQGIS itself is not installed.
    """
    if not MAPPING_PATH.exists() or not ANALYSIS_JSON_PATH.exists():
        metrics = run_analysis()
        mapping_status = "created"
    else:
        mapping = pd.read_parquet(MAPPING_PATH)
        metrics = json.loads(ANALYSIS_JSON_PATH.read_text(encoding="utf-8"))
        if not QA_GPKG_PATH.exists():
            publish_analysis(mapping, metrics)
            mapping_status = "re-published_qa_layer"
        else:
            mapping_status = "reused"

    qa_info = pyogrio.read_info(QA_GPKG_PATH, layer=QA_LAYER)
    if qa_info["features"] != 1_506 or str(qa_info["crs"]) != "EPSG:3763":
        raise ValueError("ERA5 coastal fallback QA layer failed feature-count/CRS validation")

    snapshot = create_2024_snapshot()
    return {
        "mapping_status": mapping_status,
        "affected_cell_count": int(metrics["affected_cell_count"]),
        "qa_layer": {
            "path": str(QA_GPKG_PATH.relative_to(ROOT)).replace("\\", "/"),
            "layer": QA_LAYER,
            "feature_count": int(qa_info["features"]),
            "crs": str(qa_info["crs"]),
        },
        "snapshot": snapshot,
    }


def apply_fallback(progress=print) -> dict[str, object]:
    analysis = json.loads(ANALYSIS_JSON_PATH.read_text(encoding="utf-8"))
    if analysis["new_acquisition_required"] or analysis["distance_km"]["maximum"] >= 20:
        raise ValueError("Fallback acceptance gate failed; panel remains unchanged")
    era = build_fallback_era_batches(progress)
    panel_batches = build_fallback_panel_batches(progress)
    assembly = assemble_fallback_panel(progress)
    validation = validate_fallback_panel()
    snapshot = create_2024_snapshot()
    return {
        "analysis": analysis,
        "era_batches": era,
        "panel_batches": panel_batches,
        "assembly": assembly,
        "validation": validation,
        "snapshot": snapshot,
        "decision": "accepted",
    }
