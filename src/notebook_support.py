"""Small, reusable helpers for the explanatory notebook layer.

Notebooks use these helpers to locate a cloned repository and to fail with a
clear message when a required generated artifact is absent.  They deliberately
do not contain national processing logic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def resolve_project_root(start: str | Path | None = None) -> Path:
    """Resolve the repository root from a notebook working directory."""
    current = Path.cwd() if start is None else Path(start)
    current = current.resolve()
    candidates = (current, *current.parents)
    for candidate in candidates:
        if (candidate / "src").is_dir() and (candidate / "notebooks").is_dir() and (candidate / "README.md").is_file():
            return candidate
    raise FileNotFoundError("Could not locate the repository root from the current notebook directory")


def require_artifacts(root: Path, paths: Iterable[str | Path]) -> list[Path]:
    """Return required artifact paths or raise one actionable error."""
    resolved = [root / Path(path) for path in paths]
    missing = [path.relative_to(root).as_posix() for path in resolved if not path.exists()]
    if missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(
            f"Missing generated artifact(s): {joined}. Run the documented project preflight and reproduction command first."
        )
    return resolved


def read_json_artifact(root: Path, relative_path: str | Path) -> dict[str, object]:
    """Load a project JSON artifact after confirming that it exists."""
    path = require_artifacts(root, [relative_path])[0]
    return json.loads(path.read_text(encoding="utf-8"))


def relative_display_path(root: Path, path: Path) -> str:
    """Show a portable repository-relative path in notebook output."""
    return path.resolve().relative_to(root.resolve()).as_posix()
