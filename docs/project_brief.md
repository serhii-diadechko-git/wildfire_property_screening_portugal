# Project Brief

## Project title

**Reproducible Wildfire Exposure Screening for Residential Location Selection in Mainland Portugal**

## Decision-maker

A prospective homebuyer choosing a location in mainland Portugal.

## Decision

Which residential areas should be shortlisted, reviewed with caution, or deprioritised based on their relative wildfire exposure?

## Business problem

A property purchase is a long-term and expensive decision. Wildfire exposure differs across mainland Portugal, while relevant public information is distributed across several datasets and tools. A buyer needs a transparent way to compare residential locations before investigating individual properties.

## Project goal

Use public geospatial data and machine-learning methods to estimate comparative next-calendar-year burned-share exposure across mainland Portugal, alongside a transparent historical screening output. Historical records are the training/testing evidence; the reusable model is scored only after the prior year's required inputs are complete.

## Intended use

The project supports the location-screening stage:

- shortlist comparatively lower-exposure residential areas;
- identify areas requiring caution;
- deprioritise consistently higher-exposure areas;
- mark locations with missing or unstable evidence.

It does not recommend the purchase of a specific property.

## Spatial design

- The analytical unit is a **1 km x 1 km grid cell per observation year**.
- The initial surrounding context is a **2 km buffer around each cell**.
- The 2 km buffer is used for nearby vegetation, slope, and previous-fire features.
- The 2 km value is an initial parameter and will be checked through sensitivity analysis.

## Temporal methodology and model evaluation

In ERA5-Land, `2m_temperature` means air temperature at a standard height of 2 metres above the land surface. The `2m` label describes measurement height, not a 2 m spatial resolution or a 2 m context buffer.

> Model v2 selection design: fit T=2010-2019; validate T=2020-2021; select only from that development evidence. `burned_share_next_year` is the sole current target; `burned_next_year` remains deferred. Once V2 was frozen, it was evaluated once on the held-out final period T=2022-2024; those results did not change its parameters.

Each observation is one 1 km x 1 km grid cell for predictor reference year `T`. Predictor information available at `T` estimates the observed wildfire outcome in `T+1`.

- **Continuous target:** `burned_share_next_year`, the share of the cell burned in `T+1`.
- **Classification target:** `burned_next_year`, derived later from `burned_share_next_year` after inspecting the continuous-target distribution.
- **Historical-fire feature:** `fire_years_previous_10y_2km`, counting years from `T-10` through `T-1` inclusive in which the 2 km context buffer intersects burned area.

The canonical national panel covers `T=2015-2024`. A validated backward extension supplies development years `T=2010-2021`: fitting uses `T=2010-2019` and model-version selection uses `T=2020-2021`. ICNF coverage is `2000-2025`, covering pre-`T` history and observed `T+1` outcomes. The `T=2022-2024` rows are now used only as completed labels when refitting the selected operational version through outcome year 2025.

There is no temporal gap between the historical-fire window and predictor year `T`: the window is strictly before `T`, so it is information genuinely available at prediction time and is not leakage. ICNF burned areas are never a same-year `T` predictor. CLC provides broad, retrospective land-cover context; it is not annual parcel-level land cover. Assign CLC 2006 to `T=2010-2015`, CLC 2012 to `T=2016-2018`, and CLC 2018 to `T=2019-2025`, always keeping the land-cover reference year no later than `T`. The current official revised package is used for each reference layer, without claiming that its later revision was operationally available at `T`. ERA5-Land supplies coarse regional climate context, not 1 km weather: use only June-September (`JJAS`) values from `T`. Use the centroid-containing ERA5-Land cell when valid; if it is water-masked for a mainland analytical cell, use the validated deterministic nearest valid ERA5-Land land cell. This preserves the product and temporal aggregation and is not interpolation/downscaling. This is retrospective covariate reconstruction, not an exact real-time historical forecast.

## Final model finding and responsible-use boundary

Model v2 is a nine-feature two-stage burned-share regression model. It combines histogram-gradient-boosting decision-tree ensembles: a classifier for whether any burning occurs and a regressor for the burned share conditional on burning. This design accommodates many zero outcomes while allowing non-linear relationships and interactions among fire history, landscape, terrain, and climate, without imposing a fixed linear effect. In the complete `T=2020-2021` validation comparison, V2 improved all-row MAE (0.014674 to 0.014027) and burned-share-mass capture@20% (56.23% to 60.82%) over Model v1. Its post-selection final test at `T=2022-2024` improved all-row MAE over the historical baseline (0.020913 vs 0.029186) and captured 57.16% of observed burned-share mass in the tie-aware top 20%, versus 40.17% for the baseline; RMSE was marginally higher (0.110995 vs 0.110595). It provides a continuous comparative annual estimate, but not a calibrated probability, safety rating, property-level forecast, or purchase recommendation. The model was refit through outcome 2025 and produced a target-free `2026` estimate using T=2025 inputs. Its independent operational evaluation requires the observed ICNF 2026 outcome. The historical 2016-2025 recurrence screening remains supporting context. See `docs/model_v2_validation_selection.md`, `reports/validation/final_temporal_test_2022_2024.md`, `reports/validation/operational_forecast_readiness.md`, and `reports/validation/operational_forecast_2026_validation.md`.

## Scope

### In scope

- mainland Portugal;
- a national 1 km analytical grid;
- an initial 2 km surrounding context buffer;
- historical burned-area patterns;
- built-up share as an initial residential-relevance proxy;
- surrounding forest and shrubland;
- mean terrain slope;
- warm-season temperature, precipitation, and layer-1 soil water;
- temporal and geographic model validation;
- annual scoring after the prior year's required inputs are complete, and annual refitting only after the newest ICNF outcome is available.

### Out of scope

- property prices and investment returns;
- flood, coastal, seismic, crime, or general quality-of-life analysis;
- exact building construction and fire resistance;
- private vegetation maintenance and evacuation access;
- guaranteed long-term or property-level safety;
- alternative feature sets or tuning beyond the retained nine-feature model,
  unless evaluated as a separately versioned research change.

## Business and data questions

1. Which eligible residential areas have the lowest relative wildfire exposure?
2. Which areas remain comparatively low-exposure across different years?
3. Which environmental and historical variables are most associated with wildfire exposure?
4. How reliable is the model in future years and held-out geographic areas?
5. Which locations should be shortlisted, reviewed with caution, deprioritised, or marked as insufficient evidence?

## Research hypothesis and final evidence

The project tests whether recent wildfire recurrence, landscape context,
terrain, and predictor-year climate conditions can estimate the comparative
next-year burned share of mainland Portugal 1 km cells better than a
transparent historical-recurrence baseline. The target is the continuous
`burned_share_next_year`; it is not a property-level probability or a safety
classification.

The hypothesis received partial support in the complete development-validation
comparison. Model v2 improved all-row MAE and both ranking capture diagnostics
over its Model v1 reference, while positive-target MAE was effectively
unchanged. This supports a cautious model-version change, not a claim that V2
has already passed an independent future-year test.

The conclusion is therefore limited and comparative. The model may help narrow
broad-area location research, but it is not sufficiently stable or calibrated
to support a safety guarantee, an individual-property forecast, or a
buy/do-not-buy recommendation. The detailed metric evidence is recorded in
`docs/model_v2_validation_selection.md`.

The project also displays a separate official ICNF structural-hazard reference
layer. The source is the official 25 m SRUP-CPIR 2020-2030 classification; the
2020-2030 label identifies that source/version or planning period, not a
prediction of fires during those years. The project summarizes the predominant
valid official class within each 1 km mainland cell for comparison with the
observed historical recurrence layer. It is not an ML prediction, target, or
accuracy label for the project model.

## Recommendation frame

The completed evidence supports a future annual comparative exposure layer for broad location comparison once its source gate is complete. Its retained model is not a buyer recommendation. Each published forecast must carry its forecast year, input cutoff, model version, and calibration limitation.

The historical screening is most useful when an area has:

- lower historical recurrence context;
- reasonable stability across evaluation years;
- complete mandatory data;
- acceptable uncertainty;
- no major unexplained conflict with official hazard information.

Areas with higher historical recurrence should receive more local investigation. Unstable, incomplete, or conflicting cases should be marked for further investigation.

## Analysis map and market context

### Market overview

Review official, real-time, annual, and property-oriented wildfire-information tools to identify target users, update cycles, spatial resolution, and information gaps.

### Geographic comparison

Compare national coverage, spatial resolution, and the ability to compare residential locations consistently across mainland Portugal.

### Value analysis

Compare access, transparency, update frequency, and usefulness for property-location screening. Property-price analysis is outside the capstone scope.

### Competitor and segment mapping

Compare official tools, real-time services, annual susceptibility products, and related property-risk services for authorities, landowners, emergency users, and property buyers.

### Demand proxy

Measure how many residentially relevant cells and municipalities have meaningful wildfire exposure. Do not add housing-market data unless the MVP is already complete and the source is confirmed.

### Risk and sensitivity

Test model uncertainty, false reassurance, target thresholds, the initial 2 km buffer, temporal stability, geographic generalisation, source-release dependency, and competitor overlap.

## Success criteria

### Required completion criteria

- use documented public data sources;
- build the reproducible 1 km cell-year dataset using the agreed MVP columns;
- return a score, insufficient-evidence status, or documented exclusion for every canonical cell, with coverage revalidated for each annual release;
- represent every mainland municipality containing eligible cells;
- assign recommendations only when mandatory data is complete;
- produce clear maps, ranked tables, uncertainty flags, and limitations;
- document annual rescoring and model retraining separately.

### Model evaluation targets

- compare the model with a historical-fire-frequency baseline on future-year data;
- require performance above random ranking;
- target capture of at least 40% of affected cells within the highest-risk 20% of predictions;
- use predictive recommendations only if the model improves on the baseline and generalises across years and regions.

These are evaluation targets, not guaranteed project outcomes.

## Readiness assessment

- Decision-maker and decision: **ready**
- Measurable business and data questions: **ready**
- Completion criteria and evaluation targets: **validated historical evaluation and published 2026 comparative estimate; annual update cycle documented**
- Minimum schema: **aligned with the workbook**
- Analysis-to-decision alignment: **ready**
- 60-second explanation: **ready**

## First-sprint validation gates

1. Download and inspect one sample from each required source.
2. Confirm CRS, schema, licensing, and geographic coverage.
3. Verify comparable land-cover editions.
4. Test one small-area 1 km grid and 2 km buffer workflow.
5. Validate the residential-relevance proxy.
6. Revalidate the annual source cutoff before publishing each new comparative estimate.
7. Confirm coverage and missing-data status for each annual update.
