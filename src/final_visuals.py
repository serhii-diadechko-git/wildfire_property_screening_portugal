"""Create presentation figures from the validated historical screening evidence.

The figures deliberately use only the completed descriptive screening and the
recorded development-validation model-evaluation record. They do not calculate a new
score, prediction, or recommendation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.paths import FIGURES_DIR, TABLES_DIR, VALIDATION_DIR


ROOT = Path(__file__).resolve().parents[1]
SCREENING_METRICS_PATH = VALIDATION_DIR / "historical_exposure_screening_and_icnf_comparison.json"
MODEL_EVALUATION_PATH = ROOT / "data/processed/extended_model_selection_2010_2021/metrics.json"
BAND_TABLE_PATH = TABLES_DIR / "historical_exposure_band_summary.csv"
HAZARD_TABLE_PATH = TABLES_DIR / "icnf_hazard_class_summary.csv"
CROSSTAB_TABLE_PATH = TABLES_DIR / "historical_exposure_band_by_icnf_hazard_class.csv"

HISTORICAL_BAND_ORDER = ["lower", "moderate", "higher"]
HAZARD_ORDER = ["very_low", "low", "medium", "high", "very_high", "unmatched"]
HISTORICAL_COLORS = {"lower": "#E9D8A6", "moderate": "#E69F00", "higher": "#9B2226"}
HAZARD_COLORS = {
    "very_low": "#509E2F",
    "low": "#FFE900",
    "medium": "#E87722",
    "high": "#CB333B",
    "very_high": "#6F263D",
    "unmatched": "#BDBDBD",
}

FIGURE_PATHS = {
    "crosstab": FIGURES_DIR / "historical_exposure_by_icnf_structural_hazard_crosstab.png",
    "model_comparison": FIGURES_DIR / "validation_baseline_vs_tested_models.png",
    "decision_limitations": FIGURES_DIR / "historical_exposure_screening_decision_limitations.png",
    "summary_table": FIGURES_DIR / "historical_exposure_screening_summary_table.png",
}

QGIS_FIGURE_PATHS = {
    "historical_exposure_map": FIGURES_DIR / "historical_wildfire_exposure_screening_mainland_portugal.png",
    "historical_icnf_comparison_map": FIGURES_DIR / "historical_exposure_and_official_icnf_structural_hazard_comparison.png",
}

FIGURE_SOURCE_PATHS = {
    "historical_exposure_map": (
        "data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg",
        "scripts/build_qgis_presentation_project.py",
    ),
    "historical_icnf_comparison_map": (
        "data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg",
        "scripts/build_qgis_presentation_project.py",
    ),
    "crosstab": (
        "reports/tables/historical_exposure_band_by_icnf_hazard_class.csv",
        "src/final_visuals.py",
    ),
    "model_comparison": (
        "data/processed/extended_model_selection_2010_2021/metrics.json",
        "src/final_visuals.py",
    ),
    "decision_limitations": (
        "reports/validation/historical_exposure_screening_and_icnf_comparison.json",
        "src/final_visuals.py",
    ),
    "summary_table": (
        "reports/tables/historical_exposure_band_summary.csv and reports/tables/historical_exposure_band_by_icnf_hazard_class.csv",
        "src/final_visuals.py",
    ),
}

QGIS_VALIDATION_PATH = VALIDATION_DIR / "qgis_presentation_project_validation.json"


def _atomic_savefig(figure: plt.Figure, path: Path, *, dpi: int = 180) -> None:
    """Save a figure without leaving a partially written presentation asset."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.stem + ".tmp.png")
    figure.savefig(temporary, dpi=dpi, bbox_inches="tight", facecolor="white", format="png")
    plt.close(figure)
    os.replace(temporary, path)


def _inputs() -> tuple[dict[str, object], dict[str, object], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    screening = json.loads(SCREENING_METRICS_PATH.read_text(encoding="utf-8"))
    model_selection = json.loads(MODEL_EVALUATION_PATH.read_text(encoding="utf-8"))
    bands = pd.read_csv(BAND_TABLE_PATH)
    hazards = pd.read_csv(HAZARD_TABLE_PATH)
    cross = pd.read_csv(CROSSTAB_TABLE_PATH)
    return screening, model_selection, bands, hazards, cross


def _label(value: str) -> str:
    return value.replace("_", " ").title()


def build_crosstab_figure(cross: pd.DataFrame) -> Path:
    """Render the validated descriptive cross-tab without treating it as accuracy."""
    matrix = (
        cross.pivot(index="historical_exposure_band", columns="official_icnf_hazard_class", values="cell_count")
        .reindex(index=HISTORICAL_BAND_ORDER, columns=HAZARD_ORDER, fill_value=0)
        .fillna(0)
        .astype(int)
    )
    fig, axis = plt.subplots(figsize=(12.0, 5.5), constrained_layout=True)
    image = axis.imshow(matrix.to_numpy(), cmap="YlOrRd")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = matrix.iat[row, column]
            axis.text(column, row, f"{value:,}", ha="center", va="center", fontsize=10,
                      color="white" if value > matrix.to_numpy().max() * 0.58 else "#202020")
    axis.set_xticks(range(len(HAZARD_ORDER)), [_label(item) for item in HAZARD_ORDER])
    axis.set_yticks(range(len(HISTORICAL_BAND_ORDER)), [_label(item) for item in HISTORICAL_BAND_ORDER])
    axis.set_xlabel("Official ICNF structural hazard class (predominant valid 25 m class per 1 km cell)")
    axis.set_ylabel("Historical exposure band (2016–2025 recurrence in 2 km context)")
    axis.set_title("Historical exposure × official ICNF structural hazard\nCell counts; descriptive comparison, not an accuracy assessment")
    colourbar = fig.colorbar(image, ax=axis, shrink=0.82)
    colourbar.set_label("1 km cells")
    return _save_and_return(fig, FIGURE_PATHS["crosstab"])


def _save_and_return(figure: plt.Figure, path: Path) -> Path:
    _atomic_savefig(figure, path)
    return path


def build_model_comparison_figure(model_selection: dict[str, object]) -> Path:
    """Show validation evidence for the selected model and transparent comparator."""
    metrics = model_selection["metrics"]
    keys = ["historical_recurrence_baseline", "nine_feature_hurdle"]
    labels = ["Historical\nrecurrence", "Selected Model v2\nnine-feature regression"]
    maes = [metrics[key]["overall"]["mae_all"] for key in keys]
    rmses = [metrics[key]["overall"]["rmse_all"] for key in keys]
    captures = [metrics[key]["overall"]["capture_at_20_percent"] for key in keys]
    colours = ["#9B2226", "#33658A"]

    fig, axes = plt.subplots(1, 3, figsize=(14.5, 5.2), constrained_layout=True)
    for axis, values, metric, note in zip(
        axes,
        (maes, rmses, captures),
        ("MAE (all rows)", "RMSE (all rows)", "Capture@20% (positive targets)"),
        ("Lower is better", "Lower is better", "Higher is better"),
    ):
        bars = axis.bar(labels, values, color=colours, edgecolor="#333333", linewidth=0.45)
        axis.set_title(metric)
        axis.set_ylabel(metric)
        axis.grid(axis="y", alpha=0.25)
        axis.set_axisbelow(True)
        for bar, value in zip(bars, values):
            axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.3f}",
                      ha="center", va="bottom", fontsize=9)
        axis.text(0.5, -0.22, note, ha="center", va="top", transform=axis.transAxes, fontsize=8.5)
    fig.suptitle("Development validation comparison (T=2020–2021)", fontsize=15, fontweight="bold")
    fig.text(
        0.5,
        -0.05,
        "The validation-selected Model v2 two-stage regression is compared with the transparent historical-recurrence baseline. "
        "This supports cautious annual comparative estimates; historical recurrence remains descriptive context.",
        ha="center", va="top", fontsize=9.5,
    )
    return _save_and_return(fig, FIGURE_PATHS["model_comparison"])


def build_decision_limitations_figure() -> Path:
    """Render a compact boundaries-of-use diagram for presentation."""
    fig, axis = plt.subplots(figsize=(13.5, 5.4), constrained_layout=True)
    axis.set_axis_off()
    nodes = [
        (0.05, 0.55, 0.22, 0.25, "Validated ICNF burned-area\nevidence, 2016–2025", "#DCEAF7"),
        (0.39, 0.55, 0.22, 0.25, "1 km mainland cells\nrecurrence in 2 km context", "#F6E8C3"),
        (0.73, 0.55, 0.22, 0.25, "Lower / moderate / higher\nhistorical exposure bands", "#F4CCCC"),
    ]
    for x, y, width, height, text, colour in nodes:
        axis.text(x + width / 2, y + height / 2, text, ha="center", va="center", fontsize=11,
                  bbox={"boxstyle": "round,pad=0.65", "facecolor": colour, "edgecolor": "#444444", "linewidth": 1.0})
    for start, end in ((0.28, 0.38), (0.62, 0.72)):
        axis.annotate("", xy=(end, 0.675), xytext=(start, 0.675),
                      arrowprops={"arrowstyle": "->", "lw": 1.8, "color": "#444444"})
    axis.text(0.5, 0.30, "Use: broad location comparison and shortlisting; compare separately with the official ICNF structural-hazard map.",
              ha="center", va="center", fontsize=11, fontweight="bold", color="#333333")
    axis.text(
        0.5,
        0.13,
        "Not a next-year forecast, property-level safety guarantee, wildfire-risk probability, or purchase recommendation.",
        ha="center", va="center", fontsize=11, color="#8B1A1A",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "#FCE8E6", "edgecolor": "#C5221F"},
    )
    axis.set_title("Historical wildfire-exposure screening: evidence, use, and limitations", fontsize=15, fontweight="bold", pad=16)
    return _save_and_return(fig, FIGURE_PATHS["decision_limitations"])


def build_summary_table_figure(bands: pd.DataFrame, cross: pd.DataFrame) -> Path:
    """Render a readable summary table from the validated distribution and cross-tab."""
    distribution = bands.set_index("historical_exposure_band").reindex(HISTORICAL_BAND_ORDER)
    selected = [
        ("Higher historical exposure × very high official class", "higher", "very_high"),
        ("Higher historical exposure × very low official class", "higher", "very_low"),
        ("Lower historical exposure × very high official class", "lower", "very_high"),
    ]
    cross_lookup = cross.set_index(["historical_exposure_band", "official_icnf_hazard_class"])["cell_count"]
    rows = [[_label(band), f"{int(distribution.loc[band, 'cell_count']):,}",
             f"{distribution.loc[band, 'share_of_cells']:.2%}"] for band in HISTORICAL_BAND_ORDER]
    selected_rows = [[title, f"{int(cross_lookup.loc[(band, hazard)]):,}"] for title, band, hazard in selected]

    fig, axes = plt.subplots(2, 1, figsize=(12.5, 6.6), gridspec_kw={"height_ratios": [1.0, 1.2]}, constrained_layout=True)
    for axis in axes:
        axis.set_axis_off()
    table_one = axes[0].table(cellText=rows, colLabels=["Historical exposure band", "1 km cells", "Share of mainland cells"],
                              cellLoc="left", colLoc="left", loc="center", colWidths=[0.45, 0.22, 0.25])
    table_two = axes[1].table(cellText=selected_rows, colLabels=["Selected descriptive cross-tab combination", "1 km cells"],
                              cellLoc="left", colLoc="left", loc="center", colWidths=[0.72, 0.2])
    for table in (table_one, table_two):
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.55)
        for (row, _), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor("#2F4F4F")
                cell.get_text().set_color("white")
                cell.get_text().set_weight("bold")
            else:
                cell.set_edgecolor("#D0D0D0")
    axes[0].set_title("Historical exposure-band distribution (2016–2025 evidence)", loc="left", fontweight="bold", pad=8)
    axes[1].set_title("Selected agreement / disagreement findings — descriptive only, not an accuracy assessment", loc="left", fontweight="bold", pad=8)
    fig.suptitle("Mainland Portugal historical wildfire-exposure screening summary", fontsize=15, fontweight="bold")
    return _save_and_return(fig, FIGURE_PATHS["summary_table"])


def build_final_visuals() -> dict[str, str]:
    """Build all non-map presentation figures and return repository-relative paths."""
    screening, model_selection, bands, _hazards, cross = _inputs()
    if not screening.get("no_predictive_claim"):
        raise ValueError("Historical screening evidence does not satisfy the non-predictive contract")
    outputs = {
        "historical_exposure_by_icnf_structural_hazard_crosstab": build_crosstab_figure(cross),
        "validation_baseline_vs_tested_models": build_model_comparison_figure(model_selection),
        "historical_exposure_decision_limitations": build_decision_limitations_figure(),
        "historical_exposure_summary_table": build_summary_table_figure(bands, cross),
    }
    validation = {}
    for name, path in outputs.items():
        if not path.exists() or path.stat().st_size < 5_000:
            raise ValueError(f"Presentation figure was not written correctly: {path}")
        validation[name] = {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size}
    return {name: record["path"] for name, record in validation.items()}


def validate_final_visuals() -> dict[str, object]:
    """Verify every existing presentation figure against validated source artefacts.

    This function is intentionally read-only. It validates the stable paths and
    the source-data contracts used by the figures without rewriting any image.
    """
    screening, model_selection, bands, hazards, cross = _inputs()
    qgis_validation = json.loads(QGIS_VALIDATION_PATH.read_text(encoding="utf-8"))

    if not screening.get("no_predictive_claim"):
        raise ValueError("Historical screening evidence does not satisfy the non-predictive contract")
    evidence = screening["evidence_snapshot"]
    if (evidence["history_start_year"], evidence["history_end_year"]) != (2016, 2025):
        raise ValueError("Historical evidence window changed")
    if int(bands.cell_count.sum()) != 89_112 or int(hazards.cell_count.sum()) != 89_112:
        raise ValueError("Screening summary tables no longer cover all canonical cells")
    if int(cross.cell_count.sum()) != 89_112:
        raise ValueError("Historical/ICNF cross-tab no longer covers all canonical cells")
    design = model_selection["design"]
    if tuple(design["train_years"]) != tuple(range(2010, 2020)) or tuple(design["validation_years"]) != (2020, 2021):
        raise ValueError("Development-validation years changed")
    if design["final_test_years_accessed"] or design["final_test_rows_read"]:
        raise ValueError("Validation comparison unexpectedly accessed final-test years")
    if set(model_selection["metrics"]) != {"historical_recurrence_baseline", "nine_feature_hurdle"}:
        raise ValueError("Final model-comparison candidates changed")
    if qgis_validation["screening_view_feature_count"] != 89_112:
        raise ValueError("QGIS validation no longer resolves all screening cells")

    # The four Matplotlib figures are the portable final-chart contract.  The
    # two QGIS layout exports are optional presentation copies: the QGIS
    # projects embed their layouts and remain useful without exported PNGs.
    records: dict[str, dict[str, object]] = {}
    for name, path in FIGURE_PATHS.items():
        if not path.exists() or path.stat().st_size < 5_000:
            raise ValueError(f"Missing or incomplete presentation figure: {path}")
        image = plt.imread(path)
        if image.ndim not in (2, 3) or min(image.shape[:2]) < 500:
            raise ValueError(f"Presentation figure has an unexpected image shape: {path} {image.shape}")
        source_data, source_code = FIGURE_SOURCE_PATHS[name]
        records[name] = {
            "path": path.relative_to(ROOT).as_posix(),
            "source_data": source_data,
            "source_code": source_code,
            "bytes": path.stat().st_size,
            "pixel_height": int(image.shape[0]),
            "pixel_width": int(image.shape[1]),
            "status": "verified_existing",
        }

    optional_qgis_records: dict[str, dict[str, object]] = {}
    available_qgis_maps = {
        name: path for name, path in QGIS_FIGURE_PATHS.items() if path.is_file()
    }
    if available_qgis_maps and len(available_qgis_maps) != len(QGIS_FIGURE_PATHS):
        raise ValueError("QGIS map exports must be either absent or present as a complete pair")
    for name, path in available_qgis_maps.items():
        if path.stat().st_size < 5_000:
            raise ValueError(f"Missing or incomplete optional QGIS presentation figure: {path}")
        image = plt.imread(path)
        if image.ndim not in (2, 3) or min(image.shape[:2]) < 500:
            raise ValueError(f"Optional QGIS presentation figure has an unexpected image shape: {path} {image.shape}")
        source_data, source_code = FIGURE_SOURCE_PATHS[name]
        optional_qgis_records[name] = {
            "path": path.relative_to(ROOT).as_posix(),
            "source_data": source_data,
            "source_code": source_code,
            "bytes": path.stat().st_size,
            "pixel_height": int(image.shape[0]),
            "pixel_width": int(image.shape[1]),
            "status": "verified_existing_optional",
        }

    return {
        "figure_count": len(records),
        "optional_qgis_figure_count": len(optional_qgis_records),
        "history_window": "2016-2025",
        "canonical_cell_count": 89_112,
        "figures": records,
        "optional_qgis_figures": optional_qgis_records,
        "images_rewritten": False,
    }
