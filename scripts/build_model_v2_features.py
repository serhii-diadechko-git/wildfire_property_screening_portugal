"""Build bounded V2 feature extensions for train/validation experiments only."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model_v2_features import (
    assemble_v2_feature_matrix,
    build_clc_extensions,
    build_climate_extensions,
    build_icnf_extensions,
    build_terrain_extensions,
    build_v2_features,
)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--component",
        choices=("all", "icnf", "clc", "terrain", "climate", "assemble"),
        default="all",
    )
    args = parser.parse_args()
    action = {
        "all": build_v2_features,
        "icnf": build_icnf_extensions,
        "clc": build_clc_extensions,
        "terrain": build_terrain_extensions,
        "climate": build_climate_extensions,
        "assemble": assemble_v2_feature_matrix,
    }[args.component]

    def milestone_progress(message: str) -> None:
        """Keep long bounded runs observable without flooding a terminal buffer."""
        match = re.search(r"\((\d+)/(\d+)\)", message)
        if match is None:
            print(message)
            return
        number, total = (int(value) for value in match.groups())
        if number == 1 or number == total or number % 25 == 0:
            print(message)

    if args.component == "assemble":
        result = action()
    else:
        result = action(milestone_progress)
    print(json.dumps(result, indent=2))
