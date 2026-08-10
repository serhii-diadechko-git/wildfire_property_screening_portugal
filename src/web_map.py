"""Build the small, browser-ready derivative for the local 2026 web map.

The GeoPackage remains the validated spatial publication.  This module writes
only the minimum public-facing 2026 attributes and WGS84 geometry required by
the local browser viewer; it never fits, scores, or changes the model.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from collections.abc import Callable
from typing import Any

import geopandas as gpd
import pandas as pd

from src.paths import PROCESSED_DATA_DIR, PROJECT_ROOT

FORECAST_YEAR = 2026
WEB_MAP_SCHEMA_VERSION = 1
SOURCE_PATH = PROCESSED_DATA_DIR / "spatial_outputs" / "estimated_comparative_wildfire_exposure_2026.gpkg"
SOURCE_LAYER = "estimated_comparative_exposure_2026"
WEB_MAP_DIR = PROCESSED_DATA_DIR / "web_map"
WEB_MAP_GEOJSON_PATH = WEB_MAP_DIR / "estimated_comparative_wildfire_exposure_2026.geojson"
WEB_MAP_METADATA_PATH = WEB_MAP_DIR / "estimated_comparative_wildfire_exposure_2026.metadata.json"

REQUIRED_SOURCE_COLUMNS = {
    "cell_id",
    "prediction_input_year",
    "forecast_year",
    "predicted_burned_share_next_year",
    "predicted_exposure_percentile",
    "model_sha256",
    "score_status",
    "geometry",
}
PUBLIC_FIELDS = (
    "cell_id",
    "prediction_input_year",
    "forecast_year",
    "predicted_burned_share_next_year",
    "predicted_exposure_percentile",
    "estimated_comparative_exposure_band",
)


def exposure_band(percentile: float) -> tuple[str, str]:
    """Return stable display code and wording for the validated percentile bands."""

    if percentile <= 0.50:
        return "lower", "Lower estimated comparative exposure percentile (0-50%)"
    if percentile <= 0.80:
        return "intermediate", "Intermediate estimated comparative exposure percentile (50-80%)"
    return "higher", "Higher estimated comparative exposure percentile (80-100%)"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest without loading a source file into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1_048_576), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def public_web_map_frame(scores: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Validate and reduce published scores to browser-safe map attributes."""

    missing = REQUIRED_SOURCE_COLUMNS.difference(scores.columns)
    if missing:
        raise ValueError(f"2026 spatial output is missing required fields: {sorted(missing)}")
    if str(scores.crs) != "EPSG:3763":
        raise ValueError(f"2026 spatial output must be EPSG:3763, got {scores.crs}")
    if len(scores) == 0 or not scores.cell_id.is_unique:
        raise ValueError("2026 spatial output must contain unique non-empty canonical cells")
    if scores.geometry.isna().any() or scores.geometry.is_empty.any() or not scores.geometry.is_valid.all():
        raise ValueError("2026 spatial output contains null, empty, or invalid geometry")
    if scores["forecast_year"].nunique() != 1 or int(scores["forecast_year"].iloc[0]) != FORECAST_YEAR:
        raise ValueError("Web map accepts only the published 2026 annual estimate")

    percentiles = pd.to_numeric(scores["predicted_exposure_percentile"], errors="raise")
    if ((percentiles < 0.0) | (percentiles > 1.0)).any():
        raise ValueError("Predicted exposure percentiles must be in [0, 1]")
    predicted_share = pd.to_numeric(scores["predicted_burned_share_next_year"], errors="raise")
    if (predicted_share < 0.0).any():
        raise ValueError("Predicted burned shares must be non-negative")

    frame = scores.loc[:, [column for column in PUBLIC_FIELDS if column in scores.columns] + ["geometry"]].copy()
    bands = percentiles.map(exposure_band)
    frame["exposure_band_code"] = bands.map(lambda item: item[0])
    frame["estimated_comparative_exposure_band"] = bands.map(lambda item: item[1])
    # WGS84 is the web-map transport CRS.  The canonical analytical geometry remains EPSG:3763.
    return frame.to_crs("EPSG:4326")


def _write_text_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _portable_source_path(path: Path) -> str:
    """Use a repository-relative provenance path, never a machine-specific path."""

    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.name


def build_web_map_assets(
    source_path: Path = SOURCE_PATH,
    output_path: Path = WEB_MAP_GEOJSON_PATH,
    metadata_path: Path = WEB_MAP_METADATA_PATH,
    *,
    overwrite: bool = False,
    reader: Callable[..., gpd.GeoDataFrame] = gpd.read_file,
) -> dict[str, Any]:
    """Create a deterministic local-web-map GeoJSON and provenance sidecar.

    Existing current assets are reused.  A changed source requires an explicit
    ``overwrite`` acknowledgement so a user never silently replaces a local
    presentation asset.
    """

    if not source_path.is_file():
        raise FileNotFoundError(
            f"Published 2026 GeoPackage is unavailable: {source_path}. Run the reproduction workflow first."
        )
    source_sha256 = sha256_file(source_path)
    if output_path.is_file() and metadata_path.is_file():
        current = json.loads(metadata_path.read_text(encoding="utf-8"))
        if current.get("source_sha256") == source_sha256 and current.get("web_map_schema_version") == WEB_MAP_SCHEMA_VERSION:
            return {**current, "status": "reused"}
        if current.get("source_sha256") != source_sha256 and not overwrite:
            raise FileExistsError(
                "The source GeoPackage changed after the web-map asset was built. "
                "Review it, then rerun with --overwrite to publish a replacement."
            )
    elif output_path.exists() or metadata_path.exists():
        if not overwrite:
            raise FileExistsError("Incomplete web-map asset exists; rerun with --overwrite after inspection.")

    scores = reader(source_path, layer=SOURCE_LAYER)
    frame = public_web_map_frame(scores)
    # Compact JSON matters for 89,112 browser-rendered polygons.  It intentionally excludes
    # raw source fields and the separately governed ICNF structural-hazard comparison layer.
    feature_collection = json.loads(frame.to_json(drop_id=True, na="null"))
    geojson_text = json.dumps(feature_collection, ensure_ascii=False, separators=(",", ":")) + "\n"
    metadata = {
        "status": "published",
        "web_map_schema_version": WEB_MAP_SCHEMA_VERSION,
        "forecast_year": FORECAST_YEAR,
        "prediction_input_year": int(frame["prediction_input_year"].iloc[0]),
        "source_path": _portable_source_path(source_path),
        "source_layer": SOURCE_LAYER,
        "source_sha256": source_sha256,
        "feature_count": int(len(frame)),
        "transport_crs": "EPSG:4326",
        "canonical_analysis_crs": "EPSG:3763",
        "model_sha256": str(scores["model_sha256"].iloc[0]),
        "public_fields": list(PUBLIC_FIELDS) + ["exposure_band_code"],
        "purpose": "Local browser presentation of the validated 2026 comparative estimate; not a model input or source of truth.",
    }
    _write_text_atomically(output_path, geojson_text)
    _write_text_atomically(metadata_path, json.dumps(metadata, indent=2) + "\n")
    return {"status": "published", **metadata}
