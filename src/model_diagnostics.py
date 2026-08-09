"""Build durable, read-only diagnostic artefacts from recorded final-test results.

The diagnostics consume the frozen final temporal test artefacts. They neither
fit models nor change predictions, model parameters, or feature values.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.extended_final_test import METRICS_PATH, PREDICTIONS_PATH
from src.notebook_reporting import (
    binned_observed_estimated_table,
    model_comparison_frame,
    plot_binned_observed_estimated,
    plot_metric_comparison,
    plot_prediction_diagnostics,
)
from src.paths import FIGURES_DIR, PROJECT_ROOT, TABLES_DIR


DIAGNOSTIC_FIGURES = {
    "metric_comparison": FIGURES_DIR / "model_final_test_metric_comparison.png",
    "prediction_diagnostics": FIGURES_DIR / "model_final_test_observed_vs_estimated.png",
    "binned_comparison": FIGURES_DIR / "model_final_test_binned_observed_vs_estimated.png",
}
DIAGNOSTIC_TABLES = {
    "overall_metrics": TABLES_DIR / "model_final_test_metrics.csv",
    "by_year_metrics": TABLES_DIR / "model_final_test_metrics_by_year.csv",
    "binned_comparison": TABLES_DIR / "model_final_test_binned_observed_vs_estimated.csv",
}
VALIDATION_PATH = PROJECT_ROOT / "reports" / "validation" / "model_final_test_diagnostics.md"


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    os.replace(temporary, path)


def _save_figure(figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.png")
    try:
        figure.savefig(temporary, dpi=180, bbox_inches="tight", facecolor="white", format="png")
        os.replace(temporary, path)
    finally:
        plt.close(figure)


def _by_year_metrics_frame(metrics: dict[str, object]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model, result in metrics["metrics"].items():
        for year, values in result["by_final_test_year"].items():
            rows.append(
                {
                    "model": model,
                    "predictor_year": int(year),
                    "MAE": float(values["mae_all"]),
                    "RMSE": float(values["rmse_all"]),
                    "positive_row_MAE": float(values["mae_positive"]),
                    "positive_row_RMSE": float(values["rmse_positive"]),
                    "mean_observed_share": float(values["mean_observed"]),
                    "mean_estimated_share": float(values["mean_predicted"]),
                    "capture_at_20_percent": float(values["capture_at_20_percent"]),
                }
            )
    return pd.DataFrame(rows).sort_values(["predictor_year", "model"], kind="mergesort").reset_index(drop=True)


def build_model_diagnostics() -> dict[str, object]:
    """Create durable figures/tables from frozen final-test data only."""

    if not METRICS_PATH.is_file() or not PREDICTIONS_PATH.is_file():
        raise FileNotFoundError("Run the frozen final temporal evaluation before building diagnostics")
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    if metrics["design"]["final_test_years"] != [2022, 2023, 2024] or metrics["design"]["tuning_performed"]:
        raise ValueError("Model diagnostics require the recorded frozen T=2022-2024 evaluation")
    predictions = pd.read_parquet(PREDICTIONS_PATH)
    required = {
        "cell_id",
        "observation_year",
        "outcome_year",
        "burned_share_next_year",
        "historical_recurrence_baseline",
        "nine_feature_hurdle",
    }
    if set(predictions.columns) != required:
        raise ValueError(f"Unexpected final-test prediction schema: {sorted(predictions.columns)}")
    if not predictions.outcome_year.eq(predictions.observation_year + 1).all():
        raise ValueError("Final-test prediction table breaks the T+1 target contract")

    comparison = model_comparison_frame(metrics).rename(
        index={
            "historical_recurrence_baseline": "Historical recurrence baseline",
            "nine_feature_hurdle": "Nine-feature Model v2",
        }
    )
    by_year = _by_year_metrics_frame(metrics)
    binned = binned_observed_estimated_table(predictions, model_column="nine_feature_hurdle")
    _atomic_csv(comparison.reset_index(), DIAGNOSTIC_TABLES["overall_metrics"])
    _atomic_csv(by_year, DIAGNOSTIC_TABLES["by_year_metrics"])
    _atomic_csv(binned, DIAGNOSTIC_TABLES["binned_comparison"])
    _save_figure(plot_metric_comparison(comparison), DIAGNOSTIC_FIGURES["metric_comparison"])
    _save_figure(
        plot_prediction_diagnostics(predictions, model_column="nine_feature_hurdle"),
        DIAGNOSTIC_FIGURES["prediction_diagnostics"],
    )
    _save_figure(plot_binned_observed_estimated(binned), DIAGNOSTIC_FIGURES["binned_comparison"])
    result = {
        "final_test_years": metrics["design"]["final_test_years"],
        "prediction_rows": int(len(predictions)),
        "figures": {name: path.relative_to(PROJECT_ROOT).as_posix() for name, path in DIAGNOSTIC_FIGURES.items()},
        "tables": {name: path.relative_to(PROJECT_ROOT).as_posix() for name, path in DIAGNOSTIC_TABLES.items()},
        "interpretation": "Regression diagnostics only; no probability calibration, recommendation, or model refit.",
    }
    VALIDATION_PATH.write_text(
        "# Final-test model diagnostics\n\n"
        "The listed figures and tables were regenerated from the recorded frozen T=2022-2024 final temporal test. "
        "They do not refit the model or alter its predictions.\n\n"
        f"- Prediction rows: {result['prediction_rows']:,}.\n"
        f"- Final predictor years: {result['final_test_years']}.\n"
        f"- Figures: {', '.join(f'`{path}`' for path in result['figures'].values())}.\n"
        f"- Tables: {', '.join(f'`{path}`' for path in result['tables'].values())}.\n\n"
        "MAE/RMSE are regression errors, while capture@20% is a technical ranking diagnostic. "
        "The binned chart is an observed-versus-estimated regression comparison, not probability calibration.\n",
        encoding="utf-8",
    )
    return result


def validate_model_diagnostics() -> dict[str, object]:
    """Confirm the durable diagnostic inventory exists without rewriting it."""

    missing = [path.relative_to(PROJECT_ROOT).as_posix() for path in (*DIAGNOSTIC_FIGURES.values(), *DIAGNOSTIC_TABLES.values(), VALIDATION_PATH) if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise FileNotFoundError(f"Missing model diagnostic artefacts: {missing}")
    return {
        "status": "verified_existing",
        "figures": {name: path.relative_to(PROJECT_ROOT).as_posix() for name, path in DIAGNOSTIC_FIGURES.items()},
        "tables": {name: path.relative_to(PROJECT_ROOT).as_posix() for name, path in DIAGNOSTIC_TABLES.items()},
        "report": VALIDATION_PATH.relative_to(PROJECT_ROOT).as_posix(),
    }
