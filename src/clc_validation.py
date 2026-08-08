"""Read-only validation for prepared Copernicus CLC vector derivatives."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Callable

import geopandas as gpd
import pyogrio
from pyproj import CRS
from shapely import union_all

from src.source_registry import (
    CLC_PREPARED_PORTUGAL_LAYERS,
    ClcPreparedRecord,
)


CLC_CODES = frozenset({
    "111", "112", "121", "122", "123", "124", "131", "132", "133", "141", "142",
    "211", "212", "213", "221", "222", "223", "231", "241", "242", "243", "244",
    "311", "312", "313", "321", "322", "323", "324", "331", "332", "333", "334", "335",
    "411", "412", "421", "422", "423", "511", "512", "521", "522", "523",
})
CLC_2018_CODES = CLC_CODES

CANONICAL_CLC_CLASS_MAPPING = {
    "built_up_share": frozenset({
        "111", "112", "121", "122", "123", "124", "131", "132", "133", "141", "142",
    }),
    "forest_shrub_share_2km": frozenset({"311", "312", "313", "321", "322", "323", "324"}),
}


@dataclass(frozen=True)
class PreparedClcSpec:
    """Expected identity and lineage for one Portugal-clipped CLC layer."""

    reference_year: int
    release_id: str
    raw_source_path: str
    prepared_path: str
    layer_name: str
    class_code_field: str


PREPARED_CLC_SPECS = {
    year: PreparedClcSpec(
        record.reference_year,
        record.release_id,
        record.raw_source_path,
        record.prepared_path,
        record.validation_facts.layer_name,
        record.validation_facts.class_code_field,
    )
    for year, record in CLC_PREPARED_PORTUGAL_LAYERS.items()
}


def calculate_sha256(path: Path) -> str:
    """Calculate an uppercase checksum without modifying the file."""
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_prepared_clc(
    project_root: Path,
    spec: PreparedClcSpec,
    *,
    batch_size: int = 5_000,
    deep_coverage_audit: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    """Validate one Portugal CLC GeoPackage in bounded geometry batches."""
    raw_path = project_root / spec.raw_source_path
    prepared_path = project_root / spec.prepared_path
    boundary_path = project_root / "data/processed/reference/mainland_boundary_caop2025.gpkg"
    for path in (raw_path, prepared_path, boundary_path):
        if not path.is_file():
            raise FileNotFoundError(f"Missing required CLC lineage input: {path}")

    layers = pyogrio.list_layers(prepared_path)
    if layers.tolist() != [[spec.layer_name, "MultiPolygon"]]:
        raise ValueError(f"Unexpected CLC layer definition in {prepared_path.name}: {layers.tolist()}")
    info = pyogrio.read_info(prepared_path, layer=spec.layer_name)
    if CRS.from_user_input(info["crs"]) != CRS.from_epsg(3035):
        raise ValueError(f"Expected EPSG:3035, found {info['crs']}")
    if spec.class_code_field not in info["fields"]:
        raise ValueError(f"Missing {spec.class_code_field} in {prepared_path.name}")
    identity = f"{prepared_path.name} {spec.layer_name}".lower()
    if f"clc{spec.reference_year}" not in identity or "v2020_20u1" not in identity:
        raise ValueError(f"CLC reference year/release identity is not auditable in {prepared_path.name}")

    boundary = gpd.read_file(boundary_path).to_crs(3035)
    if len(boundary) != 1 or boundary.geometry.isna().any() or boundary.geometry.is_empty.any():
        raise ValueError("Canonical mainland boundary is missing or invalid")
    boundary_geometry = boundary.geometry.iloc[0]
    boundary_area = float(boundary_geometry.area)
    boundary_bounds = tuple(float(value) for value in boundary.total_bounds)

    feature_count = int(info["features"])
    observed_codes: set[str] = set()
    geometry_types: Counter[str] = Counter()
    null_count = empty_count = invalid_count = non_polygonal_count = 0
    non_intersecting_mainland_count = 0
    coverage_geometry = None
    processed_count = 0

    for offset in range(0, feature_count, batch_size):
        frame = pyogrio.read_dataframe(
            prepared_path,
            layer=spec.layer_name,
            columns=[spec.class_code_field],
            skip_features=offset,
            max_features=min(batch_size, feature_count - offset),
            use_arrow=True,
        )
        if frame.empty:
            raise ValueError(f"Unexpected empty CLC batch at feature {offset}")
        processed_count += len(frame)
        observed_codes.update(frame[spec.class_code_field].dropna().astype(str).str.strip())

        null_mask = frame.geometry.isna()
        empty_mask = frame.geometry.is_empty
        valid_mask = frame.geometry.is_valid
        type_values = frame.geometry.geom_type.fillna("None")
        polygonal_mask = type_values.isin(("Polygon", "MultiPolygon"))
        geometry_types.update(type_values.tolist())
        null_count += int(null_mask.sum())
        empty_count += int(empty_mask.sum())
        invalid_count += int((~valid_mask & ~null_mask).sum())
        non_polygonal_count += int((~polygonal_mask & ~null_mask).sum())
        usable = ~null_mask & ~empty_mask & valid_mask & polygonal_mask
        non_intersecting_mainland_count += int((~frame.loc[usable].geometry.intersects(boundary_geometry)).sum())

        if deep_coverage_audit:
            chunk_union = union_all(frame.loc[usable].geometry.array)
            coverage_geometry = chunk_union if coverage_geometry is None else union_all(
                [coverage_geometry, chunk_union]
            )
        if progress:
            progress(
                f"CLC {spec.reference_year}: {processed_count}/{feature_count} features; "
                f"codes={len(observed_codes)}; invalid={invalid_count}"
            )

    if processed_count != feature_count or (deep_coverage_audit and coverage_geometry is None):
        raise ValueError(f"Incomplete CLC scan for {spec.reference_year}")
    invalid_codes = sorted(observed_codes - CLC_CODES)
    if invalid_codes:
        raise ValueError(f"Unexpected CLC codes for {spec.reference_year}: {invalid_codes}")

    if deep_coverage_audit:
        missing_mainland_area = float(boundary_geometry.difference(coverage_geometry).area)
        outside_mainland_area = float(coverage_geometry.difference(boundary_geometry).area)
        missing_share = missing_mainland_area / boundary_area
        outside_share = outside_mainland_area / boundary_area
    else:
        missing_share = outside_share = 0.0
    prepared_bounds = tuple(float(value) for value in info["total_bounds"])
    mapping_presence = {
        feature: tuple(sorted(codes & observed_codes))
        for feature, codes in CANONICAL_CLC_CLASS_MAPPING.items()
    }
    ready = (
        null_count == 0
        and empty_count == 0
        and invalid_count == 0
        and non_polygonal_count == 0
        and non_intersecting_mainland_count == 0
        and (not deep_coverage_audit or (missing_share <= 1e-8 and outside_share <= 1e-8))
        and all(mapping_presence.values())
    )
    return {
        "reference_year": spec.reference_year,
        "release_id": spec.release_id,
        "raw_source_path": spec.raw_source_path,
        "prepared_path": spec.prepared_path,
        "storage_format": "GeoPackage",
        "layer_name": spec.layer_name,
        "crs": "EPSG:3035",
        "feature_count": feature_count,
        "geometry_types": dict(sorted(geometry_types.items())),
        "null_geometry_count": null_count,
        "empty_geometry_count": empty_count,
        "invalid_geometry_count": invalid_count,
        "non_polygonal_geometry_count": non_polygonal_count,
        "non_intersecting_mainland_count": non_intersecting_mainland_count,
        "class_code_field": spec.class_code_field,
        "observed_codes": tuple(sorted(observed_codes)),
        "observed_code_count": len(observed_codes),
        "canonical_mapping_codes_present": mapping_presence,
        "prepared_bounds": prepared_bounds,
        "mainland_boundary_bounds": boundary_bounds,
        "missing_mainland_area_share": missing_share,
        "outside_mainland_area_share": outside_share,
        "coverage_audit": "deep" if deep_coverage_audit else "structural_only",
        "prepared_sha256": calculate_sha256(prepared_path),
        "spatial_processing": (
            "Vector polygons in EPSG:3035 are suitable for equal-area intersection. "
            "Reproject the EPSG:3763 grid and 2 km buffers to EPSG:3035 during CLC share derivation."
        ),
        "ready": ready,
    }


def validate_registered_prepared_clc(
    project_root: Path,
    record: ClcPreparedRecord,
    *,
    batch_size: int = 5_000,
    deep_coverage_audit: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    """Validate a registered prepared layer against its immutable facts."""
    spec = PreparedClcSpec(
        record.reference_year,
        record.release_id,
        record.raw_source_path,
        record.prepared_path,
        record.validation_facts.layer_name,
        record.validation_facts.class_code_field,
    )
    result = validate_prepared_clc(
        project_root,
        spec,
        batch_size=batch_size,
        deep_coverage_audit=deep_coverage_audit,
        progress=progress,
    )
    facts = record.validation_facts
    expected = {
        "feature_count": facts.feature_count,
        "geometry_types": {facts.geometry_type: facts.feature_count},
        "null_geometry_count": facts.null_geometry_count,
        "empty_geometry_count": facts.empty_geometry_count,
        "invalid_geometry_count": facts.invalid_geometry_count,
        "non_polygonal_geometry_count": facts.non_polygonal_geometry_count,
        "non_intersecting_mainland_count": facts.non_intersecting_mainland_count,
        "class_code_field": facts.class_code_field,
        "observed_codes": facts.observed_codes,
    }
    if deep_coverage_audit:
        expected["missing_mainland_area_share"] = facts.missing_mainland_area_share
        expected["outside_mainland_area_share"] = facts.outside_mainland_area_share
    for key, value in expected.items():
        if result[key] != value:
            raise ValueError(f"Prepared CLC {record.reference_year} differs at {key}")
    if not result["ready"]:
        raise ValueError(f"Prepared CLC {record.reference_year} failed readiness validation")
    # GeoPackage byte streams can differ across GDAL/SQLite versions even when
    # raw source, spatial coverage, schema, class codes, and geometries are
    # equivalent. Preserve the historical checksum as provenance but validate a
    # regenerated checkout semantically rather than requiring identical pages.
    result["registered_prepared_sha256"] = record.prepared_sha256
    result["prepared_checksum_matches_registered"] = result["prepared_sha256"] == record.prepared_sha256
    return result
