"""Run the protocol-frozen T=2022-2024 final temporal comparison once."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.extended_final_test import run


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
