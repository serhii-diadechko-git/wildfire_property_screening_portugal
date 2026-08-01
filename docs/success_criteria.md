# Success Criteria and Model Acceptance Rules

## Purpose

This document separates:

- **required project completion criteria**, which are mainly under project control;
- **model evaluation targets**, which must be tested and cannot be guaranteed in advance.

## A. Required project completion criteria

### 1. Reproducible data pipeline

**Target:** create documented steps that transform the required public sources into the agreed 1 km cell-year dataset.

**Check:** rerun the pipeline for the pilot area and confirm that the same schema and results are produced.

### 2. Consistent spatial design

**Target:** use one 1 km analytical grid and one clearly documented initial 2 km context buffer.

**Check:** confirm that cell-level and buffer-level fields follow the definitions in `docs/data_dictionary.md`.

### 3. Validated residential-relevance rule

**Target:** define which 1 km cells are relevant to residential location screening.

**Check:** inspect land-cover class definitions and mapped samples. Built-up land must not automatically be called residential.

### 4. Coverage of eligible cells

**Planning target:** return one of the following for at least 95% of eligible cells:

- predictive score;
- insufficient-evidence status;
- documented exclusion reason.

**Check:**

```text
coverage = cells with a result status / all eligible cells
```

The 95% value must be confirmed during the feasibility pilot. It is not guaranteed before source coverage is measured.

### 5. Mandatory data completeness

**Target:** assign predictive recommendations only when all mandatory groups are present:

- historical burned-area feature;
- land-cover features;
- mean slope;
- temperature and precipitation.

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

**Target:** document annual rescoring and retraining as separate processes.

- **Rescoring:** apply an accepted model to new annual features.
- **Retraining:** add new observed outcomes, refit models, and repeat validation.

## B. Model evaluation targets

### 1. Baseline comparison

Compare the machine-learning model with a simple baseline that ranks cells using `fire_years_previous_10y_2km`.

The comparison must use future-year test data. A complex model is not accepted because of training performance alone.

### 2. Performance above random ranking

For an imbalanced classification problem, PR-AUC should be compared with positive-class prevalence.

**Minimum evaluation condition:** PR-AUC above positive-class prevalence on final test data.

This condition alone does not prove that the model is useful.

### 3. Top-risk capture

Rank test cells from highest to lowest predicted exposure.

```text
capture@20% = affected cells in the highest-risk 20% / all affected cells
```

**Evaluation target:** capture at least 40% of affected cells within the highest-risk 20%.

A random 20% selection would be expected to capture about 20%. The 40% value is a useful target, not a guaranteed outcome.

### 4. Generalisation and calibration

Report:

- precision;
- recall;
- F1-score;
- ROC-AUC;
- PR-AUC;
- probability calibration;
- capture@20%;
- performance by test year;
- performance by region or geographic holdout.

No single metric is sufficient on its own.

## C. Model acceptance decision

### Accept for predictive recommendation

Predictive residential screening is allowed only when:

- the model improves on the historical baseline;
- it performs better than random ranking;
- performance is reasonably stable across years and regions;
- probability calibration and ranking quality are acceptable;
- missing-data and uncertainty rules are applied.

### Do not accept for predictive recommendation

Do not publish predictive shortlist categories when:

- the model does not improve on the baseline;
- future-year performance is unstable;
- geographic generalisation is poor;
- rankings change excessively under reasonable sensitivity tests;
- mandatory data is incomplete;
- results could create false confidence.

In this case, the capstone should present descriptive and historical exposure screening, model findings, and the reason predictive recommendations are not justified.
