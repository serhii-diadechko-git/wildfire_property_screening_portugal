"""Retrieve the two missing immutable ERA5-Land annual inputs for the full panel."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cdsapi

from src.config import ERA5_LAND, ERA5_LAND_CDS
from src.era5_land_validation import validate_era5_land_grib_record
from src.source_registry import ERA5_LAND_2022_JJAS, ERA5_LAND_2024_JJAS


YEARS = (2022, 2024)
RECORDS = {2022: ERA5_LAND_2022_JJAS, 2024: ERA5_LAND_2024_JJAS}


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


def validate_contract(path: Path, year: int) -> None:
    if path != ROOT / RECORDS[year].raw_path:
        raise ValueError(f"{year}: validation path differs from the governed raw path")
    result = validate_era5_land_grib_record(RECORDS[year], ROOT)
    print(
        f"Validated {path.name}: {result['precipitation_status']}; "
        f"{result['validation_note']}",
        flush=True,
    )


def main() -> None:
    output_directory = ROOT / "data/raw/climate/era5_land"
    output_directory.mkdir(parents=True, exist_ok=True)
    client = None
    for year in YEARS:
        target = output_directory / f"era5_land_monthly_jjas_{year}_mainland_portugal.grib"
        if target.exists():
            validate_contract(target, year)
            continue
        if client is None:
            client = cdsapi.Client()
        client.retrieve(ERA5_LAND_CDS.dataset_id, request_for_year(year), str(target))
        validate_contract(target, year)


if __name__ == "__main__":
    main()
