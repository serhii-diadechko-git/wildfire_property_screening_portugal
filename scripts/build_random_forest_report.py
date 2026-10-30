"""Build reviewable tables and a report from a completed, immutable RF run."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from src.forecast_review import ROOT, sha256, write_json
from src.random_forest_experiment import LEARNED, MODELS

LABELS = dict(zero="Zero", training_mean="Training mean", cell_training_mean="Cell historical mean",
              latest_available_year="Latest available outcome", recurrence="Recurrence",
              hgb_hurdle="Current HGB hurdle", rf_direct="Direct RF", rf_hurdle="RF hurdle")


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"]*len(headers)) + " |",
                      *["| " + " | ".join(map(str, row)) + " |" for row in rows]])


def build(run_name):
    import json
    report = ROOT / "reports/research" / run_name
    manifest = json.loads((report / "run_manifest.json").read_text())
    if manifest["status"] != "complete":
        raise ValueError("Only completed runs can be reported")
    annual = pd.read_csv(report / "metrics_by_year.csv")
    summary = pd.read_csv(report / "metrics_pooled.csv").set_index("model")
    differences = pd.read_csv(report / "paired_differences.csv")
    uncertainty = pd.read_csv(report / "paired_uncertainty.csv")
    folds = pd.read_csv(report / "folds.csv")
    sub = pd.read_csv(report / "subgroups_pooled.csv")
    annual_sub = pd.read_csv(report / "subgroups_by_year.csv").groupby(["group", "model"]).agg(
        years_with_defined_capture=("mass_capture20", "count"),
        mean_annual_capture=("mass_capture20", "mean"),
        mean_annual_positive_mae=("positive_mae", "mean")).reset_index()
    annual_sub.to_csv(report / "subgroups_annual_summary.csv", index=False)
    def contrast(model, baseline, metric):
        row = differences.loc[differences.model.eq(model) & differences.baseline.eq(baseline) & differences.metric.eq(metric)].iloc[0]
        ci = uncertainty.loc[uncertainty.model.eq(model) & uncertainty.baseline.eq(baseline)
                             & uncertainty.metric.eq(metric) & uncertainty.block_years.eq(2)].iloc[0]
        return row, ci
    decisions = []
    for model in LEARNED:
        d, ci = contrast(model, "recurrence", "mass_capture20")
        useful = bool(d.difference >= .05 and ci.lower95 > 0 and d.wins >= 7)
        decisions.append(dict(model=model, criterion="useful_ranking_vs_recurrence", passed=useful,
                              capture_gain=d.difference, winning_years=int(d.wins), interval_low=ci.lower95,
                              interval_high=ci.upper95))
        if model != "hgb_hurdle":
            d, ci = contrast(model, "hgb_hurdle", "mass_capture20")
            rmse = summary.loc[model, "rmse"] / summary.loc["hgb_hurdle", "rmse"] - 1
            pos = summary.loc[model, "positive_mae"] / summary.loc["hgb_hurdle", "positive_mae"] - 1
            better = bool(d.difference >= .02 and ci.lower95 > 0 and d.wins >= 7 and rmse <= .01 and pos <= .01)
            decisions.append(dict(model=model, criterion="improves_current_hgb", passed=better,
                capture_gain=d.difference, winning_years=int(d.wins), interval_low=ci.lower95,
                interval_high=ci.upper95, relative_rmse_change=rmse, relative_positive_mae_change=pos))
    pd.DataFrame(decisions).to_csv(report / "decision_checks.csv", index=False)
    severe = annual.loc[annual.severe_outcome & annual.model.isin(LEARNED)].copy()
    severe["national_percent_error"] = 100*(severe.national_predicted / severe.national_observed - 1)
    severe.to_csv(report / "severe_years.csv", index=False)
    yearly = annual.loc[annual.model.isin(("recurrence", *LEARNED)),
                        ["outcome_year", "model", "mae", "rmse", "positive_mae", "mass_capture20",
                         "national_observed", "national_predicted", "severe_outcome"]]
    yearly.to_csv(report / "year_summary.csv", index=False)
    main_table = table(["Model", "Pooled MAE", "Pooled RMSE", "Burned-cell MAE", "Mean annual capture", "Pooled capture"],
        [[LABELS[n], f"{summary.loc[n, 'mae']:.6f}", f"{summary.loc[n, 'rmse']:.6f}",
          f"{summary.loc[n, 'positive_mae']:.6f}", f"{100*summary.loc[n, 'mean_annual_mass_capture20']:.2f}%",
          f"{100*summary.loc[n, 'mass_capture20']:.2f}%"] for n in MODELS])
    comparison_rows = []
    for model, baseline in [(m, "recurrence") for m in LEARNED] + [(m, "hgb_hurdle") for m in LEARNED[1:]]:
        for metric in ("mae", "rmse", "positive_mae", "mass_capture20"):
            d, ci = contrast(model, baseline, metric)
            scale = 100 if metric == "mass_capture20" else 1
            unit = " pp" if scale == 100 else ""
            comparison_rows.append([f"{LABELS[model]} - {LABELS[baseline]}", metric,
                f"{d.difference*scale:+.5f}{unit}", f"[{ci.lower95*scale:+.5f}, {ci.upper95*scale:+.5f}]{unit}", f"{int(d.wins)}/10"])
    compare_table = table(["Comparison", "Metric", "Difference", "Descriptive 95% interval", "Years better"], comparison_rows)
    subgroup_table = table(["Group", "Rows", "Burned rows", "Model", "MAE", "Burned-cell MAE", "Pooled capture"],
        [[r.group, f"{r.rows:,}", f"{r.positive_rows:,}", LABELS[r.model], f"{r.mae:.6f}",
          f"{r.positive_mae:.6f}", f"{100*r.mass_capture20:.2f}%"]
         for r in sub.loc[sub.model.isin(LEARNED)].itertuples(index=False)])
    annual_sub_table = table(["Group", "Years", "Recurrence capture", "HGB capture", "Direct RF capture", "RF hurdle capture"],
        [[group, int(annual_sub.loc[annual_sub.group.eq(group), "years_with_defined_capture"].iloc[0]),
          *[f"{100*annual_sub.loc[annual_sub.group.eq(group) & annual_sub.model.eq(n), 'mean_annual_capture'].iloc[0]:.2f}%"
            for n in ("recurrence", *LEARNED)]]
         for group in ("inside_range", "outside_range", "hot", "dry", "neither_hot_nor_dry")])
    yearly_table = table(["Outcome", "Recurrence capture", "HGB capture", "Direct RF capture", "RF hurdle capture"],
        [[year, *[f"{100*annual.loc[annual.outcome_year.eq(year) & annual.model.eq(n), 'mass_capture20'].iloc[0]:.2f}%"
                   for n in ("recurrence", *LEARNED)]] for year in range(2016, 2026)])
    resource_table = table(["Model", "Total fit seconds", "Total predict seconds", "Mean saved MB", "National MAE", "National RMSE"],
        [[LABELS[n], f"{summary.loc[n, 'total_fit_seconds']:.1f}", f"{summary.loc[n, 'total_predict_seconds']:.2f}",
          f"{summary.loc[n, 'mean_model_bytes']/1e6:.2f}", f"{summary.loc[n, 'national_mae']:.6f}",
          f"{summary.loc[n, 'national_rmse']:.6f}"] for n in MODELS])
    severe_table = table(["Outcome", "Model", "Observed ha", "Predicted ha", "National error"],
        [[r.outcome_year, LABELS[r.model], f"{r.observed_burned_ha:,.0f}", f"{r.predicted_burned_ha:,.0f}",
          f"{r.national_percent_error:+.1f}%"] for r in severe.itertuples(index=False)])
    criteria_lines = "\n".join(f"- {LABELS[r['model']]}: {r['criterion']} = **{'passes' if r['passed'] else 'fails'}**."
                                for r in decisions)
    # Complement unfamiliar-range chart with the independently defined climate subsets.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    groups = ("hot", "dry", "neither_hot_nor_dry")
    for i, model in enumerate(LEARNED):
        g = sub.loc[sub.model.eq(model)].set_index("group").loc[list(groups)]
        a = annual_sub.loc[annual_sub.model.eq(model)].set_index("group").loc[list(groups)]
        axes[0].bar(np.arange(3) + (i-1)*.24, g.positive_mae, width=.24, label=LABELS[model])
        axes[1].bar(np.arange(3) + (i-1)*.24, a.mean_annual_capture, width=.24, label=LABELS[model])
    for ax, label in zip(axes, ("Pooled burned-cell MAE", "Mean annual subgroup top-20% mass capture")):
        ax.set_xticks(np.arange(3), ["Hot predictor summer", "Dry predictor summer", "Neither"])
        ax.tick_params(axis="x", labelsize=8); ax.set_ylabel(label); ax.grid(axis="y", alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle("Training-quantile climate groups: descriptive, overlapping hot/dry subsets")
    fig.savefig(report / "climate_subgroups.png", dpi=150); plt.close(fig)
    text = f"""# Random Forest in the Portugal wildfire capstone

Full retrospective experiment completed on 30 October 2026. Read the numerical
results below together with the interpretation in `conclusion.md`.

## What was actually run

Eight methods on every mainland cell in ten annual folds, outcomes 2016-2025:
**891,120 evaluation cell-years per method**, with 356,448 to 1,158,456 training
rows per fold. This includes five baselines, the unchanged current HGB hurdle,
direct Random Forest, and a two-stage Random Forest. Each RF stage has 48 trees,
depth at most 12 and at most 512 leaves. All use the same nine predictors.
No evaluated-year tuning, random cell-year split, or training-data subsampling
was performed. Standard per-tree RF bootstrapping was retained.

For outcome Y, training labels end at Y-2, scoring predictors are Y-1, and
fire history ends Y-2. The previous year is unfinished at the simulated December
cutoff. Historical publication dates are unverified: revised CLC, terrain,
boundary and climate assets cannot certify an as-issued forecast. These are
reused retrospective years, including years used to develop the HGB specification.
The old operational Y-1 training cutoff was not used here.

## Overall usefulness

{main_table}

Errors are shares from 0 to 1. Lower errors and higher capture are better.
**{100*summary.loc['zero', 'zero_fraction']:.2f}% of targets are zero**. Zero can
therefore have strong MAE without identifying useful areas. Capture means the
fraction of burned-share mass in the highest-scored 20% of cells, with fractional
boundary ties. It is not hectares or a count of burned cells. Mean annual capture
gives each year its own 20% budget; pooled capture is a different calculation.
Burned share is not fire probability.

Predeclared research screening criteria (not economic benefit or promotion):

{criteria_lines}

## Paired differences and consistency

{compare_table}

Negative error differences are better; positive capture differences are better.
Intervals resample paired whole-country two-year blocks 4,000 times, preserving
all spatial dependence within each year. One- and three-year block sensitivities
are in `paired_uncertainty.csv`. These are metric uncertainty, **not future
prediction intervals**. Ten temporal units are few; overlapping training histories,
longer dependence, model fitting uncertainty and test reuse are not eliminated.
Multiple exploratory comparisons have no multiplicity correction.

{yearly_table}

All annual MAE, RMSE, positive-cell MAE, zero fractions, timing and area-weighted
totals are in `metrics_by_year.csv`. `paired_differences.csv` compares every
learned model against all five baselines, plus RF versus HGB and each other.

## National quantities and severe years

{severe_table}

Severe years exceed the training-history 90th percentile of national observed
share; this uses outcomes only for retrospective diagnostics, never tuning.
Totals weight each cell by mainland land area and refer to this clipped panel,
not necessarily the exact official headline total.

## Unfamiliar inputs and hot/dry predictor summers

{subgroup_table}

The corresponding mean annual subgroup captures are:

{annual_sub_table}

Outside-range groups exist in seven years; the other three have zero rows and
undefined subgroup errors/capture. The inside-range mean uses all ten years,
so these group means are not paired estimates of a condition's effect. Both
annual and pooled views matter: weighting across years changes the impression.

There are {int(folds.outside_range_rows.sum()):,} outside-range cell-years.
Training-only minimum/maximum limits flag any one of nine features outside
its observed range. Counts and individual feature bounds are saved per fold.
Global marginal ranges miss novel combinations and local climate anomalies.
Hot means predictor-year mean temperature above the training 90th percentile;
dry means rainfall or mean soil water below the training 10th percentile.
Hot and dry overlap. These are country-wide training quantiles, not outcome-year
weather or physically standardized drought thresholds.

Group differences mix geography, year and fire prevalence. They do not identify
the causal effect of unfamiliar conditions or establish a changing relationship.
Within-group capture also uses a separate subgroup budget, not the national
shortlist. All annual subgroup counts and scores, including empty groups, are
in `subgroups_by_year.csv`.

`response_diagnostics.png` follows complete feature vectors anchored in real
training rows, then a deliberately synthetic hotter/drier path. Intermediate
combinations are not guaranteed physically realizable. These curves illustrate
the fitted response only, not future accuracy. RF averages tree predictions
and does not extend an unbounded target trend; that does not prevent useful
prediction in later years. See the [scikit-learn 1.8 RF documentation](https://scikit-learn.org/1.8/modules/generated/sklearn.ensemble.RandomForestRegressor.html)
and its [range illustration](https://scikit-learn.org/1.8/auto_examples/ensemble/plot_random_forest_regression_multioutput.html).

## Computational cost and review

{resource_table}

Elapsed main run: {manifest['elapsed_seconds']/60:.1f} minutes. Fit/predict times exclude
serialization and diagnostics and depend on the machine. Model size is the
uncompressed serialized artifact including its fold metadata. RF models/folds
ran sequentially, with two workers per RF and one native-library thread.
The runner reloaded all 80 model artifacts and reproduced full-grid predictions
within 1e-12. It verified {manifest['protected_file_count']} protected artifacts,
including the user's prior source-audit changes, were unchanged.
`independent_verification_refit.json` records the separate independent calculations and
full-fold deterministic refits. Focused tests are recorded in `conclusion.md`.

## Files and reproduction

Branch: `codex/random-forest-forecast-experiment`. Base Git revision:
`{manifest['git_head']}`. The manifest records exact execution code hashes,
data/grid fingerprints, all effective sklearn parameters, seeds and versions.
The run used experiment code still uncommitted at execution; the base revision
alone is not its source snapshot. Research outputs are isolated from operational artifacts.
No application change, model replacement, forecast publication or merge occurred.

Reports: `reports/research/{run_name}/`.
Local Git-ignored predictions/models: `data/processed/research/{run_name}/`.
The 10 Parquet prediction files are keyed by cell and outcome year and include
all eight methods, observed share, area weights and subgroup flags.

```powershell
.\\.venv\\Scripts\\python.exe -m unittest tests.test_random_forest_experiment tests.test_forecast_review -v
.\\.venv\\Scripts\\python.exe scripts/run_random_forest_experiment.py --run-name rf_forecast_new_unique_name
.\\.venv\\Scripts\\python.exe scripts/verify_random_forest_experiment.py --run-name rf_forecast_new_unique_name --refit-year 2025
.\\.venv\\Scripts\\python.exe scripts/build_random_forest_report.py --run-name rf_forecast_new_unique_name
```

Each run needs a new name, even after interruption. Existing validated local
matrices/grid and the pinned repository environment are prerequisites. The
builder regenerates the quantitative report; `conclusion.md` is the separately
reviewed interpretation. Figures: `yearly_metrics.png`, `national_totals.png`,
`unfamiliar_conditions.png`, `climate_subgroups.png`, `response_diagnostics.png`.
"""
    (report / "README.md").write_text(text, encoding="utf-8")
    artifacts = ["README.md", "decision_checks.csv", "severe_years.csv", "year_summary.csv",
                 "subgroups_annual_summary.csv", "climate_subgroups.png"]
    write_json(report / "report_manifest.json", dict(builder_sha256=sha256(Path(__file__)),
        results={name: sha256(report / name) for name in artifacts}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    build(parser.parse_args().run_name)
