"""Build final presentation charts/tables from validated historical evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.final_visuals import build_final_visuals


if __name__ == "__main__":
    print(json.dumps(build_final_visuals(), indent=2))
