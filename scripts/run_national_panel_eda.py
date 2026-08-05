"""Run bounded descriptive EDA for the validated national panel."""

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.panel_eda import run_panel_eda  # noqa: E402


if __name__ == "__main__":
    result = run_panel_eda()
    print(json.dumps({
        "row_count": result["row_count"],
        "split_row_counts": result["split_row_counts"],
        "overall_zero_proportion": result["target"]["overall_zero_proportion"],
        "high_redundancy_pairs": result["high_redundancy_pairs_abs_ge_0_8"],
        "decision": result["model_design_decision"],
    }, indent=2))
