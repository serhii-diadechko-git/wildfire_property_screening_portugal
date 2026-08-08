"""Create/reuse Portugal-clipped CLC reference layers from immutable ZIPs."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.reference_preparation import prepare_portugal_clc_layers  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(prepare_portugal_clc_layers(), indent=2))
