"""Create/reuse CAOP reference GeoPackages from the immutable CAOP ZIP."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.reference_preparation import prepare_caop_reference_layers  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(prepare_caop_reference_layers(), indent=2))
