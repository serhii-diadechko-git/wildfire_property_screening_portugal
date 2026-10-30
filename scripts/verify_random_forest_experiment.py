"""Independently verify the complete RF experiment from keyed saved predictions.

The NumPy metric implementation below does not call the experiment evaluator.
Optional full-fold RF refits must be run after the main experiment completes.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.feature_contract import PREDICTOR_COLUMNS, TARGET_COLUMN
from src.random_forest_experiment import MODELS, make_model


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def equal(a, b, label, atol=1e-11):
    np.testing.assert_allclose(a, b, rtol=0, atol=atol, equal_nan=True, err_msg=label)


def independent_metrics(y, prediction):
    """Exact fractional-boundary ranking via NumPy order statistics."""
    y, prediction = np.asarray(y, dtype=float), np.asarray(prediction, dtype=float)
    assert y.shape == prediction.shape and y.ndim == 1
    assert np.isfinite(y).all() and np.isfinite(prediction).all()
    assert ((prediction >= 0) & (prediction <= 1)).all()
    positive = y > 0
    e = prediction - y
    budget = .2 * len(y)
    boundary = np.sort(prediction)[::-1][int(np.ceil(budget)) - 1]
    above, tied = prediction > boundary, prediction == boundary
    tied_weight = (budget - above.sum()) / tied.sum()
    selected_mass = y[above].sum() + tied_weight * y[tied].sum()
    selected_positive = positive[above].sum() + tied_weight * positive[tied].sum()
    return dict(
        rows=len(y), positive_rows=int(positive.sum()), zero_fraction=float((~positive).mean()),
        mae=float(np.abs(e).mean()), rmse=float(np.sqrt(np.square(e).mean())),
        positive_mae=float(np.abs(e[positive]).mean()) if positive.any() else np.nan,
        positive_rmse=float(np.sqrt(np.square(e[positive]).mean())) if positive.any() else np.nan,
        zero_mae=float(np.abs(e[~positive]).mean()) if (~positive).any() else np.nan,
        observed_mean=float(y.mean()), predicted_mean=float(prediction.mean()), bias=float(e.mean()),
        predicted_observed_ratio=float(prediction.sum() / y.sum()) if y.sum() else np.nan,
        mass_capture20=float(selected_mass / y.sum()) if y.sum() else np.nan,
        positive_capture20=float(selected_positive / positive.sum()) if positive.any() else np.nan,
    )


def verify_table_row(row, calculated, label):
    for key, value in calculated.items():
        equal(float(row[key]), value, f"{label}: {key}")


def verify(run_name, refit_year=None):
    if not run_name.replace("_", "").isalnum():
        raise ValueError("Use an existing alphanumeric/underscore run name")
    report = ROOT / "reports/research" / run_name
    data = ROOT / "data/processed/research" / run_name
    manifest = json.loads((report / "run_manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "complete":
        raise RuntimeError("The main experiment must complete before verification or refitting")
    started = time.perf_counter()
    hash_counts = {}
    for category in ("input_sha256", "code_sha256", "artifact_sha256", "result_sha256"):
        for path, expected in manifest[category].items():
            assert digest(ROOT / path) == expected, f"Changed {category}: {path}"
        hash_counts[category] = len(manifest[category])
    protected = json.loads((data / "protected_before.json").read_text(encoding="utf-8"))
    for path, expected in protected.items():
        assert digest(ROOT / path) == expected, f"Changed protected artifact: {path}"
    hash_counts["protected"] = len(protected)

    source_root = ROOT / "data/processed/extended_model_selection_2010_2021"
    source_paths = [source_root / "nine_feature_train_validation_matrix.parquet",
                    source_root / "final_temporal_test_nine_feature_matrix.parquet"]
    keys = ["cell_id", "observation_year", "outcome_year"]
    source_columns = [*keys, *PREDICTOR_COLUMNS, TARGET_COLUMN,
                      "historical_fire_start_year", "historical_fire_end_year",
                      "climate_reference_year", "land_cover_reference_year"]
    source = pd.concat([pd.read_parquet(p, columns=source_columns) for p in source_paths], ignore_index=True)
    source = source.sort_values(["outcome_year", "cell_id"]).reset_index(drop=True)
    assert not source.duplicated(keys).any()
    assert source.outcome_year.eq(source.observation_year + 1).all()
    assert source.historical_fire_start_year.eq(source.observation_year - 10).all()
    assert source.historical_fire_end_year.eq(source.observation_year - 1).all()
    assert source.climate_reference_year.eq(source.observation_year).all()
    assert source.land_cover_reference_year.le(source.observation_year).all()
    assert np.isfinite(source[[*PREDICTOR_COLUMNS, TARGET_COLUMN]].to_numpy()).all()
    assert source[TARGET_COLUMN].between(0, 1).all()
    catalog = json.loads((ROOT / "data/interim/national_panel_2015_2024/grid_catalog.json").read_text())
    areas = pd.concat([pd.read_parquet(ROOT / b["path"], columns=["cell_id", "land_area_m2"])
                       for b in catalog["batches"]]).set_index("cell_id").land_area_m2
    assert areas.index.is_unique and areas.gt(0).all()
    assert len(areas) == 89112
    assert source.groupby("outcome_year").cell_id.nunique().eq(89112).all()
    national_history = pd.Series({
        year: np.average(group[TARGET_COLUMN], weights=group.cell_id.map(areas))
        for year, group in source.groupby("outcome_year")
    })
    annual = pd.read_csv(report / "metrics_by_year.csv").set_index(["outcome_year", "model"])
    subgroup = pd.read_csv(report / "subgroups_by_year.csv").set_index(["outcome_year", "model", "group"])
    bounds = pd.read_csv(report / "feature_ranges.csv").set_index(["outcome_year", "feature"])
    folds = pd.read_csv(report / "folds.csv").set_index("outcome_year")
    assert annual.index.is_unique and subgroup.index.is_unique and bounds.index.is_unique
    assert len(annual) == 80 and len(folds) == 10
    predictions = []
    subgroup_checks = 0
    refits = {}
    prior_comparison_count = 0
    bootstrap_statistics = {name: [] for name in MODELS}
    for year in range(2016, 2026):
        out = pd.read_parquet(data / f"predictions_{year}.parquet")
        truth = source.loc[source.outcome_year.eq(year)]
        assert len(out) == 89112 and not out.duplicated(keys).any()
        pd.testing.assert_frame_equal(out[keys].reset_index(drop=True), truth[keys].reset_index(drop=True))
        equal(out[TARGET_COLUMN], truth[TARGET_COLUMN], f"{year} source targets", atol=0)
        equal(out.land_area_m2, out.cell_id.map(areas), f"{year} area weights", atol=0)
        previous_path = ROOT / f"data/processed/research/forecast_review_v2/predictions_{year}.parquet"
        if previous_path.exists():
            previous = pd.read_parquet(previous_path).sort_values(["outcome_year", "cell_id"])
            pd.testing.assert_frame_equal(out[keys].reset_index(drop=True), previous[keys].reset_index(drop=True))
            for current_name, prior_name in (
                ("zero", "zero"), ("training_mean", "training_mean"),
                ("cell_training_mean", "cell_training_mean"), ("latest_available_year", "latest_available_year"),
                ("recurrence", "recurrence"), ("hgb_hurdle", "hurdle_published_parameters"),
            ):
                equal(out[current_name], previous[prior_name], f"{year}/{current_name} accepted prior evidence", atol=1e-12)
                prior_comparison_count += 1
            del previous
        training = source.loc[source.outcome_year <= year - 2]
        assert training.outcome_year.max() == year - 2
        assert set(training.cell_id) == set(out.cell_id)
        assert len(training) == 89112 * (year - 2012)
        assert folds.loc[year, "training_rows"] == len(training)
        assert folds.loc[year, "last_training_outcome"] == year - 2
        assert folds.loc[year, "evaluation_rows"] == len(out)
        assert not bool(folds.loc[year, "historical_availability_verified"])
        severe_threshold = national_history.loc[national_history.index <= year - 2].quantile(.9)
        equal(folds.loc[year, "severe_threshold_training_national_q90"], severe_threshold, "severe threshold")
        severe = bool(national_history.loc[year] > severe_threshold)
        assert bool(folds.loc[year, "severe_outcome"]) == severe
        X, Xt = training.loc[:, PREDICTOR_COLUMNS], truth.loc[:, PREDICTOR_COLUMNS]
        minimum, maximum = X.min(), X.max()
        q10, q90 = X.quantile(.1), X.quantile(.9)
        outside = ((Xt < minimum) | (Xt > maximum)).any(axis=1).to_numpy()
        hot = (Xt[PREDICTOR_COLUMNS[4]] > q90[PREDICTOR_COLUMNS[4]]).to_numpy()
        dry = ((Xt[PREDICTOR_COLUMNS[5]] < q10[PREDICTOR_COLUMNS[5]]) |
               (Xt[PREDICTOR_COLUMNS[6]] < q10[PREDICTOR_COLUMNS[6]])).to_numpy()
        for name, flag in (("outside_range", outside), ("hot", hot), ("dry", dry)):
            np.testing.assert_array_equal(out[name], flag)
            assert folds.loc[year, f"{name}_rows"] == int(flag.sum())
        for feature in PREDICTOR_COLUMNS:
            record = bounds.loc[(year, feature)]
            verify_table_row(record, dict(train_min=minimum[feature], train_max=maximum[feature],
                train_q10=q10[feature], train_q90=q90[feature],
                test_below=int((Xt[feature] < minimum[feature]).sum()),
                test_above=int((Xt[feature] > maximum[feature]).sum())), f"{year}/{feature}")
        groups = dict(inside_range=~outside, outside_range=outside, hot=hot, dry=dry,
                      neither_hot_nor_dry=~(hot | dry))
        y = out[TARGET_COLUMN].to_numpy()
        weights = out.land_area_m2.to_numpy()
        equal(out.zero, np.zeros(len(out)), f"{year} zero baseline", atol=0)
        equal(out.training_mean, np.full(len(out), training[TARGET_COLUMN].mean()), f"{year} training mean")
        equal(out.cell_training_mean, out.cell_id.map(training.groupby("cell_id")[TARGET_COLUMN].mean()), f"{year} cell means")
        latest = training.loc[training.outcome_year.eq(year - 2)].set_index("cell_id")[TARGET_COLUMN]
        equal(out.latest_available_year, out.cell_id.map(latest), f"{year} delayed latest baseline", atol=0)
        recurrence_means = training.groupby(PREDICTOR_COLUMNS[3])[TARGET_COLUMN].mean()
        recurrence = Xt[PREDICTOR_COLUMNS[3]].map(recurrence_means).fillna(training[TARGET_COLUMN].mean())
        equal(out.recurrence, recurrence, f"{year} training-only recurrence")
        for name in MODELS:
            p = out[name].to_numpy()
            recorded = annual.loc[(year, name)]
            calculated = independent_metrics(y, p)
            verify_table_row(recorded, calculated, f"{year}/{name}")
            bootstrap_statistics[name].append(dict(
                rows=len(y), positive_rows=int((y > 0).sum()),
                absolute_error_sum=float(np.abs(p-y).sum()),
                squared_error_sum=float(np.square(p-y).sum()),
                positive_absolute_error_sum=float(np.abs(p[y > 0]-y[y > 0]).sum()),
                mass_capture20=calculated["mass_capture20"],
            ))
            equal(recorded.national_observed, np.average(y, weights=weights), f"{year} national truth")
            equal(recorded.national_predicted, np.average(p, weights=weights), f"{year}/{name} national prediction")
            equal(recorded.observed_burned_ha, np.sum(y * weights) / 10000, f"{year} observed hectares", atol=1e-7)
            equal(recorded.predicted_burned_ha, np.sum(p * weights) / 10000, f"{year}/{name} predicted hectares", atol=1e-7)
            assert recorded.model_bytes == (data / f"{name}_{year}.joblib").stat().st_size
            assert recorded.fit_seconds >= 0 and recorded.predict_seconds >= 0
            assert bool(recorded.severe_outcome) == severe
            for group, mask in groups.items():
                row = subgroup.loc[(year, name, group)]
                if mask.any():
                    verify_table_row(row, independent_metrics(y[mask], p[mask]), f"{year}/{name}/{group}")
                else:
                    assert row.rows == 0 and row.positive_rows == 0
                subgroup_checks += 1
        if refit_year == year:
            for name in ("rf_direct", "rf_hurdle"):
                start = time.perf_counter()
                model = make_model(name)
                with threadpool_limits(limits=1):
                    model.fit(X, training[TARGET_COLUMN])
                    replay = model.predict(Xt)
                maximum_difference = float(np.max(np.abs(replay - out[name].to_numpy())))
                equal(replay, out[name], f"{year}/{name} full-data refit", atol=1e-12)
                refits[name] = dict(outcome_year=year, training_rows=len(training), evaluation_rows=len(out),
                                   max_absolute_prediction_difference=maximum_difference,
                                   elapsed_seconds=time.perf_counter() - start)
                del model
                gc.collect()
        predictions.append(out)
        del training, X, Xt
        print(f"Independently verified outcome {year}", flush=True)
    pooled = pd.concat(predictions, ignore_index=True)
    assert len(pooled) == 891120 and not pooled.duplicated(keys).any()
    summary = pd.read_csv(report / "metrics_pooled.csv").set_index("model")
    assert set(summary.index) == set(MODELS)
    for name in MODELS:
        verify_table_row(summary.loc[name], independent_metrics(pooled[TARGET_COLUMN], pooled[name]), f"pooled/{name}")
        annual_model = annual.xs(name, level="model")
        equal(summary.loc[name, "mean_annual_mass_capture20"], annual_model.mass_capture20.mean(), name)
        equal(summary.loc[name, "national_mae"], np.abs(annual_model.national_predicted - annual_model.national_observed).mean(), name)
        equal(summary.loc[name, "national_rmse"], np.sqrt(np.square(annual_model.national_predicted - annual_model.national_observed).mean()), name)
    sub_pooled = pd.read_csv(report / "subgroups_pooled.csv").set_index(["model", "group"])
    group_masks = dict(inside_range=~pooled.outside_range, outside_range=pooled.outside_range,
                      hot=pooled.hot, dry=pooled.dry, neither_hot_nor_dry=~(pooled.hot | pooled.dry))
    for group, mask in group_masks.items():
        for name in MODELS:
            row = sub_pooled.loc[(name, group)]
            if mask.any():
                verify_table_row(row, independent_metrics(pooled.loc[mask, TARGET_COLUMN], pooled.loc[mask, name]), f"pooled/{name}/{group}")
            else:
                assert row.rows == 0
            subgroup_checks += 1
    differences = pd.read_csv(report / "paired_differences.csv")
    intervals = pd.read_csv(report / "paired_uncertainty.csv")
    for row in differences.itertuples():
        metric = "mean_annual_mass_capture20" if row.metric == "mass_capture20" else row.metric
        expected = summary.loc[row.model, metric] - summary.loc[row.baseline, metric]
        equal(row.difference, expected, f"difference/{row.model}/{row.baseline}/{metric}")
        delta = annual.xs(row.model, level="model")[row.metric] - annual.xs(row.baseline, level="model")[row.metric]
        assert row.wins == int((delta > 0 if row.metric == "mass_capture20" else delta < 0).sum())
    # Independently aggregate raw annual error sums with resampled year multiplicities.
    # This differs from the runner's weighted means of precomputed metric tables.
    samples = {}
    for block in (1, 2, 3):
        rng = np.random.default_rng(manifest["bootstrap_seed"])
        starts = rng.integers(10, size=(4000, int(np.ceil(10 / block))))
        draws = [[(int(start) + step) % 10 for start in row for step in range(block)][:10]
                 for row in starts]
        counts = np.array([np.bincount(draw, minlength=10) for draw in draws])
        for name in MODELS:
            stats = pd.DataFrame(bootstrap_statistics[name])
            total_rows = counts @ stats.rows.to_numpy()
            total_positive = counts @ stats.positive_rows.to_numpy()
            samples[(name, block, "mae")] = (counts @ stats.absolute_error_sum.to_numpy()) / total_rows
            samples[(name, block, "rmse")] = np.sqrt((counts @ stats.squared_error_sum.to_numpy()) / total_rows)
            samples[(name, block, "positive_mae")] = (counts @ stats.positive_absolute_error_sum.to_numpy()) / total_positive
            samples[(name, block, "mass_capture20")] = (counts @ stats.mass_capture20.to_numpy()) / 10
    for row in intervals.itertuples():
        metric = "mean_annual_mass_capture20" if row.metric == "mass_capture20" else row.metric
        equal(row.difference, summary.loc[row.model, metric] - summary.loc[row.baseline, metric], "interval point")
        assert row.lower95 <= row.upper95 and row.years == 10 and row.replicates == 4000
        assert row.block_years in (1, 2, 3)
        delta_samples = samples[(row.model, row.block_years, row.metric)] - samples[(row.baseline, row.block_years, row.metric)]
        equal([row.lower95, row.upper95], np.quantile(delta_samples, [.025, .975]), "independent paired interval")
    responses = pd.read_csv(report / "response_predictions.csv")
    assert responses.diagnostic.value_counts().to_dict() == {
        "training_anchor_interpolation": 42, "synthetic_hot_dry_stress": 33}
    assert np.isfinite(responses.loc[:, PREDICTOR_COLUMNS].to_numpy()).all()
    assert responses[PREDICTOR_COLUMNS[0]].between(0, 1).all()
    assert responses[PREDICTOR_COLUMNS[1]].between(0, 1).all()
    assert responses[PREDICTOR_COLUMNS[2]].between(0, 90).all()
    assert responses[PREDICTOR_COLUMNS[3]].between(0, 10).all()
    equal(responses[PREDICTOR_COLUMNS[3]], np.round(responses[PREDICTOR_COLUMNS[3]]), "integer fire history", atol=0)
    assert responses[PREDICTOR_COLUMNS[5]].ge(0).all()
    assert (responses[PREDICTOR_COLUMNS[7]] >= responses[PREDICTOR_COLUMNS[4]] - 1e-12).all()
    assert responses[PREDICTOR_COLUMNS[6]].between(0, 1).all()
    assert responses[PREDICTOR_COLUMNS[8]].between(0, 1).all()
    assert (responses[PREDICTOR_COLUMNS[8]] <= responses[PREDICTOR_COLUMNS[6]] + 1e-12).all()
    for name in ("hgb_hurdle", "rf_direct", "rf_hurdle"):
        assert responses[name].between(0, 1).all()
    result = dict(status="passed", verified_utc=datetime.now(timezone.utc).isoformat(), run_name=run_name,
                  verifier_sha256=digest(Path(__file__)), elapsed_seconds=time.perf_counter()-started,
                  independent_numpy_metrics=True, independent_source_and_area_alignment=True,
                  independent_paired_year_block_intervals=True,
                  independent_train_only_range_flags=True, full_grid_rows=len(pooled),
                  annual_model_results=len(annual), subgroup_results=subgroup_checks,
                  prior_accepted_full_grid_model_year_comparisons=prior_comparison_count,
                  synthetic_response_rows_basic_physical_checks=len(responses),
                  hashes_checked=hash_counts, full_fold_refits=refits,
                  limitations=["Historical publication-time availability remains unverified.",
                               "Metric bootstrap does not establish future prediction coverage or remove reused-year bias."])
    output = report / ("independent_verification_refit.json" if refit_year is not None else "independent_verification.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--refit-year", type=int, choices=range(2016, 2026))
    args = parser.parse_args()
    verify(args.run_name, args.refit_year)
