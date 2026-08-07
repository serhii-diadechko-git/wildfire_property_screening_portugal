"""Read-only map helpers for the completed annual comparative estimate.

These helpers consume the scored GeoPackage created by the operational scoring
pipeline.  They do not fit a model, score new data, or alter the GeoPackage.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd


@dataclass(frozen=True)
class OperationalForecastSpatialArtifact:
    """Validated 1 km spatial output for one completed forecast year."""

    scores: gpd.GeoDataFrame
    path: Path


def load_operational_forecast_spatial_artifact(
    project_root: Path, forecast_year: int = 2026
) -> OperationalForecastSpatialArtifact:
    """Load and validate the annual target-free comparative-estimate layer.

    The checks keep the explanatory notebook tied to the canonical 1 km grid
    and make the input-year-to-estimate-year relationship explicit.  No future
    observed outcome is expected or accepted in this output.
    """

    path = (
        project_root
        / "data/processed/spatial_outputs"
        / f"estimated_comparative_wildfire_exposure_{forecast_year}.gpkg"
    )
    if not path.is_file():
        raise FileNotFoundError(path)

    layer = f"estimated_comparative_exposure_{forecast_year}"
    scores = gpd.read_file(path, layer=layer)
    required = {
        "cell_id",
        "prediction_input_year",
        "forecast_year",
        "predicted_burned_share_next_year",
        "predicted_exposure_percentile",
        "score_status",
        "geometry",
    }
    missing = required.difference(scores.columns)
    if missing:
        raise KeyError(f"Operational estimate layer is missing columns: {sorted(missing)}")
    if len(scores) != 89_112 or not scores.cell_id.is_unique or str(scores.crs) != "EPSG:3763":
        raise ValueError("Operational estimate GeoPackage breaks the canonical 1 km spatial contract")
    if not scores.forecast_year.eq(forecast_year).all() or not scores.prediction_input_year.eq(forecast_year - 1).all():
        raise ValueError("Operational estimate does not have the expected input-year-to-estimate-year alignment")
    if not scores.score_status.eq("scored_comparative_estimate").all():
        raise ValueError("Operational estimate has an unexpected score status")

    for column in ("predicted_burned_share_next_year", "predicted_exposure_percentile"):
        if scores[column].isna().any() or not scores[column].between(0.0, 1.0).all():
            raise ValueError(f"Operational estimate {column} must be complete and within [0, 1]")
    return OperationalForecastSpatialArtifact(scores=scores, path=path)
