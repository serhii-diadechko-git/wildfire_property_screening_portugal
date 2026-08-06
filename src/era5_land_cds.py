"""Build and optionally submit one immutable annual ERA5-Land CDS request.

Request construction and dry-run validation never read CDS credentials. Retrieval
delegates authentication to ``cdsapi`` and refuses to overwrite a raw file.
"""

from __future__ import annotations

from pathlib import Path

from src.config import ERA5_LAND, ERA5_LAND_CDS


def build_request(year: int, *, corrected_precipitation: bool = False) -> dict[str, object]:
    """Return one bounded JJAS request without making a network call."""
    if year < 1950:
        raise ValueError("ERA5-Land annual requests must be for 1950 or later")
    return {
        "product_type": [
            "monthly_averaged_reanalysis_by_hour_of_day"
            if corrected_precipitation
            else ERA5_LAND_CDS.product_type
        ],
        "variable": ["total_precipitation"] if corrected_precipitation else list(ERA5_LAND.variables),
        "year": [str(year)],
        "month": [f"{month:02d}" for month in ERA5_LAND.season_months],
        "time": ["00:00"],
        "data_format": ERA5_LAND_CDS.data_format,
        "download_format": ERA5_LAND_CDS.download_format,
        "area": list(ERA5_LAND_CDS.mainland_portugal_area),
    }


def output_path(project_root: Path, year: int, *, corrected_precipitation: bool = False) -> Path:
    return (
        project_root
        / ERA5_LAND_CDS.raw_directory
        / ERA5_LAND_CDS.output_filename(year, corrected_precipitation=corrected_precipitation)
    )


def dry_run(project_root: Path, year: int, *, corrected_precipitation: bool = False) -> dict[str, object]:
    """Validate the request contract without network or credential access."""
    target = output_path(project_root, year, corrected_precipitation=corrected_precipitation)
    return {
        "dataset_id": ERA5_LAND_CDS.dataset_id,
        "request": build_request(year, corrected_precipitation=corrected_precipitation),
        "target": str(target),
        "network_called": False,
        "credentials_read": False,
        "target_exists": target.exists(),
    }


def retrieve(project_root: Path, year: int, *, corrected_precipitation: bool = False) -> Path:
    """Retrieve one original GRIB, refusing to overwrite an existing raw file."""
    try:
        import cdsapi
    except ImportError as error:
        raise RuntimeError("Install the pinned cdsapi dependency before retrieval") from error

    target = output_path(project_root, year, corrected_precipitation=corrected_precipitation)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing raw download: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    cdsapi.Client().retrieve(
        ERA5_LAND_CDS.dataset_id,
        build_request(year, corrected_precipitation=corrected_precipitation),
        str(target),
    )
    return target
