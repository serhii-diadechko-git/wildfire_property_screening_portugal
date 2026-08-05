"""Run the bounded, restartable canonical national panel build."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.national_panel import (  # noqa: E402
    assemble_national_panel,
    build_clc_batches,
    build_era_batches,
    build_grid_batches,
    build_icnf_batches,
    build_panel_batches,
    build_slope_batches,
    prepare_icnf_years,
    run_national_build,
    validate_national_panel,
    write_validation_report,
)


def validate_and_report():
    metrics = validate_national_panel()
    write_validation_report(metrics)
    return metrics


STAGES = {
    "grid": build_grid_batches,
    "icnf-repair": prepare_icnf_years,
    "slope": build_slope_batches,
    "clc": build_clc_batches,
    "era5": build_era_batches,
    "icnf-components": build_icnf_batches,
    "panel-batches": build_panel_batches,
    "assemble": assemble_national_panel,
    "validate": validate_and_report,
    "all": run_national_build,
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, default="all")
    arguments = parser.parse_args()
    result = STAGES[arguments.stage]()
    print(json.dumps(result, indent=2, default=str))
