"""Build the fixed annual model and validate the current forecast inputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.operational_forecast import run_current_operational_preparation


if __name__ == "__main__":
    print(json.dumps(run_current_operational_preparation(), indent=2))
