"""Dry-run or retrieve one annual ERA5-Land JJAS source file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.era5_land_cds import dry_run, retrieve  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=int)
    parser.add_argument("--corrected-precipitation", action="store_true")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    result = dry_run(ROOT, args.year, corrected_precipitation=args.corrected_precipitation)
    print(json.dumps(result, indent=2))
    if args.download:
        target = retrieve(ROOT, args.year, corrected_precipitation=args.corrected_precipitation)
        print(f"Downloaded immutable raw GRIB: {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
