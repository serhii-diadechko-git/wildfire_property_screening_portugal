"""Read-only validation for the registered CLC 2018 mainland vector derivative."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pyogrio
from pyproj import CRS

from src.source_registry import CLC_2018_MAINLAND_INTERIM, InterimDerivativeRecord


CLC_2018_CODES = frozenset({
    "111", "112", "121", "122", "123", "124", "131", "132", "133", "141", "142",
    "211", "212", "213", "221", "222", "223", "231", "241", "242", "243", "244",
    "311", "312", "313", "321", "322", "323", "324", "331", "332", "333", "334", "335",
    "411", "412", "421", "422", "423", "511", "512", "521", "522", "523",
})


def validate_clc_2018_mainland(
    project_root: Path,
    record: InterimDerivativeRecord = CLC_2018_MAINLAND_INTERIM,
) -> dict[str, object]:
    """Validate an existing clipped vector without changing it or the raw ZIP."""
    source_path = project_root / record.input_source_path
    boundary_path = project_root / record.boundary_path
    output_path = project_root / record.output_path
    for path in (source_path, boundary_path, output_path):
        if not path.is_file():
            raise FileNotFoundError(f"Missing required CLC provenance input: {path}")

    layers = pyogrio.list_layers(output_path)
    facts = record.validation_facts
    expected_layer = facts.layer_name if facts else "clc_2018_mainland"
    if len(layers) != 1 or layers[0][0] != expected_layer:
        raise ValueError(f"Expected one clc_2018_mainland layer, found {layers.tolist()}")
    if layers[0][1] not in {"Polygon", "MultiPolygon"}:
        raise ValueError(f"CLC derivative is not vector polygon data: {layers[0][1]}")

    clc = gpd.read_file(output_path, layer=expected_layer)
    boundary_layer = pyogrio.list_layers(boundary_path)
    if len(boundary_layer) != 1:
        raise ValueError("Mainland boundary GeoPackage must have exactly one layer")
    boundary = gpd.read_file(boundary_path, layer=boundary_layer[0][0]).to_crs(clc.crs)
    if clc.crs is None or CRS.from_user_input(clc.crs) != CRS.from_epsg(3035):
        raise ValueError(f"Expected CLC EPSG:3035, found {clc.crs}")
    if "Code_18" not in clc.columns:
        raise ValueError("Missing expected CLC 2018 class-code field Code_18")
    codes = set(clc["Code_18"].astype(str))
    invalid_codes = sorted(codes - CLC_2018_CODES)
    if invalid_codes:
        raise ValueError(f"Unexpected CLC codes: {invalid_codes}")

    null_count = int(clc.geometry.isna().sum())
    empty_count = int(clc.geometry.is_empty.sum())
    invalid_count = int((~clc.geometry.is_valid).sum())
    if null_count or empty_count or invalid_count:
        raise ValueError("CLC geometry contains null, empty, or invalid values")
    if facts and (
        len(clc) != facts.feature_count
        or str(layers[0][1]) != facts.geometry_type
        or "Code_18" != facts.class_code_field
        or len(codes) != facts.unique_valid_clc_code_count
        or null_count != facts.null_geometry_count
        or empty_count != facts.empty_geometry_count
        or invalid_count != facts.invalid_geometry_count
    ):
        raise ValueError("CLC derivative no longer matches its registered validation facts")
    boundary_bounds = tuple(float(value) for value in boundary.total_bounds)
    clc_bounds = tuple(float(value) for value in clc.total_bounds)
    tolerance = 0.01
    if not (boundary_bounds[0] - tolerance <= clc_bounds[0] <= clc_bounds[2] <= boundary_bounds[2] + tolerance
            and boundary_bounds[1] - tolerance <= clc_bounds[1] <= clc_bounds[3] <= boundary_bounds[3] + tolerance):
        raise ValueError("CLC derivative extent is outside the mainland boundary envelope")
    return {
        "layer": expected_layer,
        "vector_geometry_type": str(layers[0][1]),
        "crs": "EPSG:3035",
        "feature_count": len(clc),
        "class_code_field": "Code_18",
        "unique_valid_clc_codes": len(codes),
        "null_geometry_count": null_count,
        "empty_geometry_count": empty_count,
        "invalid_geometry_count": invalid_count,
        "clc_extent": clc_bounds,
        "mainland_boundary_extent_in_clc_crs": boundary_bounds,
        "extent_within_mainland_boundary_envelope": True,
        "raw_source_unchanged_path": record.input_source_path,
        "interim_output_path": record.output_path,
        "clip_method": record.clip_method,
        "raster_required": False,
    }
