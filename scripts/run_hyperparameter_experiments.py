"""Run the small validation-only hyperparameter comparison."""

from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.hyperparameter_experiments import run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full-training",
        action="store_true",
        help="Use all T=2010-2019 training rows; use only for confirmation after screening.",
    )
    parser.add_argument(
        "--candidates",
        nargs="+",
        default=None,
        help="Candidate names to compare. Defaults to the complete small screening set.",
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help="Stable output subdirectory name; defaults to a name based on training size.",
    )
    arguments = parser.parse_args()
    print(json.dumps(run(
        rows_per_year=None if arguments.full_training else 15_000,
        candidate_names=tuple(arguments.candidates) if arguments.candidates else None,
        run_name=arguments.run_name,
    ), indent=2))
