"""Retrieve the official ERA5-Land precipitation workaround for 2022 and 2023.

The affected monthly-averaged originals remain immutable.  This script retrieves
only total precipitation from the by-hour-of-day product at 00:00, as directed
by the official ECMWF known-issue documentation.
"""

from hashlib import sha256
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cdsapi
from eccodes import codes_get, codes_grib_new_from_file, codes_release
import xarray as xr

from src.config import ERA5_LAND_CDS


YEARS = (2022, 2023)
MONTHS = ("06", "07", "08", "09")
PRODUCT_TYPE = "monthly_averaged_reanalysis_by_hour_of_day"
VARIABLE = "total_precipitation"
EXPECTED_SHAPE = (4, 55, 37)


def target_path(year: int) -> Path:
    return ROOT / (
        "data/raw/climate/era5_land/"
        f"era5_land_monthly_by_hour_00_jjas_total_precipitation_{year}_mainland_portugal.grib"
    )


def request_for_year(year: int) -> dict[str, object]:
    return {
        "product_type": [PRODUCT_TYPE],
        "variable": [VARIABLE],
        "year": [str(year)],
        "month": list(MONTHS),
        "time": ["00:00"],
        "data_format": ERA5_LAND_CDS.data_format,
        "download_format": ERA5_LAND_CDS.download_format,
        "area": list(ERA5_LAND_CDS.mainland_portugal_area),
    }


def checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def grib_contract(path: Path) -> dict[str, str]:
    observed: dict[str, str] | None = None
    message_count = 0
    with path.open("rb") as stream:
        while message := codes_grib_new_from_file(stream):
            try:
                message_count += 1
                metadata = {
                    "short_name": str(codes_get(message, "shortName")),
                    "units": str(codes_get(message, "units")),
                    "step_type": str(codes_get(message, "stepType")),
                    "step_range": str(codes_get(message, "stepRange")),
                    "stream": str(codes_get(message, "stream")),
                    "expver": str(codes_get(message, "expver")),
                }
                if observed is None:
                    observed = metadata
                elif metadata != observed:
                    raise ValueError(f"Inconsistent GRIB metadata within {path.name}")
            finally:
                codes_release(message)
    if observed is None or message_count != 4:
        raise ValueError(f"Expected four monthly GRIB messages in {path.name}")
    return observed


def validate(path: Path, year: int) -> dict[str, object]:
    dataset = xr.open_dataset(
        path,
        engine="cfgrib",
        backend_kwargs={"indexpath": "", "filter_by_keys": {"shortName": "tp"}},
    )
    try:
        if tuple(dataset.data_vars) != ("tp",):
            raise ValueError(f"{year}: expected total precipitation only")
        shape = (
            int(dataset.sizes["time"]),
            int(dataset.sizes["latitude"]),
            int(dataset.sizes["longitude"]),
        )
        months = tuple(str(value.astype("datetime64[M]"))[-2:] for value in dataset.time.values)
        extent = (
            float(dataset.latitude.max()),
            float(dataset.longitude.min()),
            float(dataset.latitude.min()),
            float(dataset.longitude.max()),
        )
        missing_count = int(dataset["tp"].isnull().sum().item())
    finally:
        dataset.close()

    metadata = grib_contract(path)
    if shape != EXPECTED_SHAPE or months != MONTHS:
        raise ValueError(f"{year}: unexpected grid/month contract: {shape}, {months}")
    if any(
        abs(actual - expected) > 1e-9
        for actual, expected in zip(extent, ERA5_LAND_CDS.mainland_portugal_area)
    ):
        raise ValueError(f"{year}: unexpected extent {extent}")
    if metadata["short_name"] != "tp" or metadata["units"] != "m":
        raise ValueError(f"{year}: unexpected precipitation variable or units: {metadata}")
    if metadata["stream"] != "mnth" or metadata["expver"] != "0001":
        raise ValueError(f"{year}: file is not the by-hour-of-day monthly product: {metadata}")
    if not metadata["step_range"].endswith("24"):
        raise ValueError(f"{year}: 00:00 workaround is not the 24-hour accumulation: {metadata}")
    if missing_count != 1928:
        raise ValueError(f"{year}: unexpected four-month water-mask count {missing_count}")
    return {
        "year": year,
        "shape": shape,
        "months": months,
        "extent": extent,
        "missing_count": missing_count,
        "grib_metadata": metadata,
        "sha256": checksum(path),
        "size_bytes": path.stat().st_size,
    }


def main() -> None:
    client = None
    for year in YEARS:
        destination = target_path(year)
        if destination.exists():
            facts = validate(destination, year)
            print(f"Existing immutable file validated: {destination.name} {facts}", flush=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if client is None:
            client = cdsapi.Client()
        with TemporaryDirectory(prefix=f"era5_land_precip_{year}_") as temporary_directory:
            temporary = Path(temporary_directory) / destination.name
            client.retrieve(ERA5_LAND_CDS.dataset_id, request_for_year(year), str(temporary))
            facts = validate(temporary, year)
            copyfile(temporary, destination)
        print(f"Downloaded and validated: {destination.name} {facts}", flush=True)


if __name__ == "__main__":
    main()
