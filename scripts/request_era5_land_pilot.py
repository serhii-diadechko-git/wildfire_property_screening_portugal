"""Dry-run or explicitly retrieve the approved ERA5-Land 2023 pilot file."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.era5_land_cds import dry_run, retrieve_pilot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--download",
        action="store_true",
        help="Submit to CDS and write the raw file; without this flag, only validate the request.",
    )
    args = parser.parse_args()
    if args.download:
        print(retrieve_pilot(PROJECT_ROOT))
    else:
        print(dry_run(PROJECT_ROOT))


if __name__ == "__main__":
    main()
