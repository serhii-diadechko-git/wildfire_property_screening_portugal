# Forecast reliability review — 24 October 2026

The existing two-stage model has useful **retrospective ranking evidence for
already-observed mainland cells**, but it is not a dependable predictor of
annual burned quantities or severe years. Retain it as a comparative research
layer beside recurrence; do not promote a more complex model from this review.
The main reliability improvement is an honest time/availability contract,
repeated annual checks and explicit baseline/uncertainty reporting.

The work is isolated on `codex/forecast-reliability-review`, based on `main`.
Published predictions, fitted models, figures, maps, presentation and historical
validation reports are preserved. New numerical evidence is in
[`reports/research/forecast_review_v2`](../reports/research/forecast_review_v2/).
The original reports remain historical records; this review supersedes their
claims of an untouched test and a verified pre-year 2026 forecast.

## 1. What was verified

The review read the feature contracts, source registry and manifest, panel
derivation, model classes, hyperparameter routine, final-test routine,
operational scorer, validation reports and Git history. It loaded the saved
models, reproduced their predictions from the nine-feature final matrix within
`1e-12`, independently recalculated metrics from all **267,336** saved rows,
and checked the recorded metric JSON. This verifies the implementation and
saved evidence, not only the prose.

### Recorded outcomes 2023–2025

| Metric | Recurrence | Two-stage model | Model minus recurrence | Relative change |
|---|---:|---:|---:|---:|
| MAE | 0.02918638 | 0.02091322 | −0.00827316 | −28.35% |
| RMSE | 0.11059461 | 0.11099527 | +0.00040066 | +0.36% |
| MAE on cells that burned | 0.31035855 | 0.31437449 | +0.00401594 | +1.29% |
| Pooled top-20% burned-share-mass capture | 40.17% | 57.16% | +16.99 percentage points | +42.31% |
| Pooled top-20% positive-cell capture | 49.30% | 48.43% | −0.87 percentage points | −1.77% |

Errors use proportions from 0 to 1. A MAE reduction of 0.00827316 is about
0.827 percentage points of cell land share, not 0.827% relative improvement.
Capture of burned-share **mass** and capture of the **number of burned cells**
are different metrics. The historical by-year CSV's `capture_at_20_percent`
is positive-cell capture with deterministic tie-breaking; it is not mass
capture. The new results name both explicitly and use fractional boundary ties.

| Outcome year | Method | MAE | RMSE | Burned-cell MAE | Mass capture in that year's top 20% |
|---:|---|---:|---:|---:|---:|
| 2023 | Recurrence | 0.017313 | 0.047503 | 0.114014 | 37.48% |
| 2023 | Two-stage | 0.007851 | 0.045993 | 0.115206 | 54.21% |
| 2024 | Recurrence | 0.028027 | 0.105194 | 0.312945 | 60.19% |
| 2024 | Two-stage | 0.020286 | 0.105957 | 0.318471 | 63.71% |
| 2025 | Recurrence | 0.042219 | 0.152876 | 0.391356 | 32.07% |
| 2025 | Two-stage | 0.034602 | 0.153680 | 0.395610 | 50.98% |

All-year pooling can allocate more of the top-20% budget to some years than
others. An actual annual shortlist has a separate budget each year. The mean
of the three annual captures is **56.30% versus 43.25%**, rather than the pooled
57.16% versus 40.17%. Both calculations are legitimate, but answer different
questions. Burned-share mass is a sum of per-cell shares, not hectares; the
national quantity experiment below uses land-area weights.

**94.82% of these outcomes are zero.** On zero rows the model's mean absolute
error falls from 0.013831 to 0.004886 (−64.67%). On positive rows error increases.
The all-row improvement therefore largely reflects fewer false positive
quantities, not more accurate predictions where fire occurred. A zero forecast
has MAE **0.016657**, better than both, but RMSE **0.112306** and no ranking
skill (20% expected mass capture under ties). It is a necessary diagnostic,
not a useful area-prioritisation method.

In outcome **2025**, observed mean share was **0.030533**, while the frozen
model predicted **0.005436**: **82.20% below** the observed mean. Recurrence
predicted 0.014021, also under by 54.08%. A rank can be informative even when
estimated quantities are badly wrong. Neither performance claim establishes
property safety, ignition probability, or a causal effect.

## 2. Does the previous test reproduce an actual forecast?

Only partly. The code correctly separates predictor year `T` from outcome
`T+1`, uses fire history `T-10..T-1`, fits the occurrence classifier on training
zeros/positives, and fits the severity regressor only on training positives.
The baseline learns its recurrence-count-to-target mapping from training rows.
Final scoring loads these fitted models without fitting on final outcomes.
The recorded final model was trained on predictor 2010–2019 / outcome
2011–2020, selected on predictor 2020–2021 / outcome 2021–2022, and applied
unchanged to predictor 2022–2024 / outcome 2023–2025. It did not simulate annual
refitting and had no exact historical issue-date ledger.

### Availability and leakage audit

| Input or operation | Verified implementation | Remaining real-time limitation |
|---|---|---|
| Fire history and labels | Strict historical predictor window; label is T+1; geometry union avoids double counting | No historical publication/acquisition ledger for every annual archive or revision. Outcome year does not establish release date. |
| CLC | Reference years never exceed T; governed 2006/2012/2018 assignments | Files explicitly use revised `V2020_20u1` packages. A 2006 reference layer revised in 2020 was not available for a 2011 issue. |
| Terrain | Static buffered slope; no target-derived transformation | The stored release is 2021, used also in earlier rows. Stable terrain makes the impact plausibly smaller, but this is still retrospective reconstruction. |
| Mainland grid/denominator | Canonical CAOP 2025 boundary and stable cell IDs | Later boundary version is used throughout history; an as-issued grid/denominator was not reconstructed. |
| ERA5-Land | JJAS summaries use T only; deterministic coastal fallback; no target-driven imputation | Reanalysis vintages and monthly publication times were not archived for each historical issue. Latest/revised downloads cannot prove historical availability. |
| Preprocessing | No learned scaling, feature selection or imputation across the complete panel; physical transforms are fixed; HGB learns bins during fit | Coastal fallback and feature-development choices were assessed retrospectively. Future comparisons must lock those rules before evaluation. |
| Early stopping | Installed sklearn 1.8.0 uses `auto` and a random 10% training validation fraction; saved stages reached 160/210 iterations | This subset contains only historical training rows, so it is not future-label leakage. Spatially/temporally related rows make it an unsuitable independent forecast test. |
| Spatial overlap | Same cells appear in earlier training years and later outcome years; 2 km buffers and coarse climate cells overlap | Appropriate for future prediction at known places, not evidence of transfer to unseen regions. Random row splits would overstate geographic independence. |
| Selection history | Current search routine reads only development rows | Git proves earlier test-period results existed before later selection; see below. |

The current [CDS monthly dataset page](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means?tab=overview)
lists a **2–3 month update delay**. A late-December issue using September data
is plausible, but actual file availability and version must pass the gate.
Near-real-time and final reanalysis products must not be silently substituted.
Provider information was checked on 24 October 2026; it is not a historical
receipt for every fold.

### Test reuse is established, its influence cannot be fully reconstructed

Commit `ed7ae77` (6 August 2026) already contains final-period results for an
earlier nine-feature configuration: MAE about **0.02140**, RMSE **0.11070**,
mass capture **60.03%**, and the observed severe 2025 mean **0.03053**.
V2 was promoted later in `9bc3f00` (9 August), with the current **0.020913**,
**0.110995**, and **57.16%** results. The earlier model-readiness EDA also
displayed final-year target distributions before modelling.

The current selection routine did not directly fit or tune on those rows.
However, a report saying `final_test_rows_read: 0` describes that routine,
not the whole development history. The final period was already known when
later choices were made. It may have informed development or acceptance;
there is insufficient evidence to claim no influence. It must not be called
untouched, nor can this review turn it into a new independent test.

The saved 2026 forecast manifest records **9 August 2026**, with a model fitted
through outcome 2025. Absence of 2026 targets is verified, but this establishes
a target-free estimate created during 2026, not an issue before 2026 began.
There is no recorded earlier issue timestamp that justifies backdating it.

## 3. New repeated annual experiment

The protocol was written before fitting the new alternatives. For each
outcome year **2016–2025**:

- Simulate issue at **31 December Y−1, 12:00 UTC**, cutoff **30 December Y−1,
  23:59:59 UTC**, target the full next calendar year Y.
- Expand training from outcome 2011 through **Y−2**. The immediately preceding
  outcome Y−1 is not complete at issue. The first fold has four labelled years;
  the final fold has thirteen. This is a one-calendar-year forecast from issue,
  but a **two-step extrapolation from the latest known annual outcome**.
- Score all **89,112** identical mainland cells with predictor year **Y−1**;
  fire history ends in Y−2, climate uses JJAS Y−1. Evaluate exactly the same
  target/rows for every cell method, with no row sampling.
- Refit the recurrence mapping, HGB bins, occurrence stage and positive stage
  in each fold. There is no learned preprocessing outside the fold; scaling
  and imputation are unnecessary for these complete inputs.
- Compare zero, training-period overall mean, per-cell training mean,
  latest-available-year per-cell outcome, recurrence, and the two-stage model.
  A literal Y−1 outcome baseline would be unavailable, so it is not used.
- Test one limited training variant: disable random internal early stopping
  while retaining both existing fixed tree budgets and every other parameter.
  Save both models per fold. No feature search, tuning or automatic promotion.

This is an **availability-delayed retrospective sensitivity study**, not a
fully as-of backtest: all input vintages are the existing revised ones, and
Y−2 publication by the issue date remains an assumption. Moreover, the current
specification was selected using outcomes through 2022, so earlier backtest
folds reuse years that helped its development. They are diagnostic evidence,
not honest prospective estimates of that selection procedure. We separate
selection from this run by holding specifications fixed; we do not select a
new winner from its evaluation years.

For a future new model, select features/parameters inside earlier expanding
inner folds, applying the same publication delay. Freeze them before each
outer evaluation issue. Keep outer outcomes out of tuning, early stopping,
threshold choice and interval calibration. An outer period already used for
decisions is development evidence thereafter. A future pre-registered issue
and later outcome, rather than another reshuffle of 2011–2025, is the cleanest
remaining independent check. This follows the rolling-origin principle in
[Forecasting: Principles and Practice](https://otexts.com/fpp3/toolbox.html#time-series-cross-validation).

### Results across ten outcome years

| Method | MAE | RMSE | Burned-cell MAE | Mean annual mass capture@20% |
|---|---:|---:|---:|---:|
| Zero | 0.016205 | 0.110023 | 0.315847 | 20.00% |
| Training mean | 0.028495 | 0.109153 | 0.307691 | 20.00% |
| Per-cell training mean | 0.027661 | 0.112352 | 0.304677 | 38.56% |
| Latest available outcome | 0.028012 | 0.143998 | 0.317187 | 22.99% |
| Recurrence | 0.028182 | 0.109006 | 0.305803 | 38.94% |
| Two-stage, existing parameters | **0.023070** | 0.109849 | 0.307278 | **49.94%** |
| Two-stage, fixed iterations | 0.023131 | 0.109889 | 0.307506 | 48.92% |

Existing two-stage versus recurrence: MAE **−0.005112 (−18.14%)**; RMSE
**+0.000844 (+0.77%)**; burned-cell MAE **+0.001476 (+0.48%)**; mean annual
mass capture **+11.00 percentage points (+28.23%)**. It beats recurrence on
MAE in 10/10 years, RMSE in 5/10, burned-cell MAE in 1/10, and mass capture
in 9/10. Zero beats its MAE in all ten years but has no prioritisation skill.

| Outcome | Recurrence MAE | Model MAE | Recurrence mass capture | Model mass capture | Model mean / observed mean |
|---:|---:|---:|---:|---:|---:|
| 2016 | 0.025129 | 0.021698 | 64.12% | 67.49% | 0.339 |
| 2017 | 0.068449 | 0.066835 | 26.02% | 30.62% | 0.110 |
| 2018 | 0.014581 | 0.013708 | 16.16% | 57.25% | 2.201 |
| 2019 | 0.022615 | 0.022042 | 35.13% | 36.33% | 4.070 |
| 2020 | 0.023553 | 0.015638 | 31.89% | 38.49% | 1.258 |
| 2021 | 0.018238 | 0.009878 | 46.21% | 44.41% | 2.408 |
| 2022 | 0.025480 | 0.018898 | 40.17% | 56.77% | 0.664 |
| 2023 | 0.016250 | 0.006516 | 37.48% | 55.26% | 0.790 |
| 2024 | 0.026944 | 0.020648 | 60.19% | 68.55% | 0.398 |
| 2025 | 0.040584 | 0.034835 | 32.07% | 44.20% | 0.185 |

These annually refitted predictions differ from the original fixed-model
evaluation; do not subtract their scores to claim a causal improvement from
refitting because the training histories differ. Complete annual MAE/RMSE,
positive-cell MAE/RMSE, zero errors, bias and both capture measures are in
`backtest_by_year.csv`. Severe-year underprediction remains **89.01% in 2017**
and **81.51% in 2025**. The model also overpredicts quiet years, e.g. 2019 by
about fourfold. Prior-summer climate cannot reveal next summer's weather,
ignitions or suppression conditions.

Disabling early stopping changes MAE by **+0.0000615 (+0.27%)** and annual
capture by **−1.02 percentage points**. There is no supported reason to promote
that variant. The more reliable evaluation is an improvement in evidence;
it does not imply that a new estimator improved forecasts.

## 4. Uncertainty and geographic scope

The paired bootstrap resamples **whole-country years in consecutive two-year
blocks**, keeping every spatially correlated cell and shared climate/fire event
together. Each draw uses the same years for both methods; RMSE is recomputed
from weighted annual squared errors, positive MAE uses positive-row counts,
and capture is the mean of separate annual-budget captures. Seed 20261024 and
4,000 replicates are fixed. One- and three-year block sensitivities are saved.
This avoids treating 891,120 rows as independent observations.

| Existing model minus recurrence | Difference | Descriptive 95% block-bootstrap interval |
|---|---:|---:|
| MAE | −0.005112 | [−0.007319, −0.002664] |
| RMSE | +0.000844 | [−0.000104, +0.003051] |
| Burned-cell MAE | +0.001476 | [+0.000123, +0.002765] |
| Mean annual mass capture | +11.00 percentage points | [+5.36, +17.25] percentage points |

These are **uncertainty in evaluation differences**, conditional on the saved
fits and historical sample. They are not prediction intervals for next year's
burned share. They do not correct for test reuse, revised datasets, a new
climate regime or training-model uncertainty. Ten years remain few independent
temporal units; long-term dependence can extend beyond the tested blocks.
Circular resampling also approximates the endpoints as adjacent. The original
three-year evaluation is especially inadequate for strong interval or tail
claims; its intervals are supplied only as sensitivity diagnostics, not
evidence of nominal 95% future coverage.

No future-outcome prediction intervals are constructed. Independent calibration
years and repeated coverage/width assessment are missing. A future interval
study must calibrate only on earlier years and report nominal versus empirical
coverage, mean/median width, and severe-year/burned-cell conditional coverage.
With many zeros, apparently good all-cell coverage can conceal failure on
burned cells. A bootstrap metric interval must never be displayed as a cell
forecast interval.

The intended use forecasts future years in **already observed locations**.
Repeated cell IDs across time are therefore intentional. A spatial test asks
whether relationships transfer to locations absent from fitting, which this
study does **not** establish. It is unnecessary to claim that transfer for the
existing complete mainland grid, and we did not add an unrelated spatial-model
search. If expansion to a new region or country is intended, run a separate
spatiotemporal test: hold out entire regions in all years, remove training
buffers at least as wide as overlapping 2 km contexts and the roughly 9 km
climate footprint (start with 20 km, inspect boundary overlap), train only
earlier years, then evaluate future outcomes in the withheld region. Use
region-level outer folds and earlier-region inner selection. Report it
separately; do not mix it with known-location annual scores.

## 5. Where time-series methods fit

Each cell has only **15 annual target values (2011–2025)**, mostly zeros.
Annual observations have no within-year seasonal cycle. Per-cell SARIMA,
seasonal-naive and Prophet's yearly seasonality would add unsupported structure;
thousands of such fits would not create more historical information. ARIMA
at each sparse cell has too little history and does not borrow spatial context.

A national aggregate is a more plausible small time-series experiment. It is
a **separate target**: sum of `burned_share * cell land_area` divided by total
mainland grid land area. It corresponds to a national panel burned-area
fraction, not the arithmetic average used by cell-level MAE. It need not match
an official headline total exactly because clipping, masks and union rules
define this panel. All national methods use the same ten outcome years,
December issue, publication delay and known-history horizon as each other.
Cell predictions are area-weighted for comparison on that national target.

| National method | MAE | RMSE |
|---|---:|---:|
| Training-period mean | 0.013429 | **0.019526** |
| Latest available year | 0.018386 | 0.027940 |
| Trailing three-year mean | 0.017230 | 0.022854 |
| Simple exponential smoothing, fixed alpha 0.3 | 0.015066 | 0.021108 |
| AR(1), intercept + conditional least squares | 0.032355 | 0.063402 |
| Zero | 0.016233 | 0.023928 |
| Area-weighted recurrence predictions | 0.013900 | 0.019929 |
| Area-weighted two-stage predictions | **0.013244** | 0.020619 |

AR(1) is a modest ARIMA(1,0,0) diagnostic fitted using OLS, with no order search
or seasonal terms; it extrapolates two steps from the latest available outcome
and clips only the final share to [0,1]. Its first fold has only four annual
observations, making fitted coefficients unstable. The poor result does not
prove all ARIMA models fail, but offers no justification for a larger search.
The mean beats smoothing on both errors; smoothing worsens MAE by about 12.2%
and RMSE by 8.1%. The aggregated two-stage model has slightly lower MAE than
the mean (about 1.4%) but about 5.6% higher RMSE. Prefer the simple mean as the
national quantity reference; no aggregate method is certified for severe-year
planning from ten reused years.

Regional aggregates might eventually help regional resource planning, but
would require a fixed reporting geography, enough independent region-years and
separate validation of regional decisions. No such claim is made here.

Monthly modelling is a **different task**, not a switch in an annual SARIMA
parameter. It needs event dates and monthly burned-area unions, handling
cross-month/overlapping fire geometry, a monthly target, month-specific
publication lags and genuinely available monthly predictors or weather
forecasts. Only then consider a 12-month seasonal-naive benchmark, aggregate
seasonal models and monthly rolling origins. The four JJAS climate means in
the current annual feature table are not a monthly burned-area series.

## 6. Operational decision and 2026 status

Use the model only to compare broad mainland areas for further research,
alongside recurrence and the separate official structural-hazard layer. Rank
gain is not established economic value or evidence that the lowest-ranked
areas are safe. No buyer decision, insurance price or exact resource allocation
is validated. Keep the recurrence baseline and the zero/mean diagnostics in
every evaluation; use recurrence/history as the fallback for prioritisation
when ML data or dependable added value are absent.

The [revised runbook](operational_forecast_cycle.md) defines the issue/cutoff,
dated inventory, refitting, immutable outputs, delayed outcome evaluation,
monitoring and fallback. The implemented standalone availability checker blocks
unknown or late releases, incomplete dynamic periods, missing source years and
checksum failures. It cannot certify provider claims on its own and is not
yet integrated into a general annual production publisher. The legacy 2026
scripts and their saved artifacts are deliberately preserved.

As of **24 October 2026**, the calendar year is unfinished. The checked
[ICNF catalogue](https://geocatalogo.icnf.pt/catalogo_tema5.html) advertises
burned-area coverage through **2025**; it did not expose a completed 2026
annual outcome in that listing. The government's October
[interim update](https://portugal.gov.pt/gc25/comunicacao/comunicados/governo-abre-novo-apoio-para-estabilizacao-de-emergencia-das-areas-afetadas-pelos-grandes-incendios-de-2026)
explicitly reports a within-year cutoff. Neither interim statistics nor an
EFFIS estimate is interchangeable with the completed ICNF per-cell target.
**No 2026 annual performance score was calculated.** Once the official full-year
data are available, score the preserved estimate with its August issue date
disclosed; do not re-label that comparison as a pre-2026 forecast experiment.

## 7. What to retain and what remains unverified

Retain the existing nine-feature specification as a cautious comparative
research layer, and recurrence as the transparent required comparator/fallback.
Do not promote fixed iterations, AR(1), SARIMA or Prophet. Retain the national
training mean as a simple quantity benchmark, without claiming calibrated
severe-year totals. A new complex model is not supported by these experiments.

The previous testing established reproducible retrospective average-error and
ranking differences. It did not establish untouched evaluation, historical
publication-time realism, reliable severe-year quantities, prediction-interval
coverage, geographic transfer or decision value. The new tests improve the
reliability of the evidence by exposing those limits, repeating ten issue
years, using fair available-information baselines and respecting dependence.

Before operational reliance: archive actual dated input vintages; complete a
prospective pre-year forecast cycle; validate the annual publisher integration;
evaluate several new completed outcome years, including severe years; and
demonstrate useful outcomes for a defined broad-area decision. If geographic
transfer or numerical uncertainty bands are required, validate them separately.

In simple English: the old test asked whether our map matched later fire maps
using data assembled afterwards. The new check repeatedly asks, “Using the
years we could have completed before January, which areas would we put on the
next year's research shortlist?” The model often makes a better shortlist than
recurrence, but it still misses how large a bad fire year can be. Predicting
zero looks good on average because most places do not burn; it is useless for
choosing where to look. Keep the useful map comparison, and be much more
careful about timing and quantities.

## Reproduce without changing published work

```text
python -m unittest tests.test_forecast_review -v
python scripts/run_forecast_review.py --run-name another_unique_review_name
python scripts/check_forecast_availability.py --manifest docs/forecast_issue_inventory.example.json
```

The final command is expected to return `blocked`: the template intentionally
contains unknown dates and incomplete inputs. Use the repository's pinned
environment and existing validated matrices/grid. The runner refuses reused
names, saves predictions and fitted models under `data/processed/research/`,
and saves protocol, annual/aggregate metrics, paired differences, uncertainty,
figure, hashes and environment metadata under `reports/research/`. Models use
the original seed 20260805; the paired bootstrap uses seed 20261024.

See the [experiment record](../reports/research/forecast_review_v2/README.md)
for execution checks and the complete result inventory.
