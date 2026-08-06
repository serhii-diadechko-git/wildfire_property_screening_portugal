"""Stable paths and low-level geometry helpers shared by national workflows."""

from __future__ import annotations

from pathlib import Path
import zipfile

import shapely


ROOT = Path(__file__).resolve().parents[1]
GRID_PATH = ROOT / "data/processed/reference/canonical_mainland_grid_1km.gpkg"
BOUNDARY_PATH = ROOT / "data/processed/reference/mainland_boundary_caop2025.gpkg"
ICNF_ROOT = ROOT / "data/raw/wildfire/icnf_burned_areas"


def polygonal_geometry(geometry):
    """Return valid polygonal content from a repaired geometry candidate."""
    if geometry is None or geometry.is_empty:
        return None
    if geometry.geom_type in ("Polygon", "MultiPolygon"):
        return geometry
    if geometry.geom_type == "GeometryCollection":
        parts = [polygonal_geometry(part) for part in geometry.geoms]
        parts = [part for part in parts if part is not None and not part.is_empty]
        if parts:
            merged = shapely.union_all(parts)
            return merged if merged.geom_type in ("Polygon", "MultiPolygon") else None
    return None


def icnf_vsi_path(archive_path: Path) -> str:
    """Return a GDAL /vsizip path after validating required Shapefile members."""
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


def dem_tile_bounds(tile_id: str) -> tuple[float, float, float, float]:
    """Return the one-degree WGS84 bounds encoded by a GLO-30 tile identifier."""
    latitude = int(tile_id[1:3])
    longitude = -int(tile_id.split("W", 1)[1].split("_", 1)[0])
    return longitude, latitude, longitude + 1, latitude + 1
