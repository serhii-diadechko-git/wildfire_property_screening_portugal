"""Analyse ERA5-Land coastal fallback suitability without changing the panel."""

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.era5_coastal_fallback import run_analysis  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(run_analysis(), indent=2, default=str))
