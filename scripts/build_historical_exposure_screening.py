"""Build or validate the non-predictive historical exposure screening layer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.historical_exposure_screening import run_historical_exposure_screening


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate-existing",
        action="store_true",
        help="Do not overwrite; recompute all analytical batches and compare with the existing output.",
    )
    args = parser.parse_args()
    metrics = run_historical_exposure_screening(validate_existing=args.validate_existing)
    print(json.dumps({
        "features": metrics["output_validation"]["feature_count"],
        "history": metrics["evidence_snapshot"],
        "thresholds": metrics["thresholds"],
        "unmatched_hazard_cells": metrics["official_hazard_unmatched_cells"],
        "no_predictive_claim": metrics["no_predictive_claim"],
    }, indent=2))


if __name__ == "__main__":
    main()

