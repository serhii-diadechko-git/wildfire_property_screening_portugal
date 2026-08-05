"""Apply the accepted ERA5-Land coastal fallback and rebuild affected panel outputs."""

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.era5_coastal_fallback import apply_fallback  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(apply_fallback(), indent=2, default=str))
