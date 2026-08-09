"""Deterministic writing helpers for versioned validation evidence.

Tracked validation reports describe scientific and pipeline contracts.  They
must not change solely because the same workflow was rerun on a different
machine or at a different time.  Per-run timestamps, durations, and command
output belong in the Git-ignored ``reports/run_logs`` directory instead.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def write_text_if_changed(path: Path, content: str) -> bool:
    """Atomically write *content* only when it differs from the current file.

    Returns ``True`` when a new version was published and ``False`` when the
    existing stable evidence was already identical.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return False
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary report requires inspection: {temporary}")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)
    return True


def write_json_if_changed(path: Path, payload: Any) -> bool:
    """Serialize stable JSON consistently and write it only on a real change."""
    return write_text_if_changed(path, json.dumps(payload, indent=2) + "\n")
