"""Build durable figures for the validation-selected final-model decision."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model_v2_reporting import build_model_v2_validation_figures


if __name__ == "__main__":
    print(json.dumps(build_model_v2_validation_figures(), indent=2))
