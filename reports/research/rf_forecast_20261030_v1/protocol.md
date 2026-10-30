# Random Forest annual forecast experiment

Specification fixed on 30 October 2026 before comparison fits. This is a
retrospective experiment on the existing mainland grid, not a prospective
forecast, an untouched test, or a test of transfer to unseen locations.

## Questions and timing

1. Do direct and two-stage Random Forest models improve annual ranking and
   continuous burned-share errors over simple baselines?
2. Do they improve over the retained histogram gradient boosting (HGB) hurdle?
3. Is performance different outside training feature ranges, in severe fire
   years, or after unusually hot/dry predictor summers?

For outcome Y=2016,...,2025, simulate issue on 31 December Y-1 at 12:00 UTC,
with input cutoff 30 December Y-1 at 23:59:59 UTC. Fit on outcomes 2011..Y-2;
score predictor Y-1 and outcome Y. Y-1 is unfinished at cutoff, so its full-year
label cannot be used. Scoring fire history ends Y-2; climate uses JJAS Y-1.
Each fold includes all 89,112 cells, with 4..13 complete training years.

Enforce actual source-year metadata: outcome=T+1, history=T-10..T-1,
climate=T, land-cover reference<=T. A reference year is not a release date.
Revised CLC V2020, terrain released in 2021, CAOP 2025 boundaries, and
unarchived historical ICNF/ERA5 receipt dates prevent a verified as-issued
comparison. All historical folds are ineligible for a claim of proven
historical availability. Y-2 label publication is an explicit assumption.
Unknown publication dates must never be converted into a passing availability
gate; the runner records this limitation and produces research artifacts only.
No data downloads or source substitutions are authorized by this experiment.

## Data and fixed models

Use the existing two nine-feature matrices, outcomes 2011..2025, with one row
per nominal 1 km mainland cell and predictor year. The continuous target is
`burned_share_next_year`, a fraction of cell land area, not fire probability.
Use exactly `src.feature_contract.PREDICTOR_COLUMNS` in its declared order.
IDs, year, area, metadata and target are excluded from learned predictors.
No imputation, scaling, feature selection or tuning is performed. Fit all
learned components on training rows only. Repeated locations are intended.

- Zero, overall training mean, cell training mean, latest available outcome
  (Y-2), and the existing training-only recurrence-count mapping.
- Retained `HurdleHistGradientRegressor`, unchanged defaults, including its
  historical-training-only automatic early stopping. Occurrence: 160 iterations,
  learning rate .07, 31 leaves, minimum leaf 80, L2 .02. Positive share:
  210 iterations, learning rate .06, 31 leaves, minimum leaf 55, L2 .02.
  Multiply occurrence probability and clipped conditional share.
- Direct `RandomForestRegressor`: 48 trees, squared error, maximum depth 12,
  maximum 512 leaves, minimum leaf 80, all nine features available at splits,
  standard full-size bootstrap per tree, no sample or class reweighting.
- RF hurdle: `RandomForestClassifier` (Gini, minimum leaf 80), and
  `RandomForestRegressor` on positive shares (squared error, minimum leaf 55).
  Other tree settings match direct RF; multiply outputs. No class reweighting.

All model seeds are 20260805. One configuration per RF design avoids tuning
on reused evaluation years. Bounded trees and 48-tree ensembles are a modest
computational comparison, not an exhaustive claim about optimal RF. Bootstrap
sampling is intrinsic to RF; every training row is supplied to fit and every
evaluation cell is scored. Models/folds run sequentially, RF uses two workers,
and native thread pools use one thread. No competing model training jobs.

## Metrics and decision criteria

Report per-year and pooled MAE, RMSE, burned-cell MAE, zero fraction, and
tie-aware top-20% burned-share-mass capture. Report separate annual-budget
mean capture; pooled capture permits different allocation between years.
Use land-area weights for national annual predicted and observed shares and
burned hectares. Record fit/predict seconds and uncompressed serialized bytes
per method/fold. Timing excludes diagnostics and serialization.

Primary research usefulness: mean annual capture at least 5 percentage points
above recurrence, a positive paired two-year-block interval, and gains in at
least 7/10 years. Improvement over current HGB additionally requires at least
2 capture points, gains in 7/10 years, a positive interval, and no more than
1% relative deterioration in pooled RMSE or burned-cell MAE. These thresholds
are research screening criteria, not validated economic utility. Report all
tradeoffs even when a criterion fails. Quantity adequacy requires separate
inspection of national errors and severe-year bias; MAE alone cannot qualify
a model because zeros dominate. No automatic model promotion.

Paired uncertainty: reuse whole-country circular year-block bootstrap, seed
20261024, 4,000 draws, primary block length two and sensitivities one/three.
Compare each learned model with all baselines and RF with HGB and each other.
These describe metric differences conditional on fitted models, not prediction
intervals. Ten overlapping-history years provide few independent units.

## Unfamiliar conditions and diagnostics

For each fold learn per-feature min/max only from training rows. Flag strict
out-of-range test values, report feature-specific counts and metrics inside
versus outside the union, including empty groups. This cannot detect every
unfamiliar combination or changing relationship.

Also flag predictor summers with mean temperature above the training 90th
percentile, precipitation below its 10th percentile, or mean soil water below
its 10th percentile. Thresholds are country-wide training-row quantiles,
not local climate anomalies. Report hot, dry, and remaining groups without
tuning. Retrospectively label severe outcome years as national observed share
above the training-history 90th percentile; labels are diagnostics only.

For the final fold select three real training rows near temperature quantiles
10/50/90%. Plot responses along interpolation between the complete nine-feature
vectors (round fire counts). These training-anchored synthetic combinations
retain joint climate patterns but do not guarantee physical realism. Also
extend the hotter/drier real anchor's two temperature features by 0..8 C and
reduce both soil-water features and precipitation together. Label this
explicitly synthetic and diagnostic; it does not establish future accuracy.
Actual held-out yearly results, not synthetic curves, test forecasting.

## Artifacts and verification

New code lives in `src/random_forest_experiment.py` and its scripts/tests;
reports in `reports/research/<unique_run_name>/`, fitted models and keyed
predictions in `data/processed/research/<unique_run_name>/`. Reject reused
names. Hash inputs, code, configurations, environment, and protected existing
artifacts. Preserve user source-audit edits. Save full per-fold predictions,
metrics CSVs, diagnostics, manifest, figures and a simple-English report.
Check temporal boundaries, source metadata, exclusion of future targets,
alignment, independent metric calculations, saved-model reload predictions,
and deterministic repeated fitting. The main run uses every eligible fold
and full data; test fixtures are not the final evidence.

Reproduce from the repository root using the pinned environment:

```powershell
.\.venv\Scripts\python.exe scripts/run_random_forest_experiment.py --run-name rf_forecast_20261030_reproduction
.\.venv\Scripts\python.exe -m unittest tests.test_random_forest_experiment tests.test_forecast_review -v
```
