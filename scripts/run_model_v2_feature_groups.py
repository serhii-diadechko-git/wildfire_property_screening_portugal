"""Run grouped V2 feature experiments using training/validation years only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model_v2_experiments import run_v2_feature_group_experiments


if __name__ == "__main__":
    result = run_v2_feature_group_experiments()
    print(json.dumps({"groups": list(result["groups"]), "runtime_seconds": result["runtime_seconds"],
                      "final_test_rows_read": result["split"]["final_test_rows_read"]}, indent=2))
