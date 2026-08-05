"""Run the bounded train/validation-only regression model-selection gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.model_selection import run_model_selection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = run_model_selection()
    print(
        json.dumps(
            {
                "train_rows": result["contract_validation"]["train_rows"],
                "validation_rows": result["contract_validation"]["validation_rows"],
                "final_test_rows_read": result["row_group_access"]["final_test_rows_read"],
                "provisional_model": result["selection"]["provisional_model"],
                "final_temporal_test_may_begin": result["selection"]["final_temporal_test_may_begin"],
                "runtime_seconds": result["runtime_seconds"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

