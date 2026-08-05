"""Retrieve five validated immutable ERA5-Land JJAS inputs for T=2010-2014."""

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
from src.era5_land_validation import EXTENDED_TRAINING_ERA5_YEARS, validate_extended_training_era5_grib


def request_for_year(year: int) -> dict[str, object]:
    return {
        "product_type": [ERA5_LAND_CDS.product_type],
        "variable": list(ERA5_LAND.variables),
        "year": [str(year)],
        "month": ["06", "07", "08", "09"],
        "time": ["00:00"],
        "data_format": ERA5_LAND_CDS.data_format,
        "download_format": ERA5_LAND_CDS.download_format,
        "area": list(ERA5_LAND_CDS.mainland_portugal_area),
    }


def main() -> None:
    output_directory = ROOT / "data/raw/climate/era5_land"
    output_directory.mkdir(parents=True, exist_ok=True)
    client = None
    results = []
    for year in EXTENDED_TRAINING_ERA5_YEARS:
        target = output_directory / f"era5_land_monthly_jjas_{year}_mainland_portugal.grib"
        temporary = target.with_suffix(".grib.part")
        if target.exists():
            results.append(validate_extended_training_era5_grib(target, year))
            continue
        if temporary.exists():
            raise FileExistsError(f"Refusing to overwrite incomplete retrieval: {temporary}")
        if client is None:
            client = cdsapi.Client()
        client.retrieve(ERA5_LAND_CDS.dataset_id, request_for_year(year), str(temporary))
        result = validate_extended_training_era5_grib(temporary, year)
        os.replace(temporary, target)
        results.append(
            result
            | {
                "raw_path": target.relative_to(ROOT).as_posix(),
                "filename": target.name,
            }
        )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
