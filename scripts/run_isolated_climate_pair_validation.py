"""Run the audit-approved nine-feature hurdle validation experiment only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model_v2_experiments import run_isolated_climate_pair_validation


if __name__ == "__main__":
    result = run_isolated_climate_pair_validation()
    print(
        json.dumps(
            {
                "features": result["feature_order"],
                "train_rows": result["split"]["train_rows"],
                "validation_rows": result["split"]["validation_rows"],
                "final_test_rows_read": result["split"]["final_test_rows_read"],
                "passes_gate": result["validation_gate"]["passes_gate"],
                "decision": result["validation_gate"]["decision"],
                "runtime_seconds": result["runtime_seconds"],
            },
            indent=2,
        )
    )
