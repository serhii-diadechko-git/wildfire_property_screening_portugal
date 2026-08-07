"""Read-only historical-screening maps and tables for explanatory notebooks.

The helpers here consume only the already validated GeoPackage and summary CSV
artefacts.  They do not rebuild recurrence, alter the GeoPackage, or create a
prediction.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch


HISTORICAL_ORDER = ("lower", "moderate", "higher")
HAZARD_ORDER = ("very_low", "low", "medium", "high", "very_high", "unmatched")
HISTORICAL_COLOURS = {"lower": "#E9D8A6", "moderate": "#E69F00", "higher": "#9B2226"}
HAZARD_COLOURS = {
    "very_low": "#509E2F",
    "low": "#FFE900",
    "medium": "#E87722",
    "high": "#CB333B",
    "very_high": "#6F263D",
    "unmatched": "#BDBDBD",
}


@dataclass(frozen=True)
class HistoricalScreeningArtifacts:
    """Validated inputs used by the historical GIS evidence notebook section."""

    screening: gpd.GeoDataFrame
    band_summary: pd.DataFrame
    hazard_summary: pd.DataFrame
    cross_matrix: pd.DataFrame


def load_historical_screening_artifacts(project_root: Path) -> HistoricalScreeningArtifacts:
    """Load and validate the completed historical-screening artefacts.

    The check deliberately verifies the fixed 2016-2025 evidence window and
    canonical 1 km geometry count.  This prevents a notebook chart from being
    silently drawn from a different layer, CRS, or historical window.
    """

    screening_path = project_root / "data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg"
    band_path = project_root / "reports/tables/historical_exposure_band_summary.csv"
    hazard_path = project_root / "reports/tables/icnf_hazard_class_summary.csv"
    cross_path = project_root / "reports/tables/historical_exposure_band_by_icnf_hazard_class.csv"
    for path in (screening_path, band_path, hazard_path, cross_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    # The GeoPackage is the common 1 km spatial reference for both map panels.
    screening = gpd.read_file(screening_path, layer="historical_exposure_screening")
    required = {
        "cell_id",
        "history_start_year",
        "history_end_year",
        "fire_years_history_10y_2km",
        "historical_exposure_band",
        "official_icnf_hazard_class",
        "geometry",
    }
    missing = required.difference(screening.columns)
    if missing:
        raise KeyError(f"Historical screening layer is missing columns: {sorted(missing)}")
    if len(screening) != 89_112 or not screening.cell_id.is_unique or str(screening.crs) != "EPSG:3763":
        raise ValueError("Historical screening GeoPackage breaks the canonical 1 km spatial contract")
    if not screening.history_start_year.eq(2016).all() or not screening.history_end_year.eq(2025).all():
        raise ValueError("Historical screening does not use the validated 2016-2025 evidence window")

    # Reindexing creates a stable, reader-friendly order even if CSV row order changes.
    band_summary = pd.read_csv(band_path).set_index("historical_exposure_band").reindex(HISTORICAL_ORDER).reset_index()
    hazard_summary = pd.read_csv(hazard_path).set_index("official_icnf_hazard_class").reindex(HAZARD_ORDER).reset_index()
    cross = pd.read_csv(cross_path)
    cross_matrix = (
        cross.pivot(index="historical_exposure_band", columns="official_icnf_hazard_class", values="cell_count")
        .reindex(index=HISTORICAL_ORDER, columns=HAZARD_ORDER, fill_value=0)
        .fillna(0)
        .astype(int)
    )
    return HistoricalScreeningArtifacts(screening, band_summary, hazard_summary, cross_matrix)


def plot_historical_and_icnf_maps(screening: gpd.GeoDataFrame):
    """Return side-by-side maps of recurrence bands and official hazard classes.

    Both maps use the same 1 km geometries.  Their different colour schemes
    represent different descriptive concepts and must not be read as an
    accuracy comparison or as a predictive map.
    """

    figure, axes = plt.subplots(1, 2, figsize=(15, 8), constrained_layout=True)
    for value in HISTORICAL_ORDER:
        screening.loc[screening.historical_exposure_band.eq(value)].plot(
            ax=axes[0], color=HISTORICAL_COLOURS[value], linewidth=0
        )
    axes[0].set_title("Observed historical exposure band\n2016-2025 recurrence in 2 km context")
    axes[0].axis("off")
    axes[0].legend(
        handles=[Patch(facecolor=HISTORICAL_COLOURS[value], label=value.title()) for value in HISTORICAL_ORDER],
        loc="lower left",
        title="Historical exposure",
    )

    for value in HAZARD_ORDER:
        screening.loc[screening.official_icnf_hazard_class.eq(value)].plot(
            ax=axes[1], color=HAZARD_COLOURS[value], linewidth=0
        )
    axes[1].set_title("Official ICNF structural hazard\npredominant valid 25 m class per 1 km cell")
    axes[1].axis("off")
    axes[1].legend(
        handles=[Patch(facecolor=HAZARD_COLOURS[value], label=value.replace("_", " ").title()) for value in HAZARD_ORDER],
        loc="lower left",
        title="Official ICNF class",
    )
    return figure


def plot_historical_icnf_crosstab(cross_matrix: pd.DataFrame):
    """Return the descriptive historical-exposure by official-hazard heatmap."""

    figure, axis = plt.subplots(figsize=(12, 5.5), constrained_layout=True)
    image = axis.imshow(cross_matrix.to_numpy(), cmap="YlOrRd")
    maximum = cross_matrix.to_numpy().max()
    # Annotated counts make the heatmap usable without requiring colour estimation.
    for row in range(cross_matrix.shape[0]):
        for column in range(cross_matrix.shape[1]):
            value = cross_matrix.iat[row, column]
            axis.text(
                column,
                row,
                f"{value:,}",
                ha="center",
                va="center",
                fontsize=10,
                color="white" if value > maximum * 0.58 else "#202020",
            )
    axis.set_xticks(range(len(HAZARD_ORDER)), [value.replace("_", " ").title() for value in HAZARD_ORDER])
    axis.set_yticks(range(len(HISTORICAL_ORDER)), [value.title() for value in HISTORICAL_ORDER])
    axis.set_xlabel("Official ICNF structural hazard class (predominant valid 25 m class per 1 km cell)")
    axis.set_ylabel("Historical exposure band (2016-2025 recurrence in 2 km context)")
    axis.set_title("Historical exposure × official ICNF structural hazard\nCell counts; descriptive comparison, not an accuracy assessment")
    colourbar = figure.colorbar(image, ax=axis, shrink=0.82)
    colourbar.set_label("1 km cells")
    return figure


def historical_screening_display_tables(artifacts: HistoricalScreeningArtifacts) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return standard pandas tables in the order used by the notebook narrative."""

    # Convert proportions only for notebook readability; the source CSV values remain numeric and unchanged.
    bands = artifacts.band_summary.assign(share_of_cells=lambda frame: frame.share_of_cells.map("{:.2%}".format))
    hazards = artifacts.hazard_summary.assign(share_of_cells=lambda frame: frame.share_of_cells.map("{:.2%}".format))
    return bands, hazards, artifacts.cross_matrix
