"""Guarded cleanup of reproducible derived outputs.

Raw downloads, credentials, source code, notebooks, QGIS projects, and tracked
validation documentation are intentionally outside this module's scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from src.paths import FIGURES_DIR, INTERIM_DATA_DIR, PROCESSED_DATA_DIR, RUN_LOGS_DIR, TABLES_DIR


@dataclass(frozen=True)
class CleanupTarget:
    """One safely constrained directory of derived files."""

    path: Path
    preserved_names: frozenset[str]


def cleanup_targets() -> tuple[CleanupTarget, ...]:
    """Return the complete, deliberately small deletion allow-list."""
    return (
        CleanupTarget(INTERIM_DATA_DIR, frozenset({".gitkeep"})),
        CleanupTarget(PROCESSED_DATA_DIR, frozenset({".gitkeep"})),
        CleanupTarget(FIGURES_DIR, frozenset({".gitkeep", "README.md"})),
        CleanupTarget(TABLES_DIR, frozenset({".gitkeep", "README.md"})),
        CleanupTarget(RUN_LOGS_DIR, frozenset({".gitkeep"})),
    )


def _within(target: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(target.resolve())
        return True
    except ValueError:
        return False


def planned_removals(targets: tuple[CleanupTarget, ...] | None = None) -> list[Path]:
    """List derived files/directories that the explicit cleanup may remove."""
    result: list[Path] = []
    for target in targets or cleanup_targets():
        if not target.path.exists():
            continue
        for child in target.path.iterdir():
            if child.name in target.preserved_names:
                continue
            if not _within(target.path, child):
                raise ValueError(f"Refusing to clean a path outside its target: {child}")
            result.append(child)
    return sorted(result, key=lambda path: (len(path.parts), path.as_posix()), reverse=True)


def remove_derived_outputs(targets: tuple[CleanupTarget, ...] | None = None) -> list[Path]:
    """Remove the allow-listed derived outputs after the caller confirms intent."""
    removals = planned_removals(targets)
    for path in removals:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    return removals
