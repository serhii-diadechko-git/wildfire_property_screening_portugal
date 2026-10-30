"""Isolated full-grid, delayed-label retrospective Random Forest experiment."""
from __future__ import annotations

import gc
import importlib.metadata
import json
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from threadpoolctl import threadpool_limits

from src.feature_contract import PREDICTOR_COLUMNS, TARGET_COLUMN
from src.forecast_review import (MATRICES, ROOT, SOURCE, load_panel, metrics,
                                 paired_uncertainty, protected_inventory,
                                 sha256, split_fold, write_json)
from src.modeling import HistoricalFireMeanRegressor, HurdleHistGradientRegressor, RANDOM_SEED

BASELINES = ("zero", "training_mean", "cell_training_mean", "latest_available_year", "recurrence")
LEARNED = ("hgb_hurdle", "rf_direct", "rf_hurdle")
MODELS = BASELINES + LEARNED
RF_PARAMS = dict(n_estimators=48, max_depth=12, max_leaf_nodes=512,
                 max_features=1.0, bootstrap=True, max_samples=None,
                 n_jobs=2, random_state=RANDOM_SEED)
PROTOCOL = ROOT / "docs/random_forest_experiment_protocol.md"


class RFHurdleRegressor:
    """Expected burned share, with separate occurrence and conditional severity."""

    def __init__(self, n_estimators=48, max_depth=12, max_leaf_nodes=512,
                 n_jobs=2, random_state=RANDOM_SEED):
        params = dict(RF_PARAMS, n_estimators=n_estimators, max_depth=max_depth,
                      max_leaf_nodes=max_leaf_nodes, n_jobs=n_jobs, random_state=random_state)
        self.occurrence_model = RandomForestClassifier(**params, min_samples_leaf=80)
        self.positive_model = RandomForestRegressor(**params, min_samples_leaf=55)

    def fit(self, X, y):
        require_features(X)
        target = np.asarray(y, dtype=float)
        positive = target > 0
        if positive.sum() < 2 or (~positive).sum() < 2:
            raise ValueError("Hurdle model requires zero and positive training targets")
        self.occurrence_model.fit(X, positive.astype("int8"))
        self.positive_model.fit(X.loc[positive], target[positive])
        return self

    def predict(self, X):
        require_features(X)
        return np.clip(self.occurrence_model.predict_proba(X)[:, 1]
                       * np.clip(self.positive_model.predict(X), 0, 1), 0, 1)


def require_features(X):
    if tuple(X.columns) != PREDICTOR_COLUMNS:
        raise ValueError("Exactly the ordered nine target-free predictors are required")


class SimpleBaseline:
    """Serializable baseline whose fitting and scoring costs can be measured."""

    def __init__(self, name):
        self.name = name

    def fit(self, train):
        y = train[TARGET_COLUMN]
        self.value = 0.0 if self.name == "zero" else float(y.mean())
        if self.name == "cell_training_mean":
            self.values = train.groupby("cell_id")[TARGET_COLUMN].mean()
        elif self.name == "latest_available_year":
            self.values = train.loc[train.outcome_year.eq(train.outcome_year.max())].set_index("cell_id")[TARGET_COLUMN]
        elif self.name == "recurrence":
            self.estimator = HistoricalFireMeanRegressor().fit(train.loc[:, PREDICTOR_COLUMNS], y)
        return self

    def predict(self, features):
        if TARGET_COLUMN in features:
            raise ValueError("Scoring must be target-free")
        if self.name in ("cell_training_mean", "latest_available_year"):
            return features.cell_id.map(self.values).to_numpy()
        if self.name == "recurrence":
            return self.estimator.predict(features.loc[:, PREDICTOR_COLUMNS])
        return np.full(len(features), self.value)


def make_model(name):
    if name in BASELINES:
        return SimpleBaseline(name)
    if name == "hgb_hurdle":
        return HurdleHistGradientRegressor()
    if name == "rf_direct":
        return RandomForestRegressor(**RF_PARAMS, min_samples_leaf=80)
    if name == "rf_hurdle":
        return RFHurdleRegressor()
    raise ValueError(name)


def range_diagnostics(train_X, test_X):
    require_features(train_X)
    require_features(test_X)
    low, high = train_X.min(), train_X.max()
    quantiles = train_X.quantile([.1, .9])
    below, above = test_X.lt(low), test_X.gt(high)
    flags = pd.DataFrame(index=test_X.index)
    flags["outside_range"] = (below | above).any(axis=1)
    flags["hot"] = test_X[PREDICTOR_COLUMNS[4]].gt(quantiles.loc[.9, PREDICTOR_COLUMNS[4]])
    flags["dry"] = (test_X[PREDICTOR_COLUMNS[5]].lt(quantiles.loc[.1, PREDICTOR_COLUMNS[5]])
                    | test_X[PREDICTOR_COLUMNS[6]].lt(quantiles.loc[.1, PREDICTOR_COLUMNS[6]]))
    bounds = pd.DataFrame(dict(feature=list(PREDICTOR_COLUMNS), train_min=low.values,
                              train_max=high.values, train_q10=quantiles.loc[.1].values,
                              train_q90=quantiles.loc[.9].values,
                              test_below=below.sum().values, test_above=above.sum().values))
    return flags, bounds


def checked_panel():
    frame = load_panel()
    canonical = frame.loc[frame.outcome_year.eq(2011), "cell_id"].to_numpy()
    for _, group in frame.groupby("outcome_year", sort=True):
        if not np.array_equal(group.cell_id.to_numpy(), canonical):
            raise ValueError("Every outcome year must contain the identical ordered full grid")
    metadata_cols = ["observation_year", "outcome_year", "historical_fire_start_year",
                     "historical_fire_end_year", "climate_reference_year", "land_cover_reference_year",
                     "land_cover_release_id", "terrain_release_id"]
    source_records = []
    for path in MATRICES:
        m = pd.read_parquet(path, columns=metadata_cols)
        valid = (m.outcome_year.eq(m.observation_year + 1)
                 & m.historical_fire_start_year.eq(m.observation_year - 10)
                 & m.historical_fire_end_year.eq(m.observation_year - 1)
                 & m.climate_reference_year.eq(m.observation_year)
                 & m.land_cover_reference_year.le(m.observation_year))
        if not valid.all():
            raise ValueError("Actual source-year metadata violates forecast timing")
        source_records.extend(m.drop_duplicates().to_dict("records"))
    return frame, source_records


def load_areas(frame):
    catalog_path = ROOT / "data/interim/national_panel_2015_2024/grid_catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    paths = [ROOT / b["path"] for b in catalog["batches"]]
    areas = pd.concat([pd.read_parquet(p, columns=["cell_id", "land_area_m2"]) for p in paths]).set_index("cell_id").land_area_m2
    if not areas.index.is_unique or set(areas.index) != set(frame.cell_id) or not areas.gt(0).all():
        raise ValueError("Area weights must match the full grid")
    return areas, [catalog_path, *paths]


def parameter_record(model):
    if isinstance(model, SimpleBaseline):
        return {"name": model.name}
    if hasattr(model, "occurrence_model"):
        return {"occurrence": model.occurrence_model.get_params(),
                "positive_share": model.positive_model.get_params()}
    return model.get_params()


def response_inputs(train_X):
    """Training-anchored diagnostics, never evidence of future accuracy."""
    temp = PREDICTOR_COLUMNS[4]
    anchors = []
    for q in (.1, .5, .9):
        value = train_X[temp].quantile(q)
        anchors.append(train_X.loc[(train_X[temp] - value).abs().idxmin()])
    rows = []
    for segment in (0, 1):
        for weight in np.linspace(0, 1, 21):
            values = (1 - weight) * anchors[segment] + weight * anchors[segment + 1]
            values[PREDICTOR_COLUMNS[3]] = round(values[PREDICTOR_COLUMNS[3]])
            rows.append(dict(diagnostic="training_anchor_interpolation", axis=segment + weight,
                             **values.to_dict()))
    # Find an actual hot, dry row rather than construct a marginal median profile.
    scores = train_X[temp].rank(pct=True) - train_X[PREDICTOR_COLUMNS[6]].rank(pct=True)
    anchor = train_X.loc[scores.idxmax()].copy()
    for delta in np.linspace(0, 8, 33):
        values = anchor.copy()
        for name in (PREDICTOR_COLUMNS[4], PREDICTOR_COLUMNS[7]):
            values[name] += delta
        for name in (PREDICTOR_COLUMNS[5], PREDICTOR_COLUMNS[6], PREDICTOR_COLUMNS[8]):
            values[name] *= 1 - .075 * delta
        rows.append(dict(diagnostic="synthetic_hot_dry_stress", axis=delta, **values.to_dict()))
    return pd.DataFrame(rows)


def empty_metrics():
    return {key: (0 if key in ("rows", "positive_rows") else np.nan)
            for key in metrics(np.array([0., 1.]), np.array([0., 0.]))}


def summarize(report_dir, data_dir):
    annual = pd.read_csv(report_dir / "metrics_by_year.csv")
    pooled = pd.concat([pd.read_parquet(data_dir / f"predictions_{y}.parquet") for y in range(2016, 2026)], ignore_index=True)
    rows = []
    for name in MODELS:
        g = annual.loc[annual.model.eq(name)]
        rows.append(dict(model=name, **metrics(pooled[TARGET_COLUMN].to_numpy(), pooled[name].to_numpy()),
                         mean_annual_mass_capture20=g.mass_capture20.mean(),
                         mean_annual_mae=g.mae.mean(), mean_annual_rmse=g.rmse.mean(),
                         mean_annual_positive_mae=g.positive_mae.mean(),
                         total_fit_seconds=g.fit_seconds.sum(), total_predict_seconds=g.predict_seconds.sum(),
                         mean_model_bytes=g.model_bytes.mean(), max_model_bytes=g.model_bytes.max(),
                         national_mae=np.abs(g.national_predicted - g.national_observed).mean(),
                         national_rmse=np.sqrt(np.square(g.national_predicted - g.national_observed).mean())))
    summary = pd.DataFrame(rows)
    summary.to_csv(report_dir / "metrics_pooled.csv", index=False)
    pairs = [(a, b) for a in LEARNED for b in BASELINES]
    pairs += [("rf_direct", "hgb_hurdle"), ("rf_hurdle", "hgb_hurdle"), ("rf_hurdle", "rf_direct")]
    intervals = [paired_uncertainty(annual, a, b, block) for a, b in pairs for block in (1, 2, 3)]
    pd.concat(intervals).to_csv(report_dir / "paired_uncertainty.csv", index=False)
    differences = []
    indexed = summary.set_index("model")
    for a, b in pairs:
        aa = annual.loc[annual.model.eq(a)].sort_values("outcome_year")
        bb = annual.loc[annual.model.eq(b)].sort_values("outcome_year")
        for metric in ("mae", "rmse", "positive_mae", "mass_capture20"):
            summary_metric = "mean_annual_mass_capture20" if metric == "mass_capture20" else metric
            av, bv = indexed.loc[a, summary_metric], indexed.loc[b, summary_metric]
            delta = aa[metric].to_numpy() - bb[metric].to_numpy()
            differences.append(dict(model=a, baseline=b, metric=metric, difference=av-bv,
                                    percent_difference=100*(av-bv)/bv if bv else np.nan,
                                    wins=int((delta > 0 if metric == "mass_capture20" else delta < 0).sum()),
                                    ties=int((delta == 0).sum()), years=len(delta)))
    pd.DataFrame(differences).to_csv(report_dir / "paired_differences.csv", index=False)
    # Pooled subgroup scores complement annual subgroup metrics; groups may overlap.
    groups = {"inside_range": ~pooled.outside_range, "outside_range": pooled.outside_range,
              "hot": pooled.hot, "dry": pooled.dry, "neither_hot_nor_dry": ~(pooled.hot | pooled.dry)}
    subgroup_rows = []
    for group, mask in groups.items():
        for name in MODELS:
            subgroup_rows.append(dict(group=group, model=name,
                **(metrics(pooled.loc[mask, TARGET_COLUMN].to_numpy(), pooled.loc[mask, name].to_numpy())
                   if mask.any() else empty_metrics())))
    pd.DataFrame(subgroup_rows).to_csv(report_dir / "subgroups_pooled.csv", index=False)
    return annual, summary


def plot_results(report_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    annual = pd.read_csv(report_dir / "metrics_by_year.csv")
    names = {"zero": "Zero", "recurrence": "Recurrence", "hgb_hurdle": "Current HGB hurdle",
             "rf_direct": "Direct RF", "rf_hurdle": "RF hurdle"}
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for name, label in names.items():
        g = annual.loc[annual.model.eq(name)]
        for ax, metric in zip(axes.flat, ("mae", "rmse", "positive_mae", "mass_capture20")):
            ax.plot(g.outcome_year, g[metric], marker="o", ms=3, label=label)
    for ax, title in zip(axes.flat, ("All-cell MAE", "All-cell RMSE", "MAE on burned cells", "Annual top-20% mass capture")):
        ax.set_title(title); ax.set_xlabel("Outcome year"); ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Retrospective full-grid comparison: labels through Y-2")
    fig.savefig(report_dir / "yearly_metrics.png", dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(11, 5), constrained_layout=True)
    g = annual.loc[annual.model.eq("zero")]
    ax.plot(g.outcome_year, g.observed_burned_ha, "k-o", label="Observed", linewidth=2)
    for name, label in {**names, "training_mean": "Training mean"}.items():
        if name == "zero":
            continue
        g = annual.loc[annual.model.eq(name)]
        ax.plot(g.outcome_year, g.predicted_burned_ha, marker=".", label=label)
    ax.set(xlabel="Outcome year", ylabel="Panel burned hectares", title="National quantities from cell land-area weights")
    ax.legend(fontsize=8); ax.grid(alpha=.2)
    fig.savefig(report_dir / "national_totals.png", dpi=150); plt.close(fig)
    sub = pd.read_csv(report_dir / "subgroups_by_year.csv")
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for group, style in (("inside_range", "-"), ("outside_range", "--")):
        for name in LEARNED:
            g = sub.loc[sub.group.eq(group) & sub.model.eq(name)]
            for ax, metric in zip(axes.flat, ("mae", "positive_mae", "mass_capture20", "rows")):
                if metric == "rows" and name != "hgb_hurdle":
                    continue
                ax.plot(g.outcome_year, g[metric], style, marker=".", label=f"{names[name]} / {group}")
    for ax, title in zip(axes.flat, ("MAE", "Burned-cell MAE", "Top-20% mass capture within subgroup", "Subgroup rows")):
        ax.set_title(title); ax.set_xlabel("Outcome year"); ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=7)
    fig.suptitle("Marginal feature ranges: descriptive comparison, not causal evidence")
    fig.savefig(report_dir / "unfamiliar_conditions.png", dpi=150); plt.close(fig)
    response = pd.read_csv(report_dir / "response_predictions.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    for ax, diagnostic in zip(axes, ("training_anchor_interpolation", "synthetic_hot_dry_stress")):
        for name in LEARNED:
            g = response.loc[response.diagnostic.eq(diagnostic)]
            ax.plot(g.axis, g[name], label=names[name])
        ax.set_ylabel("Predicted burned share"); ax.grid(alpha=.2)
    axes[0].set(xlabel="Path between real cool / median / hot training rows", title="Training-anchored synthetic interpolation")
    axes[1].set(xlabel="Added temperature (C), jointly decreasing rain / soil water", title="Synthetic hot/dry stress: not forecast accuracy")
    axes[0].legend(fontsize=8)
    fig.savefig(report_dir / "response_diagnostics.png", dpi=150); plt.close(fig)


def run(run_name):
    if not run_name.replace("_", "").isalnum():
        raise ValueError("Use letters, digits and underscores in run name")
    report_dir = ROOT / "reports/research" / run_name
    data_dir = ROOT / "data/processed/research" / run_name
    if report_dir.exists() or data_dir.exists():
        raise FileExistsError("A unique new run directory is required")
    report_dir.mkdir(parents=True); data_dir.mkdir(parents=True)
    started = time.perf_counter()
    protected = protected_inventory()
    # Preserve every pre-existing source-audit change as well as operational files.
    extra_paths = [ROOT / "docs/source_plan.md", ROOT / "docs/data_source_audit_2026_10_24.md"]
    for directory in (ROOT / "reports/research/source_audit_2026_10_24", ROOT / "reports/research/source_availability_checks"):
        extra_paths.extend(p for p in directory.rglob("*") if p.is_file())
    protected.update({p.relative_to(ROOT).as_posix(): sha256(p) for p in extra_paths if p.is_file()})
    write_json(data_dir / "protected_before.json", protected)
    (report_dir / "protocol.md").write_bytes(PROTOCOL.read_bytes())
    configurations = {name: parameter_record(make_model(name)) for name in MODELS}
    manifest = dict(status="running", run_name=run_name, started_utc=datetime.now(timezone.utc).isoformat(),
        git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        git_branch=subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        git_status_before=subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True),
        features=list(PREDICTOR_COLUMNS), target=TARGET_COLUMN, model_seed=RANDOM_SEED,
        bootstrap_seed=20261024, configurations=configurations,
        protocol_sha256=sha256(PROTOCOL),
        versions={"python": platform.python_version(), **{p: importlib.metadata.version(p)
            for p in ("numpy", "pandas", "scikit-learn", "joblib", "pyarrow", "threadpoolctl", "matplotlib")}},
        platform=platform.platform(),
        historical_availability="NOT VERIFIED: revised vintages, no complete issue-date receipt ledger",
        evaluation_status="retrospective; reused development years; no forecast published")
    code_paths = [Path(__file__), ROOT / "scripts/run_random_forest_experiment.py", PROTOCOL,
                  ROOT / "src/forecast_review.py", ROOT / "src/modeling.py", ROOT / "src/evaluation.py",
                  ROOT / "src/feature_contract.py", ROOT / "requirements.txt"]
    manifest["code_sha256"] = {p.relative_to(ROOT).as_posix(): sha256(p) for p in code_paths}
    write_json(report_dir / "run_manifest.json", manifest)
    frame, source_records = checked_panel()
    write_json(report_dir / "source_year_audit.json", dict(metadata_valid=True, actual_records=source_records,
              as_issued_eligible_folds=0, reason=manifest["historical_availability"]))
    areas, grid_paths = load_areas(frame)
    frame["land_area_m2"] = frame.cell_id.map(areas)
    national = frame.assign(burned_m2=frame[TARGET_COLUMN] * frame.land_area_m2).groupby("outcome_year").agg(
        burned_m2=("burned_m2", "sum"), land_m2=("land_area_m2", "sum"))
    national["share"] = national.burned_m2 / national.land_m2
    national.to_csv(report_dir / "national_observed_history.csv")
    # Read the saved operational model to verify the actual current specification.
    operational_path = ROOT / "data/processed/final_model_2010_2024/nine_feature_hurdle.joblib"
    artifact = joblib.load(operational_path)
    operational = artifact["model"] if isinstance(artifact, dict) else artifact
    if not isinstance(operational, HurdleHistGradientRegressor):
        raise ValueError("Saved current model is not the expected HGB hurdle")
    if parameter_record(operational) != configurations["hgb_hurdle"]:
        raise ValueError("Refit specification differs from current saved model")
    require_features(pd.DataFrame(columns=operational.occurrence_model.feature_names_in_))
    write_json(report_dir / "saved_model_audit.json", dict(type=type(operational).__name__,
        parameters_match=True, feature_order_match=True, artifact_sha256=sha256(operational_path),
        prediction_formula="occurrence probability times clipped conditional positive burned share"))
    del operational, artifact
    manifest["input_sha256"] = {p.relative_to(ROOT).as_posix(): sha256(p)
                                for p in [*MATRICES, *grid_paths, operational_path]}
    write_json(report_dir / "run_manifest.json", manifest)
    annual, subgroup, bounds_rows, folds, response = [], [], [], [], None
    for year in range(2016, 2026):
        train, test = split_fold(frame, year)
        if train.outcome_year.max() != year-2 or not test.observation_year.eq(year-1).all():
            raise ValueError("Temporal fold violation")
        X, Xt = train.loc[:, PREDICTOR_COLUMNS], test.loc[:, PREDICTOR_COLUMNS]
        y, yt = train[TARGET_COLUMN], test[TARGET_COLUMN].to_numpy()
        flags, bounds = range_diagnostics(X, Xt)
        bounds["outcome_year"] = year; bounds_rows.append(bounds)
        output = test[["cell_id", "observation_year", "outcome_year", TARGET_COLUMN, "land_area_m2"]].copy()
        for column in flags:
            output[column] = flags[column]
        group_masks = {"inside_range": ~flags.outside_range, "outside_range": flags.outside_range,
                       "hot": flags.hot, "dry": flags.dry, "neither_hot_nor_dry": ~(flags.hot | flags.dry)}
        history_threshold = float(national.loc[national.index <= year-2, "share"].quantile(.9))
        severe = bool(national.loc[year, "share"] > history_threshold)
        fold = dict(outcome_year=year, predictor_year=year-1, first_training_outcome=2011,
                    last_training_outcome=year-2, training_rows=len(train), evaluation_rows=len(test),
                    issue_utc=f"{year-1}-12-31T12:00:00Z", cutoff_utc=f"{year-1}-12-30T23:59:59Z",
                    historical_availability_verified=False, severe_outcome=severe,
                    severe_threshold_training_national_q90=history_threshold,
                    outside_range_rows=int(flags.outside_range.sum()), hot_rows=int(flags.hot.sum()), dry_rows=int(flags.dry.sum()))
        folds.append(fold)
        if year == 2025:
            response = response_inputs(X)
        print(f"Outcome {year}: full training {len(train):,}, evaluation {len(test):,}", flush=True)
        for name in MODELS:
            model = make_model(name)
            scoring = test[["cell_id", *PREDICTOR_COLUMNS]] if name in BASELINES else Xt
            with threadpool_limits(limits=1):
                tick = time.perf_counter()
                if name in BASELINES:
                    model.fit(train)
                else:
                    require_features(X); model.fit(X, y)
                fit_seconds = time.perf_counter() - tick
                tick = time.perf_counter(); pred = model.predict(scoring)
                predict_seconds = time.perf_counter() - tick
            if pred.shape != yt.shape or not np.isfinite(pred).all() or ((pred < 0) | (pred > 1)).any():
                raise ValueError("Invalid or unaligned model predictions")
            output[name] = pred
            model_path = data_dir / f"{name}_{year}.joblib"
            joblib.dump(dict(model=model, features=list(PREDICTOR_COLUMNS), fold=fold), model_path, compress=0)
            size = model_path.stat().st_size
            reloaded = joblib.load(model_path)["model"]
            with threadpool_limits(limits=1):
                replay = reloaded.predict(scoring)
            np.testing.assert_allclose(pred, replay, rtol=0, atol=1e-12)
            del reloaded
            predicted = float(np.average(pred, weights=test.land_area_m2))
            annual.append(dict(outcome_year=year, model=name, **metrics(yt, pred),
                national_predicted=predicted, national_observed=float(national.loc[year, "share"]),
                predicted_burned_ha=float(np.sum(pred * test.land_area_m2) / 10000),
                observed_burned_ha=float(national.loc[year, "burned_m2"] / 10000),
                fit_seconds=fit_seconds, predict_seconds=predict_seconds, model_bytes=size,
                severe_outcome=severe))
            for group, mask in group_masks.items():
                mask = mask.to_numpy()
                subgroup.append(dict(outcome_year=year, model=name, group=group,
                    **(metrics(yt[mask], pred[mask]) if mask.any() else empty_metrics())))
            if response is not None and name in LEARNED:
                with threadpool_limits(limits=1):
                    response[name] = model.predict(response.loc[:, PREDICTOR_COLUMNS])
            print(f"  {name}: fit {fit_seconds:.1f}s, predict {predict_seconds:.2f}s, {size/1e6:.1f} MB", flush=True)
            del model; gc.collect()
        output.to_parquet(data_dir / f"predictions_{year}.parquet", index=False, compression="zstd")
        pd.DataFrame(annual).to_csv(report_dir / "metrics_by_year.csv", index=False)
        pd.DataFrame(subgroup).to_csv(report_dir / "subgroups_by_year.csv", index=False)
        pd.concat(bounds_rows).to_csv(report_dir / "feature_ranges.csv", index=False)
        pd.DataFrame(folds).to_csv(report_dir / "folds.csv", index=False)
        del train, test, X, Xt, output; gc.collect()
    response.to_csv(report_dir / "response_predictions.csv", index=False)
    summarize(report_dir, data_dir)
    plot_results(report_dir)
    if protected != {path: sha256(ROOT / path) for path in protected}:
        raise RuntimeError("Protected artifacts changed")
    if manifest["code_sha256"] != {p.relative_to(ROOT).as_posix(): sha256(p) for p in code_paths}:
        raise RuntimeError("Experiment code changed during execution")
    manifest.update(status="complete", completed_utc=datetime.now(timezone.utc).isoformat(),
                    elapsed_seconds=time.perf_counter()-started, folds=folds,
                    protected_file_count=len(protected), protected_files_unchanged=True,
                    model_reload_full_grid_checks=80,
                    artifact_sha256={p.relative_to(ROOT).as_posix(): sha256(p) for p in data_dir.iterdir() if p.is_file()},
                    result_sha256={p.relative_to(ROOT).as_posix(): sha256(p) for p in report_dir.iterdir()
                                   if p.is_file() and p.name != "run_manifest.json"})
    write_json(report_dir / "run_manifest.json", manifest)
    return manifest
