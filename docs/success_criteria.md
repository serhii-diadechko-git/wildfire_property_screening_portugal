# Success Criteria and Model Acceptance Rules

> The canonical national panel, backward training extension, and model-readiness EDA are validated. The one frozen final temporal test `T=2022-2024` is complete. The frozen nine-feature specification is refit through observed outcome 2025 and may be used for a clearly labelled annual comparative estimate only after the relevant source-input preflight passes. It is not a calibrated probability, safety guarantee, or purchase recommendation.

## Purpose

This document separates:

- **required project completion criteria**, which are mainly under project control;
- **model evaluation targets**, which must be tested and cannot be guaranteed in advance.

## A. Required project completion criteria

### 1. Reproducible data pipeline

**Target:** create documented steps that transform the required public sources into the agreed 1 km cell-year dataset.

**Check:** rerun deterministic bounded national batches and confirm identical analytical keys and values before assembling the panel.

### 2. Consistent spatial design

**Target:** use one 1 km analytical grid and one clearly documented initial 2 km context buffer.

**Check:** confirm that cell-level and buffer-level fields follow the definitions in `docs/data_dictionary.md`.

### 3. Validated residential-relevance rule

**Target:** define which 1 km cells are relevant to residential location screening.

**Check:** inspect land-cover class definitions and mapped samples. Built-up land must not automatically be called residential.

### 4. Coverage of eligible cells

**Planning target:** return one of the following for at least 95% of eligible cells:

- comparative annual score;
- insufficient-evidence status;
- documented exclusion reason.

**Check:**

```text
coverage = cells with a result status / all eligible cells
```

The published 2026 output contains all 89,112 canonical cells. Future annual outputs must revalidate coverage rather than assume it.

### 5. Mandatory data completeness

**Target:** assign a comparative annual score only when all mandatory groups are present:

- historical burned-area feature;
- land-cover features;
- mean slope;
- temperature, precipitation, and layer-1 soil water.

**Check:** report missing mandatory groups and mark incomplete cases as insufficient evidence.

### 6. Geographic coverage

**Target:** include every mainland municipality containing eligible cells in the final coverage report.

**Check:** report eligible, scored, insufficient-evidence, and excluded cells by municipality.

### 7. Decision-output clarity

**Target:** produce at least:

- one national exposure map;
- one residential screening map;
- one model-performance figure;
- one ranked table;
- uncertainty or insufficient-evidence flags;
- a limitations section.

### 8. Update procedure

**Target:** document annual scoring and refitting as separate processes.

- **Scoring:** apply the versioned frozen-specification model to an unlabelled `T=Y-1` feature matrix to estimate year `Y`.
- **Refitting:** after ICNF outcome `Y-1` is validated, refit the unchanged selected specification through labelled predictor year `Y-2`; do not tune from an unknown future target.

## B. Model evaluation targets

### 1. Baseline comparison

Compare the regression candidates with a training-fitted historical-fire baseline using `fire_years_previous_10y_2km`. A zero-prediction baseline is reported only as an error reference; it is not an acceptable predictive model.

The comparison must use future-year test data. A complex model is not accepted because of training performance alone.

During train/validation model selection, the primary regression evidence is reported overall and separately for each validation year:

- MAE and RMSE over all rows;
- MAE and RMSE restricted to rows where `burned_share_next_year > 0`;
- mean `predicted_burned_share_next_year` versus mean observed `burned_share_next_year`;
- positive-cell capture@20%, defined as the share of positive-target cells contained in the highest-ranked 20% of regression estimates;
- burned-share-mass capture@20%, defined as the share of all observed burned-area mass contained in that same highest-ranked 20%.

Ties at the 20% boundary are handled fractionally in the formal final-test report. A simpler deterministic top-row diagnostic is retained in the generated chart for reproducibility; it differs slightly for the coarse historical baseline because many cells have identical scores. Neither form is a buyer threshold.

### 2. Conditional classification evaluation

PR-AUC, probability calibration, precision, recall, F1-score, and ROC-AUC apply only if a separate classification target and model are introduced after a documented target-distribution and threshold decision. A regression output must not be called a probability.

For any later imbalanced classification model, PR-AUC should be compared with positive-class prevalence.

This condition alone does not prove that the model is useful.

### 3. Top-ranked capture

Rank test cells from highest to lowest predicted exposure.

```text
positive-cell capture@20% = affected cells in the highest-ranked 20% / all affected cells
```

**Evaluation target:** capture at least 40% of affected cells within the highest-risk 20%.

A random 20% selection would be expected to capture about 20%. The 40% value is a useful target, not a guaranteed outcome.

### 4. Generalisation and conditional calibration

Report:

- regression MAE and RMSE overall and on positive-target rows;
- mean predicted versus observed burned share;
- positive-cell and burned-share-mass capture@20%;
- performance by test year;
- performance by region or geographic holdout.

Report precision, recall, F1-score, ROC-AUC, PR-AUC, and probability calibration only for a separately documented classification model.

No single metric is sufficient on its own.

## C. Model acceptance decision

### Accept for comparative research use

The continuous model may be retained for methodological comparison only when:

- the model improves on the historical baseline;
- it performs better than random ranking;
- final-test performance and its temporal limitations are reported transparently;
- ranking quality is acceptable, and probability calibration is acceptable only if a later classification model is introduced;
- no probability, safety, or purchase claim is made.

The frozen nine-feature hurdle meets the comparative-evidence condition: it has lower final-test MAE and higher burned-share-mass capture than the historical recurrence baseline. It remains weakly calibrated in the high-burned outcome associated with T=2024, so a published annual score must remain a cautious comparative estimate rather than a buyer-facing recommendation.

### Do not accept for buyer-facing predictive recommendation

Do not publish predictive shortlist categories when:

- the model does not improve on the baseline;
- future-year performance is unstable;
- geographic generalisation is poor;
- rankings change excessively under reasonable sensitivity tests;
- mandatory data is incomplete;
- results could create false confidence.

In this case, the capstone should present descriptive and historical exposure screening, model findings, and the annual-score limitations. It must not create a safe-area, buy/do-not-buy, or property-specific recommendation category.
