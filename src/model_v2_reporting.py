"""Durable, validation-only figures for the final-model selection decision.

The inputs are the predeclared full-training hyperparameter experiment.  This
module does not fit a model and refuses to read final-test years.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from src.paths import FIGURES_DIR


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_PATH = (
    ROOT
    / "data/processed/extended_model_selection_2010_2021/hyperparameter_experiments"
    / "full_training_all_candidates/validation_metrics.json"
)
PARAMETER_COMPARISON_PATH = FIGURES_DIR / "model_v2_validation_parameter_comparison.png"
YEAR_COMPARISON_PATH = FIGURES_DIR / "model_v2_validation_v1_vs_v2_by_year.png"
V1_NAME = "current_frozen"
V2_NAME = "larger_trees"


def _atomic_save(figure: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.stem}.tmp.png")
    figure.savefig(temporary, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    os.replace(temporary, path)


def load_experiment() -> dict[str, Any]:
    """Read and validate the frozen, validation-only experiment record."""
    if not EXPERIMENT_PATH.is_file():
        raise FileNotFoundError(
            "Missing full validation experiment. Run "
            "scripts/run_hyperparameter_experiments.py --full-training --run-name full_training_all_candidates first."
        )
    result = json.loads(EXPERIMENT_PATH.read_text(encoding="utf-8"))
    scope = result["scope"]
    if scope["final_test_years_accessed"] or scope["final_test_rows_read"]:
        raise ValueError("Final-model reporting requires validation-only experiment evidence")
    if not {V1_NAME, V2_NAME}.issubset(result["candidates"]):
        raise ValueError("Experiment record lacks the v1 and selected v2 candidates")
    return result


def plot_parameter_comparison(result: dict[str, Any]) -> plt.Figure:
    """Render the five predeclared candidates on the same validation set."""
    summary = result["summary"]
    names = [row["candidate"] for row in summary]
    labels = [name.replace("_", "\n") for name in names]
    metric_specs = (
        ("mae_all", "MAE (all rows)", "Lower is better"),
        ("rmse_all", "RMSE (all rows)", "Lower is better"),
        ("positive_cell_capture_at_20_percent", "Positive-cell capture@20%", "Higher is better"),
        ("burned_share_mass_capture_at_20_percent", "Burned-share mass capture@20%", "Higher is better"),
    )
    colors = ["#9B2226" if name == V1_NAME else "#33658A" if name == V2_NAME else "#A7B5C3" for name in names]
    figure, axes = plt.subplots(2, 2, figsize=(13.2, 8.6), constrained_layout=True)
    for axis, (key, title, note) in zip(axes.flat, metric_specs):
        values = [row[key] for row in summary]
        bars = axis.bar(labels, values, color=colors, edgecolor="#35424B", linewidth=0.45)
        axis.set_title(title, fontweight="bold")
        axis.grid(axis="y", alpha=0.25)
        axis.set_axisbelow(True)
        for bar, value in zip(bars, values):
            axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.3f}", ha="center", va="bottom", fontsize=8)
        axis.text(0.5, -0.22, note, transform=axis.transAxes, ha="center", va="top", fontsize=8.5)
    figure.suptitle("Final-model selection: predeclared validation-only parameter comparison (T=2020–2021)", fontsize=15, fontweight="bold")
    figure.text(0.5, -0.02, "Red: prior candidate reference. Blue: final selected model. No T=2022–2024 row was read for this selection.", ha="center", fontsize=9)
    return figure


def build_parameter_comparison(result: dict[str, Any]) -> Path:
    """Save the durable five-candidate comparison figure."""
    figure = plot_parameter_comparison(result)
    _atomic_save(figure, PARAMETER_COMPARISON_PATH)
    return PARAMETER_COMPARISON_PATH


def plot_v1_v2_year_comparison(result: dict[str, Any]) -> plt.Figure:
    """Render temporal stability of the prior and selected configurations."""
    candidates = result["candidates"]
    years = (2020, 2021)
    metric_specs = (
        ("mae_all", "MAE (all rows)", "Lower is better"),
        ("rmse_all", "RMSE (all rows)", "Lower is better"),
        ("capture_at_20_percent", "Positive-cell capture@20%", "Higher is better"),
    )
    figure, axes = plt.subplots(1, 3, figsize=(14.6, 4.8), constrained_layout=True)
    positions = np.arange(len(years))
    width = 0.34
    for axis, (key, title, note) in zip(axes, metric_specs):
        v1 = [candidates[V1_NAME]["metrics"]["by_validation_year"][str(year)][key] for year in years]
        v2 = [candidates[V2_NAME]["metrics"]["by_validation_year"][str(year)][key] for year in years]
        axis.bar(positions - width / 2, v1, width, label="Prior candidate reference", color="#9B2226")
        axis.bar(positions + width / 2, v2, width, label="Final selected model", color="#33658A")
        axis.set_xticks(positions, [str(year) for year in years])
        axis.set_title(title, fontweight="bold")
        axis.grid(axis="y", alpha=0.25)
        axis.set_axisbelow(True)
        axis.text(0.5, -0.22, note, transform=axis.transAxes, ha="center", va="top", fontsize=8.5)
    axes[0].set_ylabel("Validation value")
    axes[-1].legend(loc="upper left", fontsize=8)
    figure.suptitle("Prior candidate versus final selected model by validation year", fontsize=15, fontweight="bold")
    figure.text(0.5, -0.02, "Both configurations use identical train/validation rows and a fixed random seed; this is not final-test evidence.", ha="center", fontsize=9)
    return figure


def build_v1_v2_year_comparison(result: dict[str, Any]) -> Path:
    """Save the durable V1-versus-V2-by-year figure."""
    figure = plot_v1_v2_year_comparison(result)
    _atomic_save(figure, YEAR_COMPARISON_PATH)
    return YEAR_COMPARISON_PATH


def build_model_v2_validation_figures() -> dict[str, str]:
    """Create both durable V2 selection figures and return relative paths."""
    result = load_experiment()
    outputs = {
        "parameter_comparison": build_parameter_comparison(result),
        "v1_v2_by_year": build_v1_v2_year_comparison(result),
    }
    for path in outputs.values():
        if not path.is_file() or path.stat().st_size < 5_000:
            raise ValueError(f"Final-model figure was not written correctly: {path}")
    return {name: path.relative_to(ROOT).as_posix() for name, path in outputs.items()}
