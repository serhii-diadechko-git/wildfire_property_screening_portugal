"""Refit frozen models on T=2010-2019 and validate only T=2020-2021."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.extended_model_refit import run


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
