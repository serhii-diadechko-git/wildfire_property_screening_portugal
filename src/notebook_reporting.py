"""Read-only tables and figures for the explanatory notebook layer.

These helpers deliberately consume recorded model artefacts and prediction
tables.  They do not fit, tune, score, or write models, data, or figures.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def model_comparison_frame(metrics: Mapping[str, object]) -> pd.DataFrame:
    """Return the recorded overall final-test metrics in presentation order."""

    rows: list[dict[str, object]] = []
    for name, values in dict(metrics["metrics"]).items():
        overall = dict(values)["overall"]
        rows.append(
            {
                "model": str(name),
                "rows": int(overall["rows"]),
                "MAE": float(overall["mae_all"]),
                "RMSE": float(overall["rmse_all"]),
                "positive_row_MAE": float(overall["mae_positive"]),
                "positive_row_RMSE": float(overall["rmse_positive"]),
                "mean_observed_share": float(overall["mean_observed"]),
                "mean_estimated_share": float(overall["mean_predicted"]),
                "capture_at_20_percent": float(overall["capture_at_20_percent"]),
            }
        )
    return pd.DataFrame(rows).set_index("model")


def model_component_frame(model_payload: Mapping[str, object]) -> pd.DataFrame:
    """Describe the saved hurdle estimator without inferring feature importance."""

    model = model_payload["model"]
    components = (
        ("occurrence", model.occurrence_model),
        ("positive-share", model.positive_model),
    )
    rows: list[dict[str, object]] = []
    for role, estimator in components:
        parameters = estimator.get_params(deep=False)
        rows.append(
            {
                "component": role,
                "estimator": type(estimator).__name__,
                "loss_or_objective": parameters.get("loss", "binary occurrence"),
                "max_iter": parameters.get("max_iter"),
                "learning_rate": parameters.get("learning_rate"),
                "max_leaf_nodes": parameters.get("max_leaf_nodes"),
                "min_samples_leaf": parameters.get("min_samples_leaf"),
                "random_state": parameters.get("random_state"),
            }
        )
    return pd.DataFrame(rows).set_index("component")


def plot_metric_comparison(comparison: pd.DataFrame):
    """Plot error and ranking diagnostics already recorded for the final test."""

    labels = comparison.index.str.replace("_", " ").str.title()
    figure, axes = plt.subplots(1, 3, figsize=(14, 4.4), constrained_layout=True)
    for axis, column, title, ylabel in (
        (axes[0], "MAE", "MAE: all held-out cell-years", "Burned-share error"),
        (axes[1], "RMSE", "RMSE: sensitivity to larger errors", "Burned-share error"),
        (axes[2], "capture_at_20_percent", "Positive cells captured in top 20%", "Share of positive cells"),
    ):
        bars = axis.bar(labels, comparison[column], color=("#4C78A8", "#F58518"))
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        axis.tick_params(axis="x", labelrotation=18)
        for bar, value in zip(bars, comparison[column], strict=True):
            axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.3f}", ha="center", va="bottom", fontsize=9)
    axes[2].set_ylim(0, 1)
    figure.suptitle("Held-out final temporal evaluation (T=2022–2024)", fontsize=13)
    return figure


def plot_prediction_diagnostics(
    predictions: pd.DataFrame,
    *,
    model_column: str,
    target_column: str = "burned_share_next_year",
):
    """Plot observed-versus-estimated shares and residuals by predictor year."""

    required = {model_column, target_column, "observation_year"}
    missing = required.difference(predictions.columns)
    if missing:
        raise KeyError(f"Missing prediction diagnostic columns: {sorted(missing)}")
    observed = predictions[target_column].to_numpy(dtype=float)
    estimated = predictions[model_column].to_numpy(dtype=float)
    residual = estimated - observed
    figure, axes = plt.subplots(1, 3, figsize=(16, 4.6), constrained_layout=True)
    hexbin = axes[0].hexbin(observed, estimated, gridsize=55, bins="log", mincnt=1, cmap="viridis")
    axes[0].plot([0, 1], [0, 1], color="black", linewidth=1, linestyle="--", label="equal share")
    axes[0].set(xlabel="Observed burned share", ylabel="Estimated burned share", title="All held-out final-test cell-years")
    axes[0].legend(loc="upper left")
    figure.colorbar(hexbin, ax=axes[0], label="Cells (log scale)")

    positive = predictions.loc[predictions[target_column] > 0, [target_column, model_column]]
    axes[1].scatter(positive[target_column], positive[model_column], s=5, alpha=0.18, color="#F58518", rasterized=True)
    axes[1].plot([0, 1], [0, 1], color="black", linewidth=1, linestyle="--")
    axes[1].set(xlabel="Observed burned share", ylabel="Estimated burned share", title="Cell-years with observed burning only")

    years = sorted(predictions["observation_year"].unique())
    residual_by_year = [residual[predictions["observation_year"].to_numpy() == year] for year in years]
    axes[2].boxplot(residual_by_year, tick_labels=years, showfliers=False)
    axes[2].axhline(0, color="black", linewidth=1, linestyle="--")
    axes[2].set(xlabel="Predictor year T", ylabel="Estimated − observed share", title="Estimation error by predictor year")
    return figure


def binned_observed_estimated_table(
    predictions: pd.DataFrame,
    *,
    model_column: str,
    target_column: str = "burned_share_next_year",
    bins: int = 10,
) -> pd.DataFrame:
    """Compare average observed and estimated shares across prediction bins.

    This is a descriptive regression check, not probability calibration.  Tied
    estimates may yield fewer than the requested number of bins.
    """

    frame = predictions[[model_column, target_column]].dropna().copy()
    frame["estimated_share_bin"] = pd.qcut(frame[model_column], q=bins, duplicates="drop")
    result = (
        frame.groupby("estimated_share_bin", observed=True)
        .agg(
            cell_count=(target_column, "size"),
            mean_estimated_share=(model_column, "mean"),
            mean_observed_share=(target_column, "mean"),
            positive_target_share=(target_column, lambda values: float((values > 0).mean())),
        )
        .reset_index()
    )
    return result


def plot_binned_observed_estimated(table: pd.DataFrame):
    """Visualise a binned regression comparison without calling it calibration."""

    figure, axis = plt.subplots(figsize=(7.2, 4.8), constrained_layout=True)
    axis.plot(table["mean_estimated_share"], table["mean_observed_share"], marker="o", color="#4C78A8")
    maximum = float(max(table["mean_estimated_share"].max(), table["mean_observed_share"].max(), 0.01))
    axis.plot([0, maximum], [0, maximum], color="black", linewidth=1, linestyle="--", label="equal mean share")
    axis.set(
        xlabel="Mean estimated burned share in prediction bin",
        ylabel="Mean observed burned share in prediction bin",
        title="Held-out binned observed-versus-estimated comparison",
    )
    axis.legend()
    return figure


def deterministic_sample(frame: pd.DataFrame, columns: Sequence[str], size: int = 50_000) -> pd.DataFrame:
    """Return a stable diagnostic sample without changing analytical artefacts."""

    missing = set(columns).difference(frame.columns)
    if missing:
        raise KeyError(f"Missing requested sample columns: {sorted(missing)}")
    selected = frame.loc[:, list(columns)].sort_values(list(columns)).reset_index(drop=True)
    if len(selected) <= size:
        return selected
    positions = np.linspace(0, len(selected) - 1, num=size, dtype=int)
    return selected.iloc[positions].reset_index(drop=True)
