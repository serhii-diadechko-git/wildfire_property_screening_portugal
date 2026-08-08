"""Create the derived spatial QA layers referenced by the tracked QGIS projects."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.era5_coastal_fallback import ensure_spatial_qa_outputs  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(ensure_spatial_qa_outputs(), indent=2))
