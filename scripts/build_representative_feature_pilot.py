"""Run the controlled representative canonical feature-derivation pilot."""

from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.representative_feature_pilot import run_representative_pilot  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(run_representative_pilot(), indent=2, default=str))
