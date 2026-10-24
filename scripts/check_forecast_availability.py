"""Audit a proposed annual issue without publishing or modifying data."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.forecast_availability import check_availability
from src.paths import PROJECT_ROOT

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    result = check_availability(json.loads(args.manifest.read_text(encoding="utf-8")),
                                PROJECT_ROOT, datetime.now(timezone.utc))
    print(json.dumps(result, indent=2))
    sys.exit(1 if result["status"] == "blocked" else 0)
