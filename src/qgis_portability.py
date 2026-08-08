"""Small, dependency-free helpers for portable QGIS project archives."""

from __future__ import annotations

import os
from pathlib import Path
import re
import zipfile


def normalise_qgz_paths(project_path: Path, project_root: Path) -> None:
    """Replace machine-specific project-root references with QGIS-relative paths.

    QGIS can retain absolute layer references inside layout map settings even
    after active layers have been made relative.  The project itself lives in
    ``qgis/``, so ``../data/...`` is the stable portable reference.
    """
    temporary = project_path.with_suffix(".qgz.tmp")
    root_forward = project_root.as_posix() + "/"
    root_windows = str(project_root).replace("\\", "/") + "/"
    root_backslash = str(project_root) + "\\"

    with zipfile.ZipFile(project_path, "r") as source, zipfile.ZipFile(
        temporary, "w", zipfile.ZIP_DEFLATED
    ) as target:
        for entry in source.infolist():
            payload = source.read(entry.filename)
            if entry.filename.endswith(".qgs"):
                text = payload.decode("utf-8")
                text = text.replace(root_forward, "../")
                text = text.replace(root_windows, "../")
                text = text.replace(root_backslash, "../")
                text = re.sub(r'<homePath path="[^"]*"/>', '<homePath path="."/>', text)
                text = re.sub(r'\s+saveUser(?:Full)?="[^"]*"', "", text)
                payload = text.encode("utf-8")
            target.writestr(entry, payload)
    os.replace(temporary, project_path)
