"""Derive and score the current annual operational wildfire-exposure estimate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.operational_forecast import (
    CURRENT_FORECAST_YEAR,
    run_operational_forecast,
)


if __name__ == "__main__":
    result = run_operational_forecast(CURRENT_FORECAST_YEAR)
    print(json.dumps(result, indent=2))
