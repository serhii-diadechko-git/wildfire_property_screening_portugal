"""Read-only validation helpers for registered raw sources and ERA5-Land requests."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

import geopandas as gpd
from pyproj import CRS

from src.config import ERA5_LAND, PILOT_2023_TO_2024, TEMPORAL
from src.source_registry import SourceRecord


ANALYSIS_CRS = CRS.from_epsg(3763)
ERA5_LAND_DOCUMENTED_START_YEAR = 1950
ERA5_LAND_EXPECTED_VARIABLES = {
    "2m_temperature",
    "total_precipitation",
    "volumetric_soil_water_layer_1",
}


def calculate_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return an uppercase SHA-256 checksum without changing the file."""
    digest = sha256()
    with file_path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def validate_zip_archive(record: SourceRecord, project_root: Path) -> dict[str, object]:
    """Validate filename, checksum, CRCs, and required member names in place."""
    archive_path = project_root / record.raw_path
    if not archive_path.is_file():
        raise FileNotFoundError(f"Missing raw archive: {archive_path}")
    if archive_path.name != record.filename:
        raise ValueError(f"Unexpected filename: {archive_path.name}")

    checksum = calculate_sha256(archive_path)
    if checksum != record.expected_sha256:
        raise ValueError(f"SHA-256 mismatch for {archive_path.name}: {checksum}")

    with ZipFile(archive_path) as archive:
        members = tuple(member for member in archive.namelist() if not member.endswith("/"))
        corrupt_member = archive.testzip()
    missing = sorted(set(record.required_members) - set(members))
    if corrupt_member:
        raise ValueError(f"ZIP CRC validation failed for member: {corrupt_member}")
    if missing:
        raise ValueError(f"Missing required archive members: {missing}")

    return {
        "raw_path": record.raw_path,
        "filename": record.filename,
        "size_bytes": archive_path.stat().st_size,
        "sha256": checksum,
        "zip_integrity": "passed",
        "archive_members": members,
        "required_members_present": True,
    }


def validate_icnf_archive(
    record: SourceRecord,
    project_root: Path,
    *,
    expected_year: int,
    expected_feature_count: int | None = None,
) -> dict[str, object]:
    """Inspect and validate an ICNF Shapefile directly through GDAL `/vsizip`.

    Validation is against the registered archive facts.  It deliberately reports
    invalid geometries rather than repairing, dropping, or treating them as no fire.
    """
    archive_validation = validate_zip_archive(record, project_root)
    archive_path = project_root / record.raw_path
    shapefile_name = next(member for member in record.required_members if member.endswith(".shp"))

    virtual_path = f"/vsizip/{archive_path.resolve().as_posix()}/{shapefile_name}"
    frame = gpd.read_file(virtual_path)

    if frame.crs is None or CRS.from_user_input(frame.crs) != ANALYSIS_CRS:
        raise ValueError(f"ICNF: expected EPSG:3763, found {frame.crs}")
    facts = record.validation_facts
    expected_count = expected_feature_count if expected_feature_count is not None else (facts.feature_count if facts else None)
    if expected_count is not None and len(frame) != expected_count:
        raise ValueError(f"ICNF: expected {expected_count} features, found {len(frame)}")
    required_fields = facts.required_fields if facts else ("Ano", "AreaHaSIG")
    missing_fields = [field for field in required_fields if field not in frame.columns]
    if missing_fields:
        raise ValueError(f"ICNF: missing required fields {missing_fields}")
    if not frame["Ano"].eq(expected_year).all():
        raise ValueError(f"ICNF: all Ano values must equal {expected_year}")
    null_geometry_count = int(frame.geometry.isna().sum())
    non_empty_geometry_count = int((~frame.geometry.isna() & ~frame.geometry.is_empty).sum())
    invalid_geometry_count = int((~frame.geometry.is_valid).sum())
    field_names = tuple(column for column in frame.columns if column != "geometry")
    if null_geometry_count:
        raise ValueError("ICNF: geometry contains null values")
    if facts and facts.field_names is not None and field_names != facts.field_names:
        raise ValueError(f"ICNF: schema differs from registered facts for {record.filename}")
    if facts and non_empty_geometry_count != facts.non_empty_geometry_count:
        raise ValueError(f"ICNF: non-empty geometry count differs from registered facts for {record.filename}")
    if facts and invalid_geometry_count != facts.invalid_geometry_count:
        raise ValueError(f"ICNF: invalid geometry count differs from registered facts for {record.filename}")

    return archive_validation | {
        "crs": "EPSG:3763",
        "feature_count": len(frame),
        "year_field": "Ano",
        "year": expected_year,
        "field_names": field_names,
        "required_fields_present": True,
        "non_empty_geometry_count": non_empty_geometry_count,
        "invalid_geometry_count": invalid_geometry_count,
        "geometries_valid_and_non_empty": invalid_geometry_count == 0 and non_empty_geometry_count == len(frame),
    }


def validate_era5_land_request(
    predictor_year: int,
    variables: tuple[str, ...] = ERA5_LAND.variables,
) -> dict[str, object]:
    """Validate a documented ERA5-Land request without contacting CDS."""
    if predictor_year < ERA5_LAND_DOCUMENTED_START_YEAR:
        raise ValueError(f"ERA5-Land coverage begins in {ERA5_LAND_DOCUMENTED_START_YEAR}")
    if predictor_year > TEMPORAL.predictor_end_year:
        raise ValueError("Predictor year is outside the approved retrospective panel")
    if set(variables) != ERA5_LAND_EXPECTED_VARIABLES:
        raise ValueError("ERA5-Land variable configuration does not match the approved feature set")
    if ERA5_LAND.season_months != (6, 7, 8, 9):
        raise ValueError("ERA5-Land season must be June through September")

    return {
        "predictor_year": predictor_year,
        "documented_temporal_coverage": f"{ERA5_LAND_DOCUMENTED_START_YEAR}-present",
        "season": "JJAS",
        "season_months": ERA5_LAND.season_months,
        "variables": variables,
        "assignment_method": ERA5_LAND.assignment_method,
        "coverage_check": "configuration only; no CDS request was made",
    }


def validate_era5_land_pilot_request() -> dict[str, object]:
    """Validate the approved 2023 ERA5-Land request and its T-only relationship."""
    if PILOT_2023_TO_2024.outcome_year != PILOT_2023_TO_2024.predictor_year + 1:
        raise ValueError("Pilot outcome year must equal predictor year + 1")
    if any(year >= PILOT_2023_TO_2024.predictor_year for year in PILOT_2023_TO_2024.historical_fire_years):
        raise ValueError("Historical-fire years must be strictly before the predictor year")
    return validate_era5_land_request(PILOT_2023_TO_2024.predictor_year) | {
        "outcome_year": PILOT_2023_TO_2024.outcome_year,
    }
