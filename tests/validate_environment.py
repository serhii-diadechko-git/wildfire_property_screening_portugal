"""Validate requirements, imports, repository references, and notebook execution."""

from __future__ import annotations

from importlib import import_module, metadata
from pathlib import Path
import re
import sys

import nbformat
from nbclient import NotebookClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
TEST_NOTEBOOK = PROJECT_ROOT / "notebooks" / "00_environment_test.ipynb"

IMPORT_NAMES = {
    "numpy": "numpy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "scikit-learn": "sklearn",
    "geopandas": "geopandas",
    "shapely": "shapely",
    "pyproj": "pyproj",
    "pyogrio": "pyogrio",
    "rasterio": "rasterio",
    "requests": "requests",
    "ipykernel": "ipykernel",
    "nbformat": "nbformat",
    "nbclient": "nbclient",
}


def parse_requirements() -> dict[str, str]:
    result: dict[str, str] = {}
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s]+)", line)
        if not match:
            raise AssertionError(f"Requirement is not exactly pinned: {line}")
        result[match.group(1)] = match.group(2)
    return result


def validate_packages(requirements: dict[str, str]) -> None:
    assert set(requirements) == set(IMPORT_NAMES), "Requirements/import mapping is incomplete."
    for package, expected in requirements.items():
        import_module(IMPORT_NAMES[package])
        installed = metadata.version(package)
        if installed != expected:
            raise AssertionError(f"{package}: expected {expected}, installed {installed}")
        print(f"OK package: {package}=={installed}")


def validate_project_references() -> None:
    required_paths = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "docs" / "project_brief.md",
        PROJECT_ROOT / "docs" / "data_dictionary.md",
        PROJECT_ROOT / "docs" / "source_plan.md",
        PROJECT_ROOT / "docs" / "success_criteria.md",
        PROJECT_ROOT / "docs" / "task_list.md",
        PROJECT_ROOT / "src" / "config.py",
        PROJECT_ROOT / "src" / "paths.py",
    ]
    for path in required_paths:
        if not path.exists():
            raise AssertionError(f"Missing project file: {path}")
        print(f"OK file: {path.relative_to(PROJECT_ROOT)}")


def execute_test_notebook() -> None:
    notebook = nbformat.read(TEST_NOTEBOOK, as_version=4)
    client = NotebookClient(notebook, timeout=120, kernel_name="python3", resources={"metadata": {"path": str(PROJECT_ROOT)}})
    client.execute()
    nbformat.write(notebook, TEST_NOTEBOOK)
    print(f"OK notebook: {TEST_NOTEBOOK.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    try:
        requirements = parse_requirements()
        validate_packages(requirements)
        validate_project_references()
        execute_test_notebook()
    except Exception as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        raise
    print("ALL ENVIRONMENT AND NOTEBOOK CHECKS PASSED")
