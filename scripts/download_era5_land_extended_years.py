"""Acquire the immutable ERA5-Land JJAS GRIBs reported missing by preflight.

This is an explicit acquisition step.  It is intentionally separate from
``run_project.py --mode preflight``: preflight checks local readiness, while
this command uses the user's existing CDS credentials to retrieve only missing
annual files and validates each file before continuing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.era5_land_cds import build_request, output_path, retrieve  # noqa: E402
from src.era5_land_validation import (  # noqa: E402
    calculate_sha256,
    validate_extended_training_era5_grib,
)


YEARS = tuple(range(2010, 2026))
CORRECTED_PRECIPITATION_YEARS = (2022, 2023)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download",
        action="store_true",
        help="retrieve missing files through CDS; without this flag only print the requests",
    )
    parser.add_argument(
        "--include-corrected-precipitation",
        action="store_true",
        help="also retrieve the corrected precipitation-only 2022 and 2023 files",
    )
    args = parser.parse_args()

    if not args.download:
        for year in YEARS:
            print(json.dumps({"year": year, "request": build_request(year), "target": str(output_path(ROOT, year))}))
        if args.include_corrected_precipitation:
            for year in CORRECTED_PRECIPITATION_YEARS:
                print(json.dumps({"year": year, "corrected_precipitation": True, "request": build_request(year, corrected_precipitation=True), "target": str(output_path(ROOT, year, corrected_precipitation=True))}))
        print("Dry run only. Add --download to retrieve missing immutable GRIBs.")
        return

    for year in YEARS:
        target = output_path(ROOT, year)
        if target.exists():
            if year < 2015:
                facts = validate_extended_training_era5_grib(target, year)
                print(json.dumps({"status": "already_present_validated", **facts}, indent=2), flush=True)
            else:
                print(json.dumps({"status": "already_present_not_overwritten", "year": year, "path": str(target.relative_to(ROOT)), "bytes": target.stat().st_size, "sha256": calculate_sha256(target)}, indent=2), flush=True)
            continue
        retrieved = retrieve(ROOT, year)
        if year < 2015:
            facts = validate_extended_training_era5_grib(retrieved, year)
            print(json.dumps(facts, indent=2), flush=True)
        else:
            print(json.dumps({"status": "downloaded_not_overwritten", "year": year, "path": str(retrieved.relative_to(ROOT)), "bytes": retrieved.stat().st_size, "sha256": calculate_sha256(retrieved)}, indent=2), flush=True)
    if args.include_corrected_precipitation:
        for year in CORRECTED_PRECIPITATION_YEARS:
            target = output_path(ROOT, year, corrected_precipitation=True)
            if target.exists():
                print(json.dumps({"status": "already_present_not_overwritten", "path": str(target.relative_to(ROOT)), "bytes": target.stat().st_size}, indent=2), flush=True)
                continue
            retrieved = retrieve(ROOT, year, corrected_precipitation=True)
            print(json.dumps({"year": year, "corrected_precipitation": True, "path": str(retrieved.relative_to(ROOT)), "bytes": retrieved.stat().st_size}, indent=2), flush=True)


if __name__ == "__main__":
    main()
