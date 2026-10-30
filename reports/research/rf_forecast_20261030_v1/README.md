# Random Forest in the Portugal wildfire capstone

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

| Model | Pooled MAE | Pooled RMSE | Burned-cell MAE | Mean annual capture | Pooled capture |
| --- | --- | --- | --- | --- | --- |
| Zero | 0.016205 | 0.110023 | 0.315847 | 20.00% | 20.00% |
| Training mean | 0.028495 | 0.109153 | 0.307691 | 20.00% | 7.37% |
| Cell historical mean | 0.027661 | 0.112352 | 0.304677 | 38.56% | 36.77% |
| Latest available outcome | 0.028012 | 0.143998 | 0.317187 | 22.99% | 21.89% |
| Recurrence | 0.028182 | 0.109006 | 0.305803 | 38.94% | 26.99% |
| Current HGB hurdle | 0.023070 | 0.109849 | 0.307278 | 49.94% | 42.63% |
| Direct RF | 0.026356 | 0.110679 | 0.305206 | 50.63% | 36.89% |
| RF hurdle | 0.024914 | 0.109791 | 0.305683 | 48.82% | 40.32% |

Errors are shares from 0 to 1. Lower errors and higher capture are better.
**94.87% of targets are zero**. Zero can
therefore have strong MAE without identifying useful areas. Capture means the
fraction of burned-share mass in the highest-scored 20% of cells, with fractional
boundary ties. It is not hectares or a count of burned cells. Mean annual capture
gives each year its own 20% budget; pooled capture is a different calculation.
Burned share is not fire probability.

Predeclared research screening criteria (not economic benefit or promotion):

- Current HGB hurdle: useful_ranking_vs_recurrence = **passes**.
- Direct RF: useful_ranking_vs_recurrence = **passes**.
- Direct RF: improves_current_hgb = **fails**.
- RF hurdle: useful_ranking_vs_recurrence = **passes**.
- RF hurdle: improves_current_hgb = **fails**.

## Paired differences and consistency

| Comparison | Metric | Difference | Descriptive 95% interval | Years better |
| --- | --- | --- | --- | --- |
| Current HGB hurdle - Recurrence | mae | -0.00511 | [-0.00732, -0.00266] | 10/10 |
| Current HGB hurdle - Recurrence | rmse | +0.00084 | [-0.00010, +0.00305] | 5/10 |
| Current HGB hurdle - Recurrence | positive_mae | +0.00148 | [+0.00012, +0.00277] | 1/10 |
| Current HGB hurdle - Recurrence | mass_capture20 | +10.99532 pp | [+5.35885, +17.24648] pp | 9/10 |
| Direct RF - Recurrence | mae | -0.00183 | [-0.00418, +0.00083] | 7/10 |
| Direct RF - Recurrence | rmse | +0.00167 | [+0.00036, +0.00541] | 1/10 |
| Direct RF - Recurrence | positive_mae | -0.00060 | [-0.00248, +0.00096] | 5/10 |
| Direct RF - Recurrence | mass_capture20 | +11.68226 pp | [+5.04773, +18.83759] pp | 9/10 |
| RF hurdle - Recurrence | mae | -0.00327 | [-0.00542, -0.00085] | 8/10 |
| RF hurdle - Recurrence | rmse | +0.00079 | [-0.00023, +0.00367] | 6/10 |
| RF hurdle - Recurrence | positive_mae | -0.00012 | [-0.00164, +0.00131] | 4/10 |
| RF hurdle - Recurrence | mass_capture20 | +9.87536 pp | [+3.57479, +17.15603] pp | 8/10 |
| Direct RF - Current HGB hurdle | mae | +0.00329 | [+0.00270, +0.00395] | 0/10 |
| Direct RF - Current HGB hurdle | rmse | +0.00083 | [+0.00013, +0.00253] | 2/10 |
| Direct RF - Current HGB hurdle | positive_mae | -0.00207 | [-0.00298, -0.00099] | 8/10 |
| Direct RF - Current HGB hurdle | mass_capture20 | +0.68694 pp | [-1.00882, +2.37792] pp | 5/10 |
| RF hurdle - Current HGB hurdle | mae | +0.00184 | [+0.00121, +0.00249] | 0/10 |
| RF hurdle - Current HGB hurdle | rmse | -0.00006 | [-0.00047, +0.00079] | 5/10 |
| RF hurdle - Current HGB hurdle | positive_mae | -0.00159 | [-0.00221, -0.00053] | 8/10 |
| RF hurdle - Current HGB hurdle | mass_capture20 | -1.11996 pp | [-3.58961, +1.45074] pp | 5/10 |

Negative error differences are better; positive capture differences are better.
Intervals resample paired whole-country two-year blocks 4,000 times, preserving
all spatial dependence within each year. One- and three-year block sensitivities
are in `paired_uncertainty.csv`. These are metric uncertainty, **not future
prediction intervals**. Ten temporal units are few; overlapping training histories,
longer dependence, model fitting uncertainty and test reuse are not eliminated.
Multiple exploratory comparisons have no multiplicity correction.

| Outcome | Recurrence capture | HGB capture | Direct RF capture | RF hurdle capture |
| --- | --- | --- | --- | --- |
| 2016 | 64.12% | 67.49% | 72.03% | 72.63% |
| 2017 | 26.02% | 30.62% | 26.93% | 31.82% |
| 2018 | 16.16% | 57.25% | 60.59% | 62.96% |
| 2019 | 35.13% | 36.33% | 38.34% | 28.08% |
| 2020 | 31.89% | 38.49% | 36.02% | 35.97% |
| 2021 | 46.21% | 44.41% | 43.54% | 45.66% |
| 2022 | 40.17% | 56.77% | 54.11% | 47.28% |
| 2023 | 37.48% | 55.26% | 64.58% | 54.13% |
| 2024 | 60.19% | 68.55% | 64.82% | 71.21% |
| 2025 | 32.07% | 44.20% | 45.29% | 38.44% |

All annual MAE, RMSE, positive-cell MAE, zero fractions, timing and area-weighted
totals are in `metrics_by_year.csv`. `paired_differences.csv` compares every
learned model against all five baselines, plus RF versus HGB and each other.

## National quantities and severe years

| Outcome | Model | Observed ha | Predicted ha | National error |
| --- | --- | --- | --- | --- |
| 2016 | Current HGB hurdle | 156,125 | 52,775 | -66.2% |
| 2016 | Direct RF | 156,125 | 93,629 | -40.0% |
| 2016 | RF hurdle | 156,125 | 66,101 | -57.7% |
| 2017 | Current HGB hurdle | 559,617 | 61,382 | -89.0% |
| 2017 | Direct RF | 559,617 | 75,382 | -86.5% |
| 2017 | RF hurdle | 559,617 | 72,748 | -87.0% |
| 2025 | Current HGB hurdle | 271,710 | 50,187 | -81.5% |
| 2025 | Direct RF | 271,710 | 65,568 | -75.9% |
| 2025 | RF hurdle | 271,710 | 61,521 | -77.4% |

Severe years exceed the training-history 90th percentile of national observed
share; this uses outcomes only for retrospective diagnostics, never tuning.
Totals weight each cell by mainland land area and refer to this clipped panel,
not necessarily the exact official headline total.

## Unfamiliar inputs and hot/dry predictor summers

| Group | Rows | Burned rows | Model | MAE | Burned-cell MAE | Pooled capture |
| --- | --- | --- | --- | --- | --- | --- |
| inside_range | 854,218 | 44,958 | Current HGB hurdle | 0.023627 | 0.305657 | 40.94% |
| inside_range | 854,218 | 44,958 | Direct RF | 0.026890 | 0.304145 | 35.58% |
| inside_range | 854,218 | 44,958 | RF hurdle | 0.025515 | 0.304338 | 38.63% |
| outside_range | 36,902 | 763 | Current HGB hurdle | 0.010175 | 0.402788 | 85.11% |
| outside_range | 36,902 | 763 | Direct RF | 0.013984 | 0.367734 | 69.90% |
| outside_range | 36,902 | 763 | RF hurdle | 0.010984 | 0.384931 | 86.39% |
| hot | 111,116 | 2,155 | Current HGB hurdle | 0.005948 | 0.244797 | 27.79% |
| hot | 111,116 | 2,155 | Direct RF | 0.007860 | 0.244365 | 11.77% |
| hot | 111,116 | 2,155 | RF hurdle | 0.006906 | 0.244031 | 25.55% |
| dry | 211,043 | 3,923 | Current HGB hurdle | 0.006083 | 0.240597 | 45.23% |
| dry | 211,043 | 3,923 | Direct RF | 0.008329 | 0.233768 | 39.72% |
| dry | 211,043 | 3,923 | RF hurdle | 0.006890 | 0.236542 | 47.12% |
| neither_hot_nor_dry | 629,313 | 40,809 | Current HGB hurdle | 0.030107 | 0.314904 | 31.83% |
| neither_hot_nor_dry | 629,313 | 40,809 | Direct RF | 0.033820 | 0.313244 | 29.29% |
| neither_hot_nor_dry | 629,313 | 40,809 | RF hurdle | 0.032345 | 0.313524 | 31.37% |

The corresponding mean annual subgroup captures are:

| Group | Years | Recurrence capture | HGB capture | Direct RF capture | RF hurdle capture |
| --- | --- | --- | --- | --- | --- |
| inside_range | 10 | 41.87% | 48.32% | 49.49% | 46.30% |
| outside_range | 7 | 19.46% | 33.52% | 33.82% | 35.35% |
| hot | 10 | 25.06% | 25.25% | 14.52% | 28.34% |
| dry | 10 | 23.99% | 43.90% | 40.04% | 46.19% |
| neither_hot_nor_dry | 10 | 38.43% | 42.74% | 40.65% | 41.80% |

Outside-range groups exist in seven years; the other three have zero rows and
undefined subgroup errors/capture. The inside-range mean uses all ten years,
so these group means are not paired estimates of a condition's effect. Both
annual and pooled views matter: weighting across years changes the impression.

There are 36,902 outside-range cell-years.
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

| Model | Total fit seconds | Total predict seconds | Mean saved MB | National MAE | National RMSE |
| --- | --- | --- | --- | --- | --- |
| Zero | 0.0 | 0.00 | 0.00 | 0.016233 | 0.023928 |
| Training mean | 0.0 | 0.00 | 0.00 | 0.013421 | 0.019522 |
| Cell historical mean | 1.7 | 0.18 | 4.28 | 0.013429 | 0.019526 |
| Latest available outcome | 0.3 | 0.19 | 4.28 | 0.018386 | 0.027940 |
| Recurrence | 0.8 | 0.09 | 0.00 | 0.013900 | 0.019929 |
| Current HGB hurdle | 383.9 | 67.94 | 1.38 | 0.013244 | 0.020619 |
| Direct RF | 952.5 | 2.05 | 3.55 | 0.013744 | 0.020390 |
| RF hurdle | 1204.2 | 4.04 | 5.98 | 0.013517 | 0.020407 |

Elapsed main run: 46.3 minutes. Fit/predict times exclude
serialization and diagnostics and depend on the machine. Model size is the
uncompressed serialized artifact including its fold metadata. RF models/folds
ran sequentially, with two workers per RF and one native-library thread.
The runner reloaded all 80 model artifacts and reproduced full-grid predictions
within 1e-12. It verified 96 protected artifacts,
including the user's prior source-audit changes, were unchanged.
`independent_verification_refit.json` records the separate independent calculations and
full-fold deterministic refits. Focused tests are recorded in `conclusion.md`.

## Files and reproduction

Branch: `codex/random-forest-forecast-experiment`. Base Git revision:
`31285af51545f15f87ad53daac186b66102d8f5d`. The manifest records exact execution code hashes,
data/grid fingerprints, all effective sklearn parameters, seeds and versions.
The run used experiment code still uncommitted at execution; the base revision
alone is not its source snapshot. Research outputs are isolated from operational artifacts.
No application change, model replacement, forecast publication or merge occurred.

Reports: `reports/research/rf_forecast_20261030_v1/`.
Local Git-ignored predictions/models: `data/processed/research/rf_forecast_20261030_v1/`.
The 10 Parquet prediction files are keyed by cell and outcome year and include
all eight methods, observed share, area weights and subgroup flags.

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_random_forest_experiment tests.test_forecast_review -v
.\.venv\Scripts\python.exe scripts/run_random_forest_experiment.py --run-name rf_forecast_new_unique_name
.\.venv\Scripts\python.exe scripts/verify_random_forest_experiment.py --run-name rf_forecast_new_unique_name --refit-year 2025
.\.venv\Scripts\python.exe scripts/build_random_forest_report.py --run-name rf_forecast_new_unique_name
```

Each run needs a new name, even after interruption. Existing validated local
matrices/grid and the pinned repository environment are prerequisites. The
builder regenerates the quantitative report; `conclusion.md` is the separately
reviewed interpretation. Figures: `yearly_metrics.png`, `national_totals.png`,
`unfamiliar_conditions.png`, `climate_subgroups.png`, `response_diagnostics.png`.
