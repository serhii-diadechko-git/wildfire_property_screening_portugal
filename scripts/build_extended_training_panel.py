"""Build the isolated T=2010-2021 train/validation panel in bounded batches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.extended_training_panel import (
    assemble_extended_panel,
    build_early_era_batches,
    build_early_icnf_batches,
    build_early_panel_batches,
    prepare_early_icnf_years,
    run_extended_panel_build,
    validate_extended_panel,
    write_validation_report,
)


def validate_and_report():
    metrics = validate_extended_panel()
    write_validation_report(metrics)
    return metrics


STAGES = {
    "icnf-repair": prepare_early_icnf_years,
    "icnf-components": build_early_icnf_batches,
    "era5": build_early_era_batches,
    "panel-batches": build_early_panel_batches,
    "assemble": assemble_extended_panel,
    "validate": validate_and_report,
    "all": run_extended_panel_build,
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, default="all")
    arguments = parser.parse_args()
    print(json.dumps(STAGES[arguments.stage](), indent=2, default=str))
