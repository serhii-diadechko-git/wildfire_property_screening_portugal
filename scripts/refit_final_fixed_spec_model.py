"""Refit the post-evaluation fixed nine-feature model on T=2010-2021 only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.final_model_refit import refit


if __name__ == "__main__":
    print(json.dumps(refit(), indent=2))
