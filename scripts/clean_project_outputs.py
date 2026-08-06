"""List or delete only reproducible derived outputs.

Examples
--------
python scripts/clean_project_outputs.py --dry-run
python scripts/clean_project_outputs.py --confirm-delete-derived
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.output_cleanup import planned_removals, remove_derived_outputs
from src.paths import project_relative


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="List derived outputs that would be removed (default).")
    parser.add_argument(
        "--confirm-delete-derived",
        action="store_true",
        help="Required to delete the displayed derived outputs. Raw data and source files are never targets.",
    )
    args = parser.parse_args()
    if args.dry_run and args.confirm_delete_derived:
        parser.error("Choose either --dry-run or --confirm-delete-derived, not both.")
    removals = planned_removals()
    mode = "DELETE" if args.confirm_delete_derived else "DRY RUN"
    print(f"{mode}: {len(removals)} derived path(s)")
    for path in removals:
        print(f" - {project_relative(path)}")
    if not args.confirm_delete_derived:
        print("Nothing was deleted. Re-run with --confirm-delete-derived to remove only this allow-listed set.")
        return
    removed = remove_derived_outputs()
    print(f"Removed {len(removed)} derived path(s). data/raw/, source code, notebooks, QGIS projects, and tracked validation docs were preserved.")


if __name__ == "__main__":
    main()
