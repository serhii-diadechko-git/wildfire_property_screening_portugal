"""Retrieve and validate the immutable T=2025 ERA5-Land JJAS scoring input.

Credentials are resolved only by ``cdsapi`` from the user's external CDS
configuration.  This script neither reads nor prints the credentials file.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cdsapi

from src.config import ERA5_LAND, ERA5_LAND_CDS
from src.era5_land_validation import validate_unregistered_annual_era5_grib


YEAR = 2025


def request() -> dict[str, object]:
    return {
        "product_type": [ERA5_LAND_CDS.product_type],
        "variable": list(ERA5_LAND.variables),
        "year": [str(YEAR)],
        "month": ["06", "07", "08", "09"],
        "time": ["00:00"],
        "data_format": ERA5_LAND_CDS.data_format,
        "download_format": ERA5_LAND_CDS.download_format,
        "area": list(ERA5_LAND_CDS.mainland_portugal_area),
    }


def main() -> None:
    output_directory = ROOT / "data/raw/climate/era5_land"
    target = output_directory / f"era5_land_monthly_jjas_{YEAR}_mainland_portugal.grib"
    temporary = target.with_suffix(".grib.part")
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite immutable raw file: {target}")
    if temporary.exists():
        raise FileExistsError(f"Refusing to overwrite incomplete retrieval: {temporary}")
    output_directory.mkdir(parents=True, exist_ok=True)
    cdsapi.Client().retrieve(ERA5_LAND_CDS.dataset_id, request(), str(temporary))
    result = validate_unregistered_annual_era5_grib(temporary, YEAR)
    os.replace(temporary, target)
    result["raw_path"] = target.relative_to(ROOT).as_posix()
    result["dataset_id"] = ERA5_LAND_CDS.dataset_id
    result["request"] = request()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
