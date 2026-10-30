# Conclusion: Random Forest forecast experiment

**Random Forest has useful retrospective ranking skill in this capstone, but
neither tested RF design improves enough on the current HGB model to justify
replacement. The concern about unfamiliar conditions is plausible, but this
experiment does not establish a general decline caused by extrapolation or
changing relationships.**

## What was tested

Eight methods were evaluated on all 89,112 mainland cells for every outcome
year 2016-2025: 891,120 cell-years per method. The comparison includes five
simple baselines, the retained histogram gradient boosting hurdle, direct RF,
and an occurrence-times-positive-share RF hurdle. Each RF stage used 48 bounded
trees. Training expanded from outcomes 2011 through Y-2; scoring used predictor
Y-1. The nine predictors and evaluation rows were identical for every method.
No evaluation-year tuning or random cell-year split was used.

These are retrospective comparisons using revised historical data and previously
examined years. Source-year chronology was verified, but historical publication
and acquisition dates cannot be certified. This is annual forecasting for known
mainland cells, not transfer to new locations. Burned share is a continuous
fraction of cell land area, not fire probability.

## Useful ranking, with clear tradeoffs

| Method | Pooled MAE | Pooled RMSE | Burned-cell MAE | Mean annual top-20% mass capture |
| --- | --- | --- | --- | --- |
| Zero | 0.016205 | 0.110023 | 0.315847 | 20.00% |
| Recurrence | 0.028182 | 0.109006 | 0.305803 | 38.94% |
| Current HGB hurdle | 0.023070 | 0.109849 | 0.307278 | 49.94% |
| Direct RF | 0.026356 | 0.110679 | 0.305206 | 50.63% |
| RF hurdle | 0.024914 | 0.109791 | 0.305683 | 48.82% |

Direct RF gained **11.68 percentage points** of mean annual capture over
recurrence, winning in **9/10 years**. RF hurdle gained **9.88 points**, winning
in **8/10**. Paired two-year country-block descriptive 95% intervals were
[5.05, 18.84] and [3.57, 17.16] points. Both pass the predeclared research
ranking criterion. This is evidence for a better research shortlist, not
established operational or economic value.

The other baseline comparisons also matter. Negative MAE differences are better:

| Baseline | Direct RF MAE difference; years better | RF hurdle MAE difference; years better | Annual capture gain: direct / hurdle; years better |
| --- | --- | --- | --- |
| Zero | +0.010150; 0/10 | +0.008708; 0/10 | +30.63 / +28.82 points; 10/10 each |
| Training mean | -0.002140; 8/10 | -0.003582; 9/10 | +30.63 / +28.82 points; 10/10 each |
| Cell historical mean | -0.001306; 7/10 | -0.002748; 9/10 | +12.07 / +10.26 points; 9/10 and 8/10 |
| Latest available outcome | -0.001656; 3/10 | -0.003099; 3/10 | +27.64 / +25.83 points; 10/10 each |
| Recurrence | -0.001827; 7/10 | -0.003269; 8/10 | +11.68 / +9.88 points; 9/10 and 8/10 |

Both RFs beat the cell mean and latest outcome on pooled RMSE, but lose to
recurrence and the training mean. Direct RF even has worse pooled RMSE than
zero. Zero wins MAE because **94.87% of targets are zero**; it provides no
ranking skill. A lower pooled error can coexist with fewer annual wins, as
the latest-outcome comparison shows. All per-year metrics and all paired
comparisons are retained in the CSVs.

Against HGB, direct RF's capture gain is only **0.69 points** [-1.01, +2.38];
RF hurdle is **1.12 points lower** [-3.59, +1.45]. Each wins ranking in only
5/10 years. HGB has lower all-cell MAE in **every year**; RF pooled MAE is
14.24% and 7.99% higher. RF does improve burned-cell MAE slightly, by 0.67%
and 0.52%, winning in 8/10 years. Hurdle RF has nearly identical pooled RMSE
to HGB; direct RF is 0.76% worse. Neither passes the predeclared replacement
criteria. HGB does not dominate every metric.

Changing RF's structure helps quantity errors: the hurdle improves direct RF's
MAE in 10/10 years and RMSE in 9/10. However, its mean annual capture falls by
1.81 points. The algorithm name alone does not determine usefulness.

## Quantities and unfamiliar conditions

Both RFs substantially miss severe national totals. Direct/hurdle RF are
86.5%/87.0% below the observed 2017 burned area and 75.9%/77.4% below 2025.
HGB also underpredicts those years, by 89.0% and 81.5%. Both RFs have worse
national MAE and RMSE than the simple training-mean comparator. Better ranking
does not make these dependable forecasts of annual burned quantities.

Only **36,902 cell-years (4.14%)**, including **763 burned cell-years**, fall outside
training feature ranges. The excursions are all climate features, mainly low
precipitation. Direct RF burned-cell MAE rises from 0.3041 inside to 0.3677
outside; RF hurdle rises from 0.3043 to 0.3849. However, all-cell MAE falls and
pooled capture rises outside. Annual subgroup capture gives a different picture;
outside groups exist in seven years, while inside groups exist in ten. These
changing mixtures of years, geography and fire prevalence prevent a simple
causal explanation. HGB also has larger pooled burned-cell errors outside.

For hot predictor summers, direct RF mean annual subgroup capture is only
14.52%, versus 25.25% for HGB and 28.34% for RF hurdle. In dry predictor summers,
the RF values are 40.04% and 46.19%, versus 43.90% for HGB and 23.99% for
recurrence. Conditional performance is mixed, and depends on model structure.
These are training-quantile groups of the preceding summer, not forecasts of
the outcome year's weather or validated drought classifications.

**No inputs scored for outcome 2025 are outside the marginal training ranges**, despite the severe
underprediction. Range checks miss unfamiliar combinations, local anomalies,
and changes in the relationship between predictors and outcomes. The synthetic
hot/dry response curves eventually flatten for both RF and HGB. That illustrates
their fitted responses, not future accuracy or an RF-specific failure. A later
year can still contain familiar patterns; inability to extend a rising trend
does not imply inability to forecast later outcomes.

## Recommendation and limits

Retain the current HGB research layer, recurrence comparator/fallback, and
simple national mean benchmark. Keep these RFs as reproducible research
comparators; do not promote either from this evidence. A later study could
freeze any new choices using earlier chronological validation, then evaluate
genuinely new completed outcomes with archived input vintages.

The uncertainty intervals describe historical metric differences, not prediction
intervals. Ten country-years, overlapping training histories, reused development
years, revised data, one RF configuration per design, and unadjusted exploratory
comparisons limit the conclusions. No formal relationship-change test or causal
attribution was performed.

## Review and reproduction

The full run took 46.3 minutes. All 80 saved model bundles reproduced their
full-grid predictions within 1e-12 after reload, and 96 protected artifacts were
unchanged. Six new focused tests plus ten existing temporal/availability tests
passed. Independent verification reproduced all 891,120 keyed evaluation rows,
80 annual model results, 440 subgroup results, the bootstrap interval endpoints,
and 60 baseline/HGB comparisons against the previous accepted run. Repeating
both full-data 2025 RF fits changed predictions by at most 8.33e-17 (direct)
and 5.55e-17 (hurdle). Verification and final review details are recorded in
the adjacent verification and delivery records.

Branch: `codex/random-forest-forecast-experiment`. No operational model,
application, forecast or published artifact was replaced, and no merge occurred.
The numerical report, all metric CSVs, figures, manifest and reproduction
commands are in [README.md](README.md). Predictions and fitted models are in
`data/processed/research/rf_forecast_20261030_v1/` under the repository root.

## Short capstone conclusion

The experiment showed that Random Forest can help rank areas by next-year
wildfire exposure. Both versions ranked areas better than historical fire
recurrence, but neither clearly improved on the current HGB model. We therefore
keep HGB as a research tool because it combines useful ranking with lower
average error.

However, all models substantially underestimated burning in severe years.
Results under unfamiliar conditions were mixed, so we cannot conclude that
unfamiliar inputs caused poorer predictions. Because the experiment used
revised historical data and previously examined years, performance on genuinely
new future years remains uncertain.
