"""Build and optionally submit the approved small ERA5-Land CDS pilot request.

The default operation is a credential-free dry run.  Retrieval requires an
explicit caller action and relies on CDS credentials configured outside this
repository (for example, in the user's .cdsapirc file).
"""

from __future__ import annotations

from pathlib import Path

from src.config import ERA5_LAND, ERA5_LAND_CDS, PILOT_2023_TO_2024


def build_pilot_request() -> dict[str, object]:
    """Return the exact CDS request; make no network call or filesystem change."""
    if PILOT_2023_TO_2024.predictor_year != 2023:
        raise ValueError("This request module is limited to the approved 2023 pilot")
    return {
        "product_type": [ERA5_LAND_CDS.product_type],
        "variable": list(ERA5_LAND.variables),
        "year": [str(PILOT_2023_TO_2024.predictor_year)],
        "month": [f"{month:02d}" for month in ERA5_LAND.season_months],
        "time": ["00:00"],
        "data_format": ERA5_LAND_CDS.data_format,
        "download_format": ERA5_LAND_CDS.download_format,
        "area": list(ERA5_LAND_CDS.mainland_portugal_area),
    }


def dry_run(project_root: Path) -> dict[str, object]:
    """Validate the local request contract without contacting CDS."""
    target = project_root / ERA5_LAND_CDS.pilot_raw_output
    request = build_pilot_request()
    return {
        "dataset_id": ERA5_LAND_CDS.dataset_id,
        "request": request,
        "target": str(target),
        "network_called": False,
        "credentials_read": False,
        "target_exists": target.exists(),
    }


def retrieve_pilot(project_root: Path) -> Path:
    """Submit the approved CDS request after the user has configured credentials."""
    try:
        import cdsapi
    except ImportError as error:
        raise RuntimeError("Install cdsapi>=0.7.7 before retrieval") from error

    target = project_root / ERA5_LAND_CDS.pilot_raw_output
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing raw download: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    cdsapi.Client().retrieve(ERA5_LAND_CDS.dataset_id, build_pilot_request(), str(target))
    return target
