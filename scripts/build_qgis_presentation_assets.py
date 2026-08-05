"""Build text/legend assets used by the portable QGIS presentation project."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.qgis_presentation_assets import build_qgis_presentation_assets


if __name__ == "__main__":
    for name, path in build_qgis_presentation_assets().items():
        print(f"{name}: {path.relative_to(ROOT).as_posix()}")
