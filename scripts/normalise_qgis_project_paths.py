"""Make the tracked QGIS project archives portable without changing any data layer."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.qgis_portability import normalise_qgz_paths  # noqa: E402


PROJECTS = (
    ROOT / "qgis" / "wildfire_exposure_screening_portugal.qgz",
    ROOT / "qgis" / "wildfire_exposure_screening_portugal_2026.qgz",
)


if __name__ == "__main__":
    for project in PROJECTS:
        if not project.is_file():
            raise FileNotFoundError(project)
        normalise_qgz_paths(project, ROOT)
        print(f"Normalised portable paths: {project.relative_to(ROOT).as_posix()}")
