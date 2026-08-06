"""Build durable final-test model tables and figures from saved artefacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model_diagnostics import build_model_diagnostics, validate_model_diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-existing", action="store_true", help="Check diagnostics without rewriting them.")
    arguments = parser.parse_args()
    result = validate_model_diagnostics() if arguments.validate_existing else build_model_diagnostics()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
