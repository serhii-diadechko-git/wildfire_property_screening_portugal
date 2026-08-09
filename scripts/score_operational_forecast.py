"""Derive and score the current annual operational wildfire-exposure estimate."""

from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.operational_forecast import (
    CURRENT_FORECAST_YEAR,
    run_operational_forecast,
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Atomically republish the score after a documented model-version update.",
    )
    arguments = parser.parse_args()
    result = run_operational_forecast(
        CURRENT_FORECAST_YEAR,
        replace_existing=arguments.replace_existing,
    )
    print(json.dumps(result, indent=2))
