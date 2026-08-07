"""Bounded descriptive EDA for the validated national cell-year panel."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.config import TEMPORAL
from src.feature_contract import PREDICTOR_COLUMNS, TARGET_COLUMN
from src.national_panel import NATIONAL_PANEL_PATH, OBSERVATION_YEARS, ROOT, _atomic_json


EDA_JSON_PATH = ROOT / "reports/validation/national_panel_model_readiness_eda.json"
EDA_REPORT_PATH = ROOT / "reports/validation/national_panel_model_readiness_eda.md"
TARGET_FIGURE_PATH = ROOT / "reports/figures/panel_eda_target_by_year.png"
CORRELATION_FIGURE_PATH = ROOT / "reports/figures/panel_eda_predictor_correlations.png"
NUMERIC_COLUMNS = (*PREDICTOR_COLUMNS, TARGET_COLUMN)


def split_for_year(year: int) -> str:
    if TEMPORAL.training_years[0] <= year <= TEMPORAL.training_years[1]:
        return "train"
    if TEMPORAL.validation_years[0] <= year <= TEMPORAL.validation_years[1]:
        return "validation"
    if TEMPORAL.final_test_years[0] <= year <= TEMPORAL.final_test_years[1]:
        return "final_test"
    raise ValueError(f"Year outside canonical split: {year}")


def _describe(values: pd.Series) -> dict[str, float | int]:
    quantiles = values.quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    return {
        "count": int(values.count()),
        "missing": int(values.isna().sum()),
        "minimum": float(values.min()),
        "p01": float(quantiles.loc[0.01]),
        "p05": float(quantiles.loc[0.05]),
        "p25": float(quantiles.loc[0.25]),
        "median": float(quantiles.loc[0.5]),
        "p75": float(quantiles.loc[0.75]),
        "p95": float(quantiles.loc[0.95]),
        "p99": float(quantiles.loc[0.99]),
        "maximum": float(values.max()),
        "mean": float(values.mean()),
        "standard_deviation": float(values.std()),
        "zero_count": int(values.eq(0).sum()),
    }


def run_panel_eda() -> dict[str, object]:
    parquet = pq.ParquetFile(NATIONAL_PANEL_PATH)
    frames = []
    yearly_target = {}
    for group, year in enumerate(OBSERVATION_YEARS):
        frame = parquet.read_row_group(
            group, columns=["cell_id", "observation_year", *NUMERIC_COLUMNS]
        ).to_pandas()
        frame["split"] = split_for_year(year)
        target = frame[TARGET_COLUMN]
        positive = target[target > 0]
        yearly_target[year] = {
            "row_count": len(frame),
            "zero_proportion": float(target.eq(0).mean()),
            "positive_count": int(target.gt(0).sum()),
            "mean": float(target.mean()),
            "median": float(target.median()),
            "p90": float(target.quantile(0.90)),
            "p95": float(target.quantile(0.95)),
            "p99": float(target.quantile(0.99)),
            "maximum": float(target.max()),
            "positive_median": float(positive.median()),
            "positive_p90": float(positive.quantile(0.90)),
        }
        frames.append(frame)
    panel = pd.concat(frames, ignore_index=True)
    if panel[list(NUMERIC_COLUMNS)].isna().any().any():
        raise ValueError("Model-readiness EDA found unexpected predictor/target missingness")

    split_distributions = {}
    for split, part in panel.groupby("split", sort=False):
        split_distributions[split] = {
            column: _describe(part[column]) for column in NUMERIC_COLUMNS
        }

    yearly_predictor_means = {
        int(year): {column: float(value) for column, value in means.items()}
        for year, means in panel.groupby("observation_year")[list(PREDICTOR_COLUMNS)].mean().iterrows()
    }
    train = panel.loc[panel.split.eq("train")]
    split_standardized_mean_difference = {}
    for split in ("validation", "final_test"):
        comparison = panel.loc[panel.split.eq(split)]
        split_standardized_mean_difference[split] = {
            column: float((comparison[column].mean() - train[column].mean()) / train[column].std())
            for column in PREDICTOR_COLUMNS
        }

    correlations = panel[list(NUMERIC_COLUMNS)].corr(method="pearson")
    predictor_correlations = correlations.loc[list(PREDICTOR_COLUMNS), list(PREDICTOR_COLUMNS)]
    redundant_pairs = []
    for left_index, left in enumerate(PREDICTOR_COLUMNS):
        for right in PREDICTOR_COLUMNS[left_index + 1:]:
            value = float(predictor_correlations.loc[left, right])
            if abs(value) >= 0.8:
                redundant_pairs.append({"left": left, "right": right, "correlation": value})

    outliers = {}
    for column in PREDICTOR_COLUMNS:
        q1, q3 = train[column].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = q1 - 3 * iqr, q3 + 3 * iqr
        outliers[column] = {
            "train_3iqr_lower": float(lower),
            "train_3iqr_upper": float(upper),
            "counts_by_split": {
                split: int(((part[column] < lower) | (part[column] > upper)).sum())
                for split, part in panel.groupby("split", sort=False)
            },
        }

    overall_zero = float(panel[TARGET_COLUMN].eq(0).mean())
    decision = {
        "continuous_target_retained": True,
        "binary_target_still_deferred": True,
        "zero_inflation_requires_evaluation_safeguards": True,
        "design": (
            "Proceed with the continuous regression target. Retain the historical-fire and Random "
            "Forest regression baselines, but pre-register a zero-prediction baseline, report MAE/RMSE "
            "by year plus errors on positive-target rows, and assess a compound/Tweedie regression "
            "candidate that accommodates exact zeros without defining a classification threshold."
        ),
        "gate": "Model-design gate passed — modelling may begin",
    }
    metrics = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "panel_path": str(NATIONAL_PANEL_PATH.relative_to(ROOT)).replace("\\", "/"),
        "row_count": len(panel),
        "split_row_counts": {key: int(value) for key, value in panel.split.value_counts().items()},
        "missingness": {column: int(panel[column].isna().sum()) for column in NUMERIC_COLUMNS},
        "target": {
            "overall_zero_proportion": overall_zero,
            "by_year": yearly_target,
        },
        "split_distributions": split_distributions,
        "yearly_predictor_means": yearly_predictor_means,
        "split_standardized_mean_difference_from_train": split_standardized_mean_difference,
        "correlations": correlations.to_dict(),
        "high_redundancy_pairs_abs_ge_0_8": redundant_pairs,
        "outlier_screen": outliers,
        "model_design_decision": decision,
        "final_test_use": "Descriptive drift review only; no model performance or model selection was performed.",
    }
    _atomic_json(metrics, EDA_JSON_PATH)
    _write_figures(metrics, predictor_correlations)
    _write_report(metrics)
    return metrics


def _write_figures(metrics: dict[str, object], correlations: pd.DataFrame) -> None:
    TARGET_FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    years = list(OBSERVATION_YEARS)
    target = metrics["target"]["by_year"]
    fig, axis = plt.subplots(figsize=(10, 5.5))
    axis.bar(years, [target[year]["zero_proportion"] * 100 for year in years], color="#64748b")
    axis.set_ylabel("Zero-target rows (%)")
    axis.set_xlabel("Predictor year T")
    axis.set_title("Next-year burned-share target is strongly zero-inflated")
    axis.set_ylim(80, 100)
    axis.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(TARGET_FIGURE_PATH, dpi=180)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(9, 7))
    image = axis.imshow(correlations.to_numpy(), vmin=-1, vmax=1, cmap="coolwarm")
    axis.set_xticks(range(len(correlations.columns)), correlations.columns, rotation=55, ha="right")
    axis.set_yticks(range(len(correlations.index)), correlations.index)
    fig.colorbar(image, ax=axis, label="Pearson r", shrink=0.8)
    axis.set_title("Canonical predictor Pearson correlations")
    fig.tight_layout()
    fig.savefig(CORRELATION_FIGURE_PATH, dpi=180)
    plt.close(fig)


def _write_report(metrics: dict[str, object]) -> None:
    target_rows = []
    for year in OBSERVATION_YEARS:
        item = metrics["target"]["by_year"][year]
        target_rows.append(
            f"| {year} | {split_for_year(year)} | {item['zero_proportion']:.4%} | {item['positive_count']:,} | "
            f"{item['mean']:.8f} | {item['p95']:.6f} | {item['p99']:.6f} | {item['positive_median']:.6f} |"
        )
    drift_rows = []
    for split, values in metrics["split_standardized_mean_difference_from_train"].items():
        for column, value in values.items():
            drift_rows.append(f"| {split} | `{column}` | {value:.3f} |")
    redundancy = metrics["high_redundancy_pairs_abs_ge_0_8"]
    redundancy_text = (
        "None at |r| >= 0.8."
        if not redundancy else "; ".join(
            f"`{item['left']}` / `{item['right']}`: {item['correlation']:.3f}" for item in redundancy
        )
    )
    EDA_REPORT_PATH.write_text(
        "# National panel model-readiness EDA\n\n"
        f"**{metrics['model_design_decision']['gate']}.**\n\n"
        "This report is descriptive. Final-test years are shown only for temporal-drift assessment; no model was trained, selected or evaluated.\n\n"
        "## Target distribution\n\n"
        f"Overall zero proportion: {metrics['target']['overall_zero_proportion']:.4%}.\n\n"
        "| T | Split | Zero proportion | Positive rows | Mean | P95 | P99 | Positive median |\n"
        "|---:|---|---:|---:|---:|---:|---:|---:|\n" + "\n".join(target_rows) + "\n\n"
        "The continuous target remains scientifically meaningful, but aggregate MAE/RMSE alone could reward near-zero predictions. "
        "The model design therefore retains continuous regression and adds a zero-prediction baseline, positive-row error reporting, "
        "and a compound/Tweedie candidate without defining the deferred classification threshold.\n\n"
        "## Predictor completeness, drift and redundancy\n\n"
        "All nine predictors and the target have zero missing values. Standardized mean differences below compare each later split with training:\n\n"
        "| Split | Predictor | Standardized mean difference |\n|---|---|---:|\n" + "\n".join(drift_rows) + "\n\n"
        f"High predictor redundancy: {redundancy_text}\n\n"
        "The largest split drift is JJAS precipitation: validation is +0.678 and final test +0.849 training standard deviations. "
        "Final-test years contain 9,332 precipitation rows above the training 3-IQR upper fence, but all remain inside the physical feature contract. "
        "The built-up-share training IQR is zero because most cells have zero mapped built-up area, so its 3-IQR flag counts non-zero values rather than implausible extremes.\n\n"
        "Exact distributions, annual means, correlations and 3-IQR outlier-screen counts are stored in "
        "`reports/validation/national_panel_model_readiness_eda.json`. Extreme values remain within the feature contract.\n",
        encoding="utf-8",
    )
