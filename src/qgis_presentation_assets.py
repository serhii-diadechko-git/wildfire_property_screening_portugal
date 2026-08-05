"""Render readable raster annotations for QGIS layouts in headless environments.

QGIS keeps the vector maps, aliases, and layer tree.  These small transparent
PNG assets supply presentation typography because the installed headless Qt
runtime does not render layout fonts reliably.
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "qgis" / "assets"
HISTORICAL_COLORS = [("#E9D8A6", "Lower historical exposure (0–1 years)"), ("#E69F00", "Moderate historical exposure (2–3 years)"), ("#9B2226", "Higher historical exposure (4–10 years)")]
HAZARD_COLORS = [
    ("#509E2F", "Official very low structural hazard"),
    ("#FFE900", "Official low structural hazard"),
    ("#E87722", "Official medium structural hazard"),
    ("#CB333B", "Official high structural hazard"),
    ("#6F263D", "Official very high structural hazard"),
    ("#BDBDBD", "Official class unmatched"),
]


def _figure(width_mm: float, height_mm: float, dpi: int = 220):
    figure = plt.figure(figsize=(width_mm / 25.4, height_mm / 25.4), dpi=dpi)
    axis = figure.add_axes([0, 0, 1, 1])
    axis.set_xlim(0, 1); axis.set_ylim(0, 1); axis.axis("off")
    return figure, axis


def _save(figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.stem + ".tmp.png")
    figure.savefig(temporary, dpi=220, transparent=True, format="png", bbox_inches=None, pad_inches=0)
    plt.close(figure)
    os.replace(temporary, path)


def _title(path: Path, title: str, subtitle: str, width_mm: float) -> None:
    figure, axis = _figure(width_mm, 18)
    axis.text(0, 0.76, title, fontsize=15, fontweight="bold", ha="left", va="center", color="#1F1F1F")
    axis.text(0, 0.23, subtitle, fontsize=8.9, ha="left", va="center", color="#333333")
    _save(figure, path)


def _legend(path: Path, items: list[tuple[str, str]], width_mm: float, height_mm: float, *, heading: str, point_size: float = 7.2) -> None:
    figure, axis = _figure(width_mm, height_mm)
    axis.text(0.0, 0.98, heading, fontsize=point_size + 0.7, fontweight="bold", va="top", ha="left")
    start = 0.82
    step = 0.70 / len(items)
    for number, (colour, label) in enumerate(items):
        y = start - number * step
        axis.add_patch(Rectangle((0.0, y - step * 0.32), 0.12, step * 0.58, facecolor=colour, edgecolor="#555555", linewidth=0.35))
        axis.text(0.16, y, label, fontsize=point_size, ha="left", va="center", color="#222222")
    _save(figure, path)


def _scale_north(path: Path) -> None:
    figure, axis = _figure(72, 25)
    axis.text(0.92, 0.93, "N", fontsize=9, fontweight="bold", ha="center", va="top")
    axis.add_patch(Polygon([[0.92, 0.86], [0.98, 0.54], [0.92, 0.62], [0.86, 0.54]], closed=True, facecolor="#222222", edgecolor="#222222"))
    axis.add_patch(Polygon([[0.92, 0.86], [0.92, 0.62], [0.86, 0.54]], closed=True, facecolor="#F6F6F6", edgecolor="#222222", linewidth=0.5))
    x, y, width = 0.02, 0.25, 0.66
    for index in range(4):
        axis.add_patch(Rectangle((x + index * width / 4, y), width / 4, 0.16,
                                 facecolor="#222222" if index % 2 == 0 else "white", edgecolor="#222222", linewidth=0.45))
        axis.text(x + index * width / 4, y - 0.07, f"{index * 25}", fontsize=6.1, ha="center", va="top")
    axis.text(x + width, y - 0.07, "100 km", fontsize=6.1, ha="center", va="top")
    _save(figure, path)


def _footer(path: Path, width_mm: float = 277) -> None:
    figure, axis = _figure(width_mm, 22)
    axis.text(0, 0.84, "EPSG:3763 | Sources: CAOP 2025 boundary; ICNF annual burned areas; ICNF structural hazard map 2020–2030.", fontsize=6.8, ha="left", va="center")
    axis.text(0, 0.50, "1 km cells; recurrence measured in 2 km context; 2016–2025 evidence", fontsize=7.4, fontweight="bold", ha="left", va="center")
    axis.text(0, 0.16, "Historical comparative exposure only; not a next-year forecast, property-level safety guarantee, or purchase recommendation.", fontsize=7.0, ha="left", va="center", color="#8B1A1A")
    _save(figure, path)


def build_qgis_presentation_assets() -> dict[str, Path]:
    """Build exact-size transparent annotations used by the two print layouts."""
    outputs = {
        "historical_title": ASSET_DIR / "historical_layout_title.png",
        "comparison_title": ASSET_DIR / "comparison_layout_title.png",
        "historical_legend": ASSET_DIR / "historical_layout_legend.png",
        "comparison_historical_legend": ASSET_DIR / "comparison_historical_legend.png",
        "comparison_hazard_legend": ASSET_DIR / "comparison_hazard_legend.png",
        "scale_north": ASSET_DIR / "scale_north.png",
        "footer": ASSET_DIR / "layout_footer.png",
    }
    _title(outputs["historical_title"], "Historical Wildfire Exposure Screening — Mainland Portugal", "Historical exposure bands for 1 km mainland cells", 277)
    _title(outputs["comparison_title"], "Historical Exposure and Official ICNF Structural Hazard — Comparison", "Left: historical recurrence bands. Right: official ICNF structural-hazard class, summarized to 1 km cells.", 281)
    _legend(outputs["historical_legend"], HISTORICAL_COLORS, 72, 48, heading="Historical exposure", point_size=7.0)
    _legend(outputs["comparison_historical_legend"], HISTORICAL_COLORS, 132, 26, heading="Historical exposure", point_size=5.6)
    _legend(outputs["comparison_hazard_legend"], HAZARD_COLORS, 132, 26, heading="Official ICNF structural hazard", point_size=4.8)
    _scale_north(outputs["scale_north"])
    _footer(outputs["footer"])
    if any(path.stat().st_size < 1_000 for path in outputs.values()):
        raise ValueError("A QGIS presentation annotation asset was not written correctly")
    return outputs
