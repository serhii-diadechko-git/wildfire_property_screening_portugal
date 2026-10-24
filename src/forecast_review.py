"""Isolated retrospective forecast checks; never rewrites published artefacts.

All specifications are fixed before this run. These are reused development
years and revised input vintages, NOT a new untouched or as-issued test.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

from src.evaluation import tie_aware_ranking_metrics
from src.feature_contract import PREDICTOR_COLUMNS, TARGET_COLUMN
from src.modeling import HistoricalFireMeanRegressor, HurdleHistGradientRegressor, RANDOM_SEED
from src.paths import PROJECT_ROOT as ROOT

SEED = 20261024
SOURCE = ROOT / "data/processed/extended_model_selection_2010_2021"
MATRICES = (SOURCE / "nine_feature_train_validation_matrix.parquet",
            SOURCE / "final_temporal_test_nine_feature_matrix.parquet")
MODELS = ("zero", "training_mean", "cell_training_mean", "latest_available_year",
          "recurrence", "hurdle_published_parameters", "hurdle_fixed_iterations")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def split_fold(frame: pd.DataFrame, outcome_year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Issue Dec 31 Y-1: labels through Y-2, predictors Y-1, target Y.

    Publication of Y-2 is an assumption here, NOT evidence of availability.
    Real issuance additionally requires the dated availability gate.
    """
    if not frame.outcome_year.eq(frame.observation_year + 1).all():
        raise ValueError("Target must be the next calendar year")
    if frame.duplicated(["cell_id", "outcome_year"]).any():
        raise ValueError("Duplicate cell-year")
    train = frame.loc[frame.outcome_year.le(outcome_year - 2)].copy()
    test = frame.loc[frame.outcome_year.eq(outcome_year)].copy()
    if train.outcome_year.nunique() < 4 or test.empty:
        raise ValueError("Need at least four completed training years and a test year")
    if set(train.cell_id) != set(test.cell_id):
        raise ValueError("This experiment requires the same complete grid each year")
    return train, test


def fit_predict(train: pd.DataFrame, features: pd.DataFrame) -> tuple[dict, dict]:
    """The scoring argument has no label column; all learning uses train only."""
    if TARGET_COLUMN in features:
        raise ValueError("Scoring features must be target-free")
    X = train.loc[:, PREDICTOR_COLUMNS]
    X_test = features.loc[:, PREDICTOR_COLUMNS]
    y = train[TARGET_COLUMN]
    latest = train.loc[train.outcome_year.eq(train.outcome_year.max())].set_index("cell_id")[TARGET_COLUMN]
    predictions = {
        "zero": np.zeros(len(features)),
        "training_mean": np.full(len(features), y.mean()),
        "cell_training_mean": features.cell_id.map(train.groupby("cell_id")[TARGET_COLUMN].mean()).to_numpy(),
        "latest_available_year": features.cell_id.map(latest).to_numpy(),
        "recurrence": HistoricalFireMeanRegressor().fit(X, y).predict(X_test),
    }
    fitted = {}
    for name, override in (("hurdle_published_parameters", {}),
                           ("hurdle_fixed_iterations", {"early_stopping": False})):
        model = HurdleHistGradientRegressor(occurrence_params=override, positive_share_params=override)
        with threadpool_limits(limits=1):
            model.fit(X, y)
            predictions[name] = model.predict(X_test)
        fitted[name] = model
    for values in predictions.values():
        if not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
            raise ValueError("Invalid prediction")
    return predictions, fitted


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    if y.shape != p.shape or y.ndim != 1 or not len(y):
        raise ValueError("Metrics require aligned nonempty vectors")
    if not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError("Metrics require finite values")
    positive = y > 0
    e = p - y
    ranks = tie_aware_ranking_metrics(y, p, .2)
    return {
        "rows": len(y), "positive_rows": int(positive.sum()),
        "zero_fraction": float((~positive).mean()),
        "mae": float(np.abs(e).mean()), "rmse": float(np.sqrt(np.square(e).mean())),
        "positive_mae": float(np.abs(e[positive]).mean()) if positive.any() else np.nan,
        "positive_rmse": float(np.sqrt(np.square(e[positive]).mean())) if positive.any() else np.nan,
        "zero_mae": float(np.abs(e[~positive]).mean()) if (~positive).any() else np.nan,
        "observed_mean": float(y.mean()), "predicted_mean": float(p.mean()),
        "bias": float(e.mean()),
        "predicted_observed_ratio": float(p.sum() / y.sum()) if y.sum() else np.nan,
        "mass_capture20": ranks["burned_share_mass_capture"],
        "positive_capture20": ranks["positive_cell_capture"],
    }


def block_year_draws(n_years: int, block_length: int, replicates: int, seed: int) -> np.ndarray:
    """Circular moving blocks; one country-wide year is the sampling unit."""
    if not 1 <= block_length <= n_years or replicates < 1:
        raise ValueError("Invalid bootstrap shape")
    rng = np.random.default_rng(seed)
    starts = rng.integers(n_years, size=(replicates, int(np.ceil(n_years / block_length))))
    return ((starts[..., None] + np.arange(block_length)) % n_years).reshape(replicates, -1)[:, :n_years]


def paired_uncertainty(annual: pd.DataFrame, model: str, baseline: str,
                       block_length: int, replicates: int = 4000) -> pd.DataFrame:
    """Paired whole-country year blocks preserve all within-year spatial dependence.

    This estimates metric differences, NOT prediction intervals. It does not
    refit models, repair selection reuse, or establish independence of years.
    """
    a = annual.loc[annual.model.eq(model)].sort_values("outcome_year").set_index("outcome_year")
    b = annual.loc[annual.model.eq(baseline)].sort_values("outcome_year").set_index("outcome_year")
    if not a.index.equals(b.index) or not np.array_equal(a.rows, b.rows):
        raise ValueError("Paired methods must use identical years and rows")
    draws = block_year_draws(len(a), block_length, replicates, SEED)
    rows = []
    for metric in ("mae", "rmse", "positive_mae", "mass_capture20"):
        def statistic(frame, idx):
            values = frame[metric].to_numpy()[idx]
            weights = frame["positive_rows" if metric == "positive_mae" else "rows"].to_numpy()[idx]
            if metric == "mass_capture20":
                return values.mean(axis=-1)  # equal annual decision budgets
            avg = np.sum((values ** 2 if metric == "rmse" else values) * weights, axis=-1) / weights.sum(axis=-1)
            return np.sqrt(avg) if metric == "rmse" else avg
        distribution = statistic(a, draws) - statistic(b, draws)
        point = float(statistic(a, np.arange(len(a))) - statistic(b, np.arange(len(b))))
        low, high = np.quantile(distribution, [.025, .975])
        rows.append(dict(model=model, baseline=baseline, metric=metric, difference=point,
                         lower95=float(low), upper95=float(high), years=len(a),
                         block_years=block_length, replicates=replicates))
    return pd.DataFrame(rows)


def aggregate_forecasts(history: pd.Series, year: int) -> dict[str, float]:
    """National annual land-area-weighted target; no invented annual seasonality."""
    known = history.loc[history.index <= year - 2].sort_index()
    if len(known) < 4:
        raise ValueError("Insufficient aggregate history")
    horizon = year - int(known.index[-1])
    values = known.to_numpy(dtype=float)
    # Fixed simple exponential smoothing, no tuning on evaluation years.
    level = values[0]
    for value in values[1:]:
        level = .3 * value + .7 * level
    # AR(1) = ARIMA(1,0,0), conditional least squares with intercept. A modest
    # aggregate-only diagnostic, not thousands of poorly identified cell fits.
    intercept, phi = np.linalg.lstsq(np.column_stack([np.ones(len(values) - 1), values[:-1]]),
                                   values[1:], rcond=None)[0]
    ar = values[-1]
    for _ in range(horizon):
        ar = intercept + phi * ar
    return {"zero": 0., "training_mean": float(values.mean()),
            "latest_available_year": float(values[-1]),
            "trailing_three_year_mean": float(values[-3:].mean()),
            "ses_alpha_0_3": float(level), "ar1_ols": float(np.clip(ar, 0, 1))}


def protected_inventory() -> dict[str, str]:
    """Hash existing analytical/publication files; research outputs live elsewhere."""
    paths = set(MATRICES)
    for directory in (SOURCE, ROOT / "data/processed/final_model_2010_2024",
                      ROOT / "data/processed/operational_forecasts", ROOT / "data/processed/spatial_outputs",
                      ROOT / "data/processed/web_map", ROOT / "reports/figures", ROOT / "reports/tables",
                      ROOT / "reports/validation", ROOT / "reports/presentation", ROOT / "qgis"):
        # Legacy preflight refreshes its checked_utc timestamp even in tests.
        # It is a volatile readiness log, not a model/prediction/publication.
        paths.update(p for p in directory.rglob("*") if p.is_file()
                     and p.name != "forecast_2026_preflight.json")
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(paths)}


def load_panel() -> pd.DataFrame:
    columns = ["cell_id", "observation_year", "outcome_year", *PREDICTOR_COLUMNS, TARGET_COLUMN]
    frame = pd.concat([pd.read_parquet(p, columns=columns) for p in MATRICES], ignore_index=True)
    frame = frame.sort_values(["outcome_year", "cell_id"]).reset_index(drop=True)
    if frame.duplicated(["cell_id", "outcome_year"]).any():
        raise ValueError("Duplicate analytical key")
    if tuple(frame.outcome_year.unique()) != tuple(range(2011, 2026)):
        raise ValueError("Expected completed outcomes 2011-2025")
    if not frame.groupby("outcome_year").cell_id.nunique().eq(89112).all():
        raise ValueError("Expected complete mainland grid in every year")
    if not np.isfinite(frame[[*PREDICTOR_COLUMNS, TARGET_COLUMN]].to_numpy()).all():
        raise ValueError("Missing or invalid inputs; no whole-panel imputation allowed")
    if not frame[TARGET_COLUMN].between(0, 1).all():
        raise ValueError("Invalid target")
    return frame


def run(run_name: str) -> dict:
    if not run_name.replace("_", "").isalnum():
        raise ValueError("Use letters, digits and underscores in run_name")
    report_dir = ROOT / "reports/research" / run_name
    data_dir = ROOT / "data/processed/research" / run_name
    if report_dir.exists() or data_dir.exists():
        raise FileExistsError("Use a new run name; completed or interrupted experiments are immutable")
    report_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    started = time.perf_counter()
    protected = protected_inventory()
    write_json(data_dir / "protected_before.json", protected)
    protocol = {
        "review_date": "2026-10-24", "bootstrap_seed": SEED, "model_seed": RANDOM_SEED,
        "outcome_years": list(range(2016, 2026)), "training_first_outcome_year": 2011,
        "issue_time": "December 31 Y-1 at 12:00 UTC", "input_cutoff": "December 30 Y-1 at 23:59:59 UTC",
        "latest_training_outcome_year": "Y-2", "scoring_predictor_year": "Y-1",
        "history_fire_window": "Y-11 through Y-2", "label_publication_assumption": "Y-2 available; not verified historically",
        "status": "retrospective sensitivity analysis using revised vintages and reused development years",
        "selection": "none; two predeclared versions, no hyperparameter search or test-based promotion",
        "preprocessing": "identity; fixed source transformations; all HGB binning and both stages fitted within fold",
        "variants": {"hurdle_published_parameters": "current defaults incl training-only automatic early stopping",
                     "hurdle_fixed_iterations": "same fixed tree budgets, early_stopping=False in both stages"},
        "baselines": list(MODELS[:5]), "geographic_scope": "future years in already-observed mainland cells",
        "aggregate_target": "sum(cell burned_share * land_area_m2) / sum(land_area_m2); separate from cell-level task",
        "uncertainty": "paired whole-country circular year blocks of length 1, 2 and 3; 4000 resamples; not prediction intervals",
    }
    write_json(report_dir / "protocol.json", protocol)
    frame = load_panel()
    catalog_path = ROOT / "data/interim/national_panel_2015_2024/grid_catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    grid_paths = [ROOT / b["path"] for b in catalog["batches"]]
    areas = pd.concat([pd.read_parquet(p, columns=["cell_id", "land_area_m2"]) for p in grid_paths]).set_index("cell_id").land_area_m2
    if not areas.index.is_unique or set(areas.index) != set(frame.cell_id) or not areas.gt(0).all():
        raise ValueError("Area weights do not match grid")
    frame["land_area_m2"] = frame.cell_id.map(areas)
    national = (frame.assign(burned_m2=frame[TARGET_COLUMN] * frame.land_area_m2)
                .groupby("outcome_year").agg(burned_m2=("burned_m2", "sum"), land_m2=("land_area_m2", "sum")))
    national["burned_share"] = national.burned_m2 / national.land_m2
    national.to_csv(report_dir / "national_observed.csv")

    # Independently recompute the recorded frozen predictions, with explicit
    # mass and positive-cell ranking names. Do not regenerate old reports.
    frozen = pd.read_parquet(SOURCE / "final_temporal_test_predictions.parquet")
    frozen_rows = []
    for year, group in [("pooled", frozen), *list(frozen.groupby("outcome_year"))]:
        for model in ("historical_recurrence_baseline", "nine_feature_hurdle", "zero"):
            p = np.zeros(len(group)) if model == "zero" else group[model].to_numpy()
            frozen_rows.append(dict(outcome_year=year, model=model, **metrics(group[TARGET_COLUMN].to_numpy(), p)))
    pd.DataFrame(frozen_rows).to_csv(report_dir / "frozen_audit.csv", index=False)
    # Verify saved model predictions and recorded metric JSON, not docs alone.
    final_features = pd.read_parquet(MATRICES[1]).sort_values(["observation_year", "cell_id"])
    frozen = frozen.sort_values(["observation_year", "cell_id"])
    if not final_features[["cell_id", "outcome_year"]].reset_index(drop=True).equals(frozen[["cell_id", "outcome_year"]].reset_index(drop=True)):
        raise ValueError("Frozen features/predictions misaligned")
    verification = {}
    recorded = json.loads((SOURCE / "final_temporal_test_metrics.json").read_text())
    for name in ("historical_recurrence_baseline", "nine_feature_hurdle"):
        model = joblib.load(SOURCE / f"models/{name}.joblib")["model"]
        with threadpool_limits(limits=1):
            pred = model.predict(final_features.loc[:, PREDICTOR_COLUMNS])
        if not np.allclose(pred, frozen[name], rtol=0, atol=1e-12):
            raise ValueError("Saved model does not reproduce frozen predictions")
        m = metrics(frozen[TARGET_COLUMN].to_numpy(), pred)
        for key in ("mae", "rmse"):
            if not np.isclose(m[key], recorded["metrics"][name]["overall"][key + "_all"], rtol=0, atol=1e-12):
                raise ValueError("Recorded error metric differs")
        verification[name] = {"predictions_match_atol": 1e-12, "recorded_mae_rmse_match": True}
    write_json(report_dir / "frozen_verification.json", verification)

    annual, fold_rows, aggregate_rows = [], [], []
    for year in protocol["outcome_years"]:
        tick = time.perf_counter()
        train, test = split_fold(frame, year)
        print(f"Outcome {year}: fit {len(train):,} rows, labels through {year-2}", flush=True)
        predictions, fitted = fit_predict(train, test[["cell_id", *PREDICTOR_COLUMNS]])
        out = test[["cell_id", "observation_year", "outcome_year", TARGET_COLUMN]].copy()
        for name, values in predictions.items():
            out[name] = values
            annual.append(dict(outcome_year=year, model=name, **metrics(test[TARGET_COLUMN].to_numpy(), values)))
            aggregate_rows.append(dict(outcome_year=year, model="cell_" + name,
                                       observed=national.loc[year, "burned_share"],
                                       predicted=float(np.average(values, weights=test.land_area_m2))))
        out.to_parquet(data_dir / f"predictions_{year}.parquet", index=False, compression="zstd")
        for name, model in fitted.items():
            joblib.dump({"model": model, "outcome_year": year, "latest_training_outcome_year": year-2,
                         "features": list(PREDICTOR_COLUMNS), "protocol": protocol}, data_dir / f"{name}_{year}.joblib")
            fold_rows.append(dict(outcome_year=year, model=name, training_rows=len(train),
                                  first_training_outcome=int(train.outcome_year.min()),
                                  last_training_outcome=int(train.outcome_year.max()), test_rows=len(test),
                                  occurrence_iterations=model.occurrence_model.n_iter_,
                                  positive_iterations=model.positive_model.n_iter_))
        for name, value in aggregate_forecasts(national.burned_share, year).items():
            aggregate_rows.append(dict(outcome_year=year, model="aggregate_" + name,
                                       observed=national.loc[year, "burned_share"], predicted=value))
        print(f"Outcome {year}: complete in {time.perf_counter()-tick:.1f}s", flush=True)
        pd.DataFrame(annual).to_csv(report_dir / "backtest_by_year.csv", index=False)
        pd.DataFrame(fold_rows).to_csv(report_dir / "folds.csv", index=False)
    annual = pd.DataFrame(annual)
    summary_rows = []
    for name, group in annual.groupby("model"):
        summary_rows.append(dict(model=name, years=len(group),
            mae=float(np.average(group.mae, weights=group.rows)),
            rmse=float(np.sqrt(np.average(group.rmse ** 2, weights=group.rows))),
            positive_mae=float(np.average(group.positive_mae, weights=group.positive_rows)),
            mean_annual_mass_capture20=float(group.mass_capture20.mean()),
            burned_mass_weighted_annual_capture20=float(np.average(group.mass_capture20, weights=group.observed_mean * group.rows)),
            mean_observed=float(group.observed_mean.mean()), mean_predicted=float(group.predicted_mean.mean())))
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(report_dir / "backtest_summary.csv", index=False)
    deltas = []
    indexed = summary.set_index("model")
    for name in MODELS:
        for baseline in ("recurrence", "zero"):
            for metric in ("mae", "rmse", "positive_mae", "mean_annual_mass_capture20"):
                v, b = indexed.loc[name, metric], indexed.loc[baseline, metric]
                deltas.append(dict(model=name, baseline=baseline, metric=metric,
                                   difference=v-b, percent_difference=100*(v-b)/b if b else np.nan))
    pd.DataFrame(deltas).to_csv(report_dir / "differences.csv", index=False)
    intervals = []
    for block in (1, 2, 3):
        for model, baseline in (("hurdle_published_parameters", "recurrence"),
                                ("hurdle_published_parameters", "zero"),
                                ("hurdle_fixed_iterations", "hurdle_published_parameters")):
            intervals.append(paired_uncertainty(annual, model, baseline, block))
    pd.concat(intervals).to_csv(report_dir / "uncertainty.csv", index=False)
    frozen_annual = pd.DataFrame(frozen_rows).query("outcome_year != 'pooled'")
    frozen_intervals = [paired_uncertainty(frozen_annual, "nine_feature_hurdle", "historical_recurrence_baseline", b)
                        for b in (1, 2)]
    pd.concat(frozen_intervals).to_csv(report_dir / "frozen_uncertainty.csv", index=False)
    aggregate = pd.DataFrame(aggregate_rows)
    aggregate.to_csv(report_dir / "aggregate_by_year.csv", index=False)
    agg_summary = []
    for name, group in aggregate.groupby("model"):
        error = group.predicted - group.observed
        agg_summary.append(dict(model=name, years=len(group), mae=error.abs().mean(),
                                rmse=np.sqrt(np.square(error).mean()), bias=error.mean()))
    pd.DataFrame(agg_summary).to_csv(report_dir / "aggregate_summary.csv", index=False)
    plot_results(annual, report_dir / "annual_results.png")
    after = {path: sha256(ROOT / path) for path in protected}
    if protected != after:
        raise RuntimeError("A protected published file changed during the run")
    inputs = [*MATRICES, SOURCE / "final_temporal_test_predictions.parquet", SOURCE / "final_temporal_test_metrics.json",
              SOURCE / "models/nine_feature_hurdle.joblib", SOURCE / "models/historical_recurrence_baseline.joblib",
              catalog_path, *grid_paths]
    manifest = {
        "status": "complete", "run_name": run_name, "review_date": "2026-10-24",
        "elapsed_seconds": time.perf_counter() - started,
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "sklearn": sklearn.__version__},
        "code_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in (Path(__file__), ROOT / "src/modeling.py", ROOT / "src/evaluation.py", ROOT / "scripts/run_forecast_review.py")},
        "input_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in inputs},
        "protected_file_count": len(protected), "protected_files_unchanged": True,
        "excluded_volatile_log": "data/processed/final_model_2010_2024/forecast_2026_preflight.json",
        "research_artifact_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in data_dir.iterdir() if p.is_file()},
        "result_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in report_dir.iterdir() if p.is_file()},
    }
    write_json(report_dir / "run_manifest.json", manifest)
    return manifest


def plot_results(annual: pd.DataFrame, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True, constrained_layout=True)
    names = {"zero": "Zero", "recurrence": "Recurrence", "hurdle_published_parameters": "Two-stage: published parameters",
             "hurdle_fixed_iterations": "Two-stage: fixed iterations"}
    for name, label in names.items():
        g = annual.loc[annual.model.eq(name)]
        for ax, metric in zip(axes, ("mae", "mass_capture20", "predicted_mean")):
            ax.plot(g.outcome_year, g[metric], marker="o", label=label)
    g = annual.loc[annual.model.eq("zero")]
    axes[2].plot(g.outcome_year, g.observed_mean, "k--", label="Observed mean")
    axes[0].set_title("Retrospective annual backtest: known locations, labels delayed one full year")
    for ax, label in zip(axes, ("MAE (share)", "Annual top-20% mass capture", "Mean burned share")):
        ax.set_ylabel(label)
        ax.grid(alpha=.25)
    axes[0].legend(fontsize=8)
    axes[2].legend(fontsize=8)
    axes[2].set_xlabel("Outcome year (not predictor year)")
    fig.savefig(path, dpi=150)
    plt.close(fig)
