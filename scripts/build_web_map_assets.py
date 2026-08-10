"""Build/reuse the browser-ready 2026 comparative-exposure map asset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.web_map import build_web_map_assets


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local browser map asset from the validated 2026 GeoPackage.")
    parser.add_argument("--overwrite", action="store_true", help="Replace a derived web-map asset only when its source changed.")
    arguments = parser.parse_args()
    print(json.dumps(build_web_map_assets(overwrite=arguments.overwrite), indent=2))


if __name__ == "__main__":
    main()
