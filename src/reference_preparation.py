"""Build reusable CAOP and Portugal-clipped CLC reference derivatives.

Raw archives remain immutable. CAOP and CLC GeoPackages are extracted only to
system temporary directories, while the published derivatives are written under
``data/processed``.  CLC reads use a spatial bounding-box filter so the full
European source layer is never loaded into memory.
"""

from __future__ import annotations

import os
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile

import geopandas as gpd
import numpy as np
import pyogrio
from pyproj import CRS
import shapely
from shapely.geometry import MultiPolygon

from src.config import SPATIAL
from src.geospatial_utils import GRID_PATH
from src.source_registry import CAOP_2025, CLC_PREPARED_PORTUGAL_LAYERS


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "data/processed/reference"
BOUNDARY_PATH = REFERENCE_DIR / "mainland_boundary_caop2025.gpkg"
MUNICIPALITIES_PATH = REFERENCE_DIR / "municipalities_caop2025.gpkg"
CANONICAL_GRID_LAYER = "canonical_mainland_grid_1km"
EXPECTED_CANONICAL_GRID_CELLS = 89_112


def _extract_single_gpkg(archive_path: Path, temporary_directory: Path) -> Path:
    with zipfile.ZipFile(archive_path) as archive:
        members = [member for member in archive.namelist() if member.lower().endswith(".gpkg")]
        if len(members) != 1:
            raise ValueError(f"Expected one GeoPackage member in {archive_path.name}, found {members}")
        member = members[0]
        target = temporary_directory / Path(member).name
        with archive.open(member) as source, target.open("xb") as destination:
            while block := source.read(8 * 1024 * 1024):
                destination.write(block)
    return target


def _write_gpkg(frame: gpd.GeoDataFrame, path: Path, layer: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.stem + "_temporary.gpkg")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary GeoPackage requires inspection: {temporary}")
    pyogrio.write_dataframe(frame, temporary, layer=layer, driver="GPKG")
    os.replace(temporary, path)


def prepare_caop_reference_layers() -> dict[str, object]:
    """Create/reuse the canonical mainland boundary and municipality layers."""
    if BOUNDARY_PATH.is_file() and MUNICIPALITIES_PATH.is_file():
        return {"status": "validated_reused", "boundary": str(BOUNDARY_PATH.relative_to(ROOT)), "municipalities": str(MUNICIPALITIES_PATH.relative_to(ROOT))}
    if BOUNDARY_PATH.exists() or MUNICIPALITIES_PATH.exists():
        raise FileExistsError("Incomplete CAOP reference output requires inspection")
    archive_path = ROOT / CAOP_2025.raw_path
    if not archive_path.is_file():
        raise FileNotFoundError(f"Missing immutable CAOP archive: {archive_path}")
    with TemporaryDirectory(prefix="wildfire_caop_") as temp:
        gpkg = _extract_single_gpkg(archive_path, Path(temp))
        boundary = pyogrio.read_dataframe(gpkg, layer="cont_nuts1", columns=["nuts1"])
        municipalities = pyogrio.read_dataframe(gpkg, layer="cont_municipios", columns=["dtmn", "municipio"])
    if CRS.from_user_input(boundary.crs) != CRS.from_epsg(3763) or CRS.from_user_input(municipalities.crs) != CRS.from_epsg(3763):
        raise ValueError("CAOP reference layers must use EPSG:3763")
    boundary = boundary.loc[boundary["nuts1"] == "Continente", ["nuts1", "geometry"]].copy()
    if len(boundary) != 1 or boundary.geometry.isna().any() or boundary.geometry.is_empty.any() or not boundary.geometry.is_valid.all():
        raise ValueError("CAOP cont_nuts1 did not yield one valid mainland boundary")
    municipalities = municipalities.loc[:, ["dtmn", "municipio", "geometry"]].copy()
    if len(municipalities) != 278 or municipalities.dtmn.isna().any() or not municipalities.dtmn.is_unique:
        raise ValueError("CAOP municipalities do not satisfy the registered mainland contract")
    if municipalities.geometry.isna().any() or municipalities.geometry.is_empty.any() or not municipalities.geometry.is_valid.all():
        raise ValueError("CAOP municipalities contain invalid or empty geometry")
    _write_gpkg(boundary, BOUNDARY_PATH, "mainland_boundary_caop2025")
    _write_gpkg(municipalities, MUNICIPALITIES_PATH, "municipalities_caop2025")
    return {"status": "created", "boundary": str(BOUNDARY_PATH.relative_to(ROOT)), "municipalities": str(MUNICIPALITIES_PATH.relative_to(ROOT))}


def _validate_canonical_grid() -> dict[str, object]:
    """Validate the deterministic grid contract before it is reused."""
    info = pyogrio.read_info(GRID_PATH, layer=CANONICAL_GRID_LAYER)
    if str(info["crs"]) != SPATIAL.analysis_crs:
        raise ValueError("Canonical grid must use EPSG:3763")
    if info["geometry_type"] != "Polygon" or info["features"] != EXPECTED_CANONICAL_GRID_CELLS:
        raise ValueError("Canonical grid does not satisfy the 89,112-cell Polygon contract")
    frame = pyogrio.read_dataframe(GRID_PATH, layer=CANONICAL_GRID_LAYER, columns=["cell_id"])
    if (
        frame.cell_id.isna().any()
        or not frame.cell_id.is_unique
        or frame.geometry.isna().any()
        or frame.geometry.is_empty.any()
        or not frame.geometry.is_valid.all()
    ):
        raise ValueError("Canonical grid contains invalid identifiers or geometry")
    return {
        "path": str(GRID_PATH.relative_to(ROOT)),
        "layer": CANONICAL_GRID_LAYER,
        "cell_count": len(frame),
    }


def _canonical_grid_geometries(boundary) -> np.ndarray:
    """Return canonical grid squares in stable west-to-east/south-to-north order."""
    minx, miny, maxx, maxy = boundary.bounds
    size = SPATIAL.grid_size_metres
    x_values = np.arange(math.floor(minx / size) * size, math.ceil(maxx / size) * size, size)
    y_values = np.arange(math.floor(miny / size) * size, math.ceil(maxy / size) * size, size)
    x_coordinates = np.repeat(x_values, len(y_values))
    y_coordinates = np.tile(y_values, len(x_values))
    candidates = shapely.box(
        x_coordinates, y_coordinates, x_coordinates + size, y_coordinates + size,
    )
    centres = shapely.points(x_coordinates + size / 2, y_coordinates + size / 2)
    # STRtree avoids evaluating the detailed CAOP boundary against every square
    # one at a time. Sorting restores the stable west-to-east/south-to-north
    # candidate order after spatial filtering.
    selected = np.sort(shapely.STRtree(centres).query(boundary, predicate="contains"))
    return candidates[selected]


def prepare_canonical_mainland_grid() -> dict[str, object]:
    """Create/reuse the stable 1 km EPSG:3763 grid from the CAOP boundary.

    A full 1 km square is retained when its centre lies within mainland
    Portugal. Downstream processing derives coastal land area and
    mainland-masked 2 km context separately. IDs are assigned in deterministic
    west-to-east, south-to-north order.
    """
    if GRID_PATH.is_file():
        return {"status": "validated_reused", **_validate_canonical_grid()}
    if GRID_PATH.exists():
        raise FileExistsError(f"Incomplete canonical grid output requires inspection: {GRID_PATH}")
    if not BOUNDARY_PATH.is_file():
        raise FileNotFoundError("Prepare the CAOP mainland boundary before creating the canonical grid")

    boundary_frame = pyogrio.read_dataframe(BOUNDARY_PATH, columns=[])
    if len(boundary_frame) != 1 or str(boundary_frame.crs) != SPATIAL.analysis_crs:
        raise ValueError("Expected one EPSG:3763 CAOP mainland boundary")
    boundary = boundary_frame.geometry.iloc[0]
    geometries = _canonical_grid_geometries(boundary)
    if len(geometries) != EXPECTED_CANONICAL_GRID_CELLS:
        raise ValueError(
            f"Grid centre selection produced {len(geometries)} cells, expected {EXPECTED_CANONICAL_GRID_CELLS}"
        )
    grid = gpd.GeoDataFrame(
        {"cell_id": [f"PT3763_{index:06d}" for index in range(len(geometries))]},
        geometry=geometries,
        crs=SPATIAL.analysis_crs,
    )
    _write_gpkg(grid, GRID_PATH, CANONICAL_GRID_LAYER)
    return {"status": "created", **_validate_canonical_grid()}


def _raw_clc_layer(gpkg: Path, class_code_field: str) -> str:
    for layer_name, _geometry_type in pyogrio.list_layers(gpkg):
        if class_code_field in pyogrio.read_info(gpkg, layer=layer_name)["fields"]:
            return str(layer_name)
    raise ValueError(f"No CLC layer contains required field {class_code_field}")


def _as_multipolygon(geometry):
    if geometry is None or geometry.is_empty:
        return geometry
    if geometry.geom_type == "Polygon":
        return MultiPolygon([geometry])
    if geometry.geom_type == "MultiPolygon":
        return geometry
    raise ValueError(f"CLC clip produced non-polygonal geometry: {geometry.geom_type}")


def prepare_portugal_clc_layers() -> dict[str, object]:
    """Create/reuse the three governed CLC Portugal derivatives in EPSG:3035."""
    if not BOUNDARY_PATH.is_file():
        raise FileNotFoundError("Prepare the CAOP mainland boundary before clipping CLC")
    boundary = pyogrio.read_dataframe(BOUNDARY_PATH, columns=[]).to_crs(3035)
    if len(boundary) != 1:
        raise ValueError("Expected one canonical mainland boundary")
    boundary_geometry = boundary.geometry.iloc[0]
    results: dict[str, object] = {}
    for year, record in CLC_PREPARED_PORTUGAL_LAYERS.items():
        output = ROOT / record.prepared_path
        if output.is_file():
            results[str(year)] = {"status": "reused", "path": str(output.relative_to(ROOT))}
            continue
        raw = ROOT / record.raw_source_path
        if not raw.is_file():
            raise FileNotFoundError(f"Missing immutable CLC ZIP: {raw}")
        with TemporaryDirectory(prefix=f"wildfire_clc_{year}_") as temp:
            source_gpkg = _extract_single_gpkg(raw, Path(temp))
            layer = _raw_clc_layer(source_gpkg, record.validation_facts.class_code_field)
            candidates = pyogrio.read_dataframe(
                source_gpkg,
                layer=layer,
                columns=[record.validation_facts.class_code_field],
                bbox=tuple(boundary.total_bounds),
                use_arrow=True,
            )
        if CRS.from_user_input(candidates.crs) != CRS.from_epsg(3035):
            raise ValueError(f"CLC {year} source is not EPSG:3035")
        clipped = candidates.loc[candidates.geometry.intersects(boundary_geometry)].copy()
        clipped.geometry = clipped.geometry.intersection(boundary_geometry).map(_as_multipolygon)
        clipped = clipped.loc[~clipped.geometry.is_empty].copy()
        if clipped.empty or clipped.geometry.isna().any() or not clipped.geometry.is_valid.all():
            raise ValueError(f"CLC {year} clip did not produce valid non-empty polygons")
        _write_gpkg(clipped, output, record.validation_facts.layer_name)
        results[str(year)] = {"status": "created", "path": str(output.relative_to(ROOT)), "feature_count": len(clipped)}
    return results
