"""Read-only HTTP API for the published comparative wildfire-exposure output.

The API is intentionally a presentation and lookup layer.  It does not fit a
model, score a new year, geocode addresses, or expose the separately licensed
ICNF structural-hazard raster.  It reads the published 2026 GeoPackage and the
observed historical-recurrence GeoPackage only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import geopandas as gpd
import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pyproj import Transformer
from shapely.geometry import Point

from src.operational_forecast_reporting import load_operational_forecast_spatial_artifact
from src.paths import PROJECT_ROOT
from src.web_map import WEB_MAP_GEOJSON_PATH

API_TITLE = "Portugal Wildfire Exposure Screening API"
API_VERSION = "0.1.0"
FORECAST_YEAR = 2026
HISTORICAL_PATH = PROJECT_ROOT / "data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg"
HISTORICAL_LAYER = "historical_exposure_screening"
WGS84_TO_GRID = Transformer.from_crs("EPSG:4326", "EPSG:3763", always_xy=True)
GRID_TO_WGS84 = Transformer.from_crs("EPSG:3763", "EPSG:4326", always_xy=True)
DEFAULT_BUFFERS_KM = (1.0, 3.0, 5.0)
WEB_DIRECTORY = PROJECT_ROOT / "web"


class CellEstimate(BaseModel):
    """Annual comparative estimate and historical evidence for one 1 km cell."""

    cell_id: str
    forecast_year: int
    prediction_input_year: int
    predicted_burned_share_next_year: float = Field(
        description="Continuous estimated share of the cell land area expected to burn in the forecast year; not a probability."
    )
    predicted_exposure_percentile: float = Field(
        description="National relative rank of the annual estimated burned share, from 0 to 1."
    )
    estimated_comparative_exposure_band: str
    historical_evidence_period: str
    fire_years_history_10y_2km: int
    historical_exposure_band: str


class BufferSummary(BaseModel):
    """Area-weighted descriptive summary around the requested coordinate."""

    radius_km: float
    intersecting_cell_count: int
    intersected_grid_area_sq_km: float
    mean_predicted_burned_share_next_year: float
    mean_predicted_exposure_percentile: float
    higher_estimated_exposure_area_share: float
    mean_fire_years_history_10y_2km: float


class ExposureResponse(BaseModel):
    """Read-only response for a mainland Portugal coordinate lookup."""

    api_version: str
    request_longitude: float
    request_latitude: float
    grid_x_epsg_3763: float
    grid_y_epsg_3763: float
    containing_cell: CellEstimate
    context_buffers: list[BufferSummary]
    limitations: list[str]


@dataclass(frozen=True)
class ExposureStore:
    """Validated in-memory spatial views used by the small read-only service."""

    cells: gpd.GeoDataFrame

    @classmethod
    def from_project_root(cls, project_root: Path = PROJECT_ROOT) -> "ExposureStore":
        """Load, join, and validate the two published 1 km spatial artefacts."""

        scores = load_operational_forecast_spatial_artifact(project_root, FORECAST_YEAR).scores.copy()
        historical_path = project_root / HISTORICAL_PATH.relative_to(PROJECT_ROOT)
        if not historical_path.is_file():
            raise FileNotFoundError(historical_path)
        historical = gpd.read_file(historical_path, layer=HISTORICAL_LAYER)
        required = {
            "cell_id", "history_start_year", "history_end_year", "fire_years_history_10y_2km",
            "historical_exposure_band", "geometry",
        }
        missing = required.difference(historical.columns)
        if missing:
            raise ValueError(f"Historical evidence layer is missing columns: {sorted(missing)}")
        if str(historical.crs) != "EPSG:3763" or not historical.cell_id.is_unique:
            raise ValueError("Historical evidence layer breaks the canonical 1 km spatial contract")
        historical_fields = historical.drop(columns="geometry").set_index("cell_id")
        cells = scores.join(historical_fields, on="cell_id", how="left", validate="one_to_one")
        if len(cells) != len(scores) or cells[["history_start_year", "history_end_year", "fire_years_history_10y_2km"]].isna().any().any():
            raise ValueError("Historical evidence does not cover every published annual-estimate cell")
        return cls(cells=cells)

    @classmethod
    def from_frames(cls, scores: gpd.GeoDataFrame, historical: gpd.GeoDataFrame) -> "ExposureStore":
        """Create a store from validated test/deployment frames without file I/O."""

        historical_fields = historical.drop(columns="geometry").set_index("cell_id")
        return cls(cells=scores.join(historical_fields, on="cell_id", how="left", validate="one_to_one"))

    def containing_cell(self, point: Point):
        """Return the deterministically selected canonical cell covering ``point``."""

        candidate_positions = self.cells.sindex.query(point, predicate="intersects")
        if len(candidate_positions) == 0:
            return None
        candidates = self.cells.iloc[candidate_positions]
        matches = candidates[candidates.geometry.apply(lambda geometry: geometry.covers(point))]
        if matches.empty:
            return None
        return matches.sort_values("cell_id", kind="stable").iloc[0]

    def context_summary(self, point: Point, radius_km: float) -> BufferSummary:
        """Return an intersection-area-weighted context summary around a point."""

        buffer_geometry = point.buffer(radius_km * 1_000.0)
        positions = self.cells.sindex.query(buffer_geometry, predicate="intersects")
        candidates = self.cells.iloc[positions].copy()
        intersections = candidates.geometry.intersection(buffer_geometry)
        weights = intersections.area.to_numpy(dtype="float64")
        positive = weights > 0.0
        candidates = candidates.iloc[np.flatnonzero(positive)].copy()
        weights = weights[positive]
        if candidates.empty:
            raise ValueError("A mainland point did not intersect any canonical grid cells")
        total_area = float(weights.sum())
        def weighted_mean(column: str) -> float:
            return float(np.average(candidates[column].to_numpy(dtype="float64"), weights=weights))

        higher_share = float(weights[candidates["predicted_exposure_percentile"].to_numpy(dtype="float64") > 0.80].sum() / total_area)
        return BufferSummary(
            radius_km=radius_km,
            intersecting_cell_count=int(len(candidates)),
            intersected_grid_area_sq_km=total_area / 1_000_000.0,
            mean_predicted_burned_share_next_year=weighted_mean("predicted_burned_share_next_year"),
            mean_predicted_exposure_percentile=weighted_mean("predicted_exposure_percentile"),
            higher_estimated_exposure_area_share=higher_share,
            mean_fire_years_history_10y_2km=weighted_mean("fire_years_history_10y_2km"),
        )


def _parse_buffers(value: str) -> tuple[float, ...]:
    try:
        buffers = tuple(float(item.strip()) for item in value.split(","))
    except ValueError as error:
        raise ValueError("buffers_km must be comma-separated positive numbers, for example 1,3,5") from error
    if not buffers or any(not np.isfinite(item) or item <= 0.0 or item > 10.0 for item in buffers):
        raise ValueError("buffers_km values must be finite numbers greater than 0 and no greater than 10")
    if len(set(buffers)) != len(buffers):
        raise ValueError("buffers_km values must be unique")
    return buffers


def _exposure_band(percentile: float) -> str:
    if percentile <= 0.50:
        return "Lower estimated comparative exposure percentile (0-50%)"
    if percentile <= 0.80:
        return "Intermediate estimated comparative exposure percentile (50-80%)"
    return "Higher estimated comparative exposure percentile (80-100%)"


def _store_or_503(request: Request) -> ExposureStore:
    if not hasattr(request.app.state, "exposure_store"):
        try:
            request.app.state.exposure_store = ExposureStore.from_project_root()
        except (FileNotFoundError, KeyError, ValueError) as error:
            raise HTTPException(
                status_code=503,
                detail=("Published 2026 spatial outputs are unavailable or invalid. Run the documented "
                        "reproduction workflow before starting this API."),
            ) from error
    return request.app.state.exposure_store


def create_app(store: ExposureStore | None = None) -> FastAPI:
    """Create the documented read-only API application."""

    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        description=(
            "Read-only lookup for the published 2026 mainland Portugal comparative wildfire-exposure layer. "
            "Coordinates only: address geocoding is intentionally not bundled because it requires a separate "
            "provider, privacy policy, and usage terms."
        ),
        license_info={"name": "Project code: MIT", "url": "https://github.com/serhii-diadechko-git/wildfire_property_screening_portugal/blob/main/LICENSE"},
    )
    if store is not None:
        app.state.exposure_store = store

    # The browser client is static. It calls only same-origin, read-only endpoints;
    # it cannot train, rescore, geocode, or reveal the ICNF structural-hazard layer.
    app.mount("/web", StaticFiles(directory=WEB_DIRECTORY), name="web")

    @app.get("/", include_in_schema=False)
    def web_map() -> FileResponse:
        """Serve the local 2026 comparative-exposure viewer."""

        return FileResponse(WEB_DIRECTORY / "index.html")

    @app.get(
        "/v1/map/2026/cells.geojson",
        tags=["web map"],
        summary="Return the reduced browser map asset for the published 2026 estimate.",
        responses={503: {"description": "Build the local web-map asset after reproducing outputs."}},
    )
    def web_map_cells() -> FileResponse:
        """Serve a prebuilt 2026-only map derivative without loading it into memory."""

        if not WEB_MAP_GEOJSON_PATH.is_file():
            raise HTTPException(
                status_code=503,
                detail=("The local 2026 web-map asset is unavailable. Run "
                        "python scripts/build_web_map_assets.py after the documented reproduction workflow."),
            )
        return FileResponse(WEB_MAP_GEOJSON_PATH, media_type="application/geo+json")

    @app.get("/health", tags=["service"])
    def health(request: Request) -> dict[str, str]:
        _store_or_503(request)
        return {"status": "ok", "api_version": API_VERSION}

    @app.get(
        "/v1/exposure",
        response_model=ExposureResponse,
        tags=["exposure lookup"],
        summary="Look up the containing 1 km cell and 1/3/5 km context summaries.",
        responses={404: {"description": "Coordinate is outside the canonical mainland Portugal grid."},
                   503: {"description": "Published local spatial outputs are not available."}},
    )
    def exposure(
        request: Request,
        longitude: Annotated[float, Query(ge=-31.0, le=15.0, description="WGS84 longitude in decimal degrees.")],
        latitude: Annotated[float, Query(ge=25.0, le=55.0, description="WGS84 latitude in decimal degrees.")],
        buffers_km: Annotated[str, Query(description="Comma-separated context radii in kilometres; default: 1,3,5.")] = "1,3,5",
    ) -> ExposureResponse:
        try:
            buffers = _parse_buffers(buffers_km)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        store = _store_or_503(request)
        x, y = WGS84_TO_GRID.transform(longitude, latitude)
        point = Point(x, y)
        cell = store.containing_cell(point)
        if cell is None:
            raise HTTPException(status_code=404, detail="Coordinate is outside the canonical mainland Portugal 1 km grid")
        containing = CellEstimate(
            cell_id=str(cell.cell_id),
            forecast_year=int(cell.forecast_year),
            prediction_input_year=int(cell.prediction_input_year),
            predicted_burned_share_next_year=float(cell.predicted_burned_share_next_year),
            predicted_exposure_percentile=float(cell.predicted_exposure_percentile),
            estimated_comparative_exposure_band=_exposure_band(float(cell.predicted_exposure_percentile)),
            historical_evidence_period=f"{int(cell.history_start_year)}-{int(cell.history_end_year)}",
            fire_years_history_10y_2km=int(cell.fire_years_history_10y_2km),
            historical_exposure_band=str(cell.historical_exposure_band),
        )
        return ExposureResponse(
            api_version=API_VERSION,
            request_longitude=longitude,
            request_latitude=latitude,
            grid_x_epsg_3763=x,
            grid_y_epsg_3763=y,
            containing_cell=containing,
            context_buffers=[store.context_summary(point, radius) for radius in buffers],
            limitations=[
                "Comparative screening evidence for broad 1 km cells; not a property-level forecast, safety guarantee, insurance quote, or purchase recommendation.",
                "The annual estimate is target-free for 2026 and uses 2025 predictor inputs; its observed outcome is not yet available.",
                "Buffer summaries are descriptive intersection-area-weighted summaries of published 1 km cells; they are not downscaled weather or a local site assessment.",
                "No address is stored or geocoded by this service. Convert an address to coordinates only through a separately governed geocoding provider.",
            ],
        )

    return app


app = create_app()
