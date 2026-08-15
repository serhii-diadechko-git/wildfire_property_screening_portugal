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

Build a reproducible data-science, machine-learning, and GIS workflow that helps a prospective buyer narrow **broad mainland Portugal location-search areas** for further wildfire-exposure research. It combines a comparative annual estimate with observed historical recurrence and an official structural-hazard reference. Historical records are the training/testing evidence; the reusable model is scored only after the prior year's required inputs are complete.

## Intended use

The project supports the location-screening stage:

- shortlist comparatively lower-exposure residential areas;
- identify areas requiring caution;
- deprioritise consistently higher-exposure areas;
- mark locations with missing or unstable evidence.

It does not recommend the purchase of a specific property.

## Spatial design

- The analytical unit is a **1 km x 1 km grid cell per observation year**.
- The surrounding context is a **2 km buffer around each cell**.
- The 2 km buffer is used for nearby vegetation, slope, and previous-fire features.
- The 2 km value is the fixed context definition used by this project. No alternative-buffer sensitivity analysis was completed, so its choice remains a documented limitation for future research.

## Temporal methodology and model evaluation

In ERA5-Land, `2m_temperature` means air temperature at a standard height of 2 metres above the land surface. The `2m` label describes measurement height, not a 2 m spatial resolution or a 2 m context buffer.

> Final-model selection design: fit T=2010-2019; validate T=2020-2021; select only from that development evidence. `burned_share_next_year` is the sole current target; `burned_next_year` remains deferred. Once the final model was frozen, it was evaluated once during the final temporal evaluation period T=2022-2024; those results did not change its parameters.

Each observation is one 1 km x 1 km grid cell for predictor reference year `T`. Predictor information available at `T` estimates the observed wildfire outcome in `T+1`.

### Capstone purpose versus scientific modelling question

The **capstone purpose** is decision support at the broad-area search stage: compare consistent national evidence, narrow an initial location search, and then investigate shortlisted areas locally. It is not a property recommendation system.

The **scientific modelling question** is narrower: whether recent fire recurrence, landscape context, terrain, and predictor-year climate can estimate comparative next-year burned share better than a transparent recurrence-only benchmark. The model result is one source of evidence within the capstone workflow; it is not causal proof, a safety classification, or the final property decision.

- **Continuous target:** `burned_share_next_year`, the share of the cell burned in `T+1`.
- **Classification target:** `burned_next_year`, derived later from `burned_share_next_year` after inspecting the continuous-target distribution.
- **Historical-fire feature:** `fire_years_previous_10y_2km`, counting years from `T-10` through `T-1` inclusive in which the 2 km context buffer intersects burned area.

The canonical national panel covers `T=2015-2024`. A validated backward extension supplies development years `T=2010-2021`: fitting uses `T=2010-2019` and model-version selection uses `T=2020-2021`. ICNF coverage is `2000-2025`, covering pre-`T` history and observed `T+1` outcomes. The `T=2022-2024` rows are now used only as completed labels when refitting the selected operational version through outcome year 2025.

There is no temporal gap between the historical-fire window and predictor year `T`: the window is strictly before `T`, so it is information genuinely available at prediction time and is not leakage. ICNF burned areas are never a same-year `T` predictor. CLC provides broad, retrospective land-cover context; it is not annual parcel-level land cover. Assign CLC 2006 to `T=2010-2015`, CLC 2012 to `T=2016-2018`, and CLC 2018 to `T=2019-2025`, always keeping the land-cover reference year no later than `T`. The current official revised package is used for each reference layer, without claiming that its later revision was operationally available at `T`. ERA5-Land supplies coarse regional climate context, not 1 km weather: use only June-September (`JJAS`) values from `T`. Use the centroid-containing ERA5-Land cell when valid; if it is water-masked for a mainland analytical cell, use the validated deterministic nearest valid ERA5-Land land cell. This preserves the product and temporal aggregation and is not interpolation/downscaling. This is retrospective covariate reconstruction, not an exact real-time historical forecast.

## Final model finding and responsible-use boundary

The final nine-feature model is a two-stage burned-share regression model. It combines histogram-gradient-boosting decision-tree ensembles: a classifier for whether any burning occurs and a regressor for the burned share conditional on burning. This design accommodates many zero outcomes while allowing non-linear relationships and interactions among fire history, landscape, terrain, and climate, without imposing a fixed linear effect. In the complete `T=2020-2021` validation comparison, it improved all-row MAE (0.014674 to 0.014027) and burned-share-mass capture@20% (56.23% to 60.82%) over the previous nine-feature candidate configuration. Its post-selection final test at `T=2022-2024` improved all-row MAE over the historical baseline (0.020913 vs 0.029186) and captured 57.16% of observed burned-share mass in the tie-aware top 20%, versus 40.17% for the baseline; RMSE was marginally higher (0.110995 vs 0.110595). It provides a continuous comparative annual estimate, but not a calibrated probability, safety rating, property-level forecast, or purchase recommendation. The model was refit through outcome 2025 and produced a target-free `2026` estimate using T=2025 inputs. Its independent operational evaluation requires the observed ICNF 2026 outcome. The historical 2016-2025 recurrence screening remains supporting context. See `docs/model_v2_validation_selection.md`, `reports/validation/final_temporal_test_2022_2024.md`, `reports/validation/operational_forecast_readiness.md`, and `reports/validation/operational_forecast_2026_validation.md`.

## Scope

### In scope

- mainland Portugal;
- a national 1 km analytical grid;
- a fixed 2 km surrounding context buffer;
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

## Capstone decision and data questions

1. Which broad areas should be prioritised for further local location research based on comparative wildfire-exposure evidence?
2. Which patterns remain comparatively lower or higher across different completed years?
3. Does the final nine-feature model improve on historical recurrence alone during the later final temporal evaluation years?
4. How stable are its comparative estimates and limitations across time?
5. Which broad areas should be shortlisted for local verification, investigated with caution, or marked as insufficient evidence?

## Scientific modelling hypothesis and final evidence

The scientific component tests whether recent wildfire recurrence, landscape context,
terrain, and predictor-year climate conditions can estimate the comparative
next-year burned share of mainland Portugal 1 km cells better than a
transparent historical-recurrence baseline. The target is the continuous
`burned_share_next_year`; it is not a property-level probability or a safety
classification. This limited empirical question supports the capstone's
broad-area screening purpose; it does not define a buy/do-not-buy decision.

The hypothesis received partial support. The final nine-feature model was selected from the
development validation period and then evaluated once during the final temporal
evaluation period `T=2022-2024`: it reduced all-row MAE from 0.029186 to 0.020913 and
increased tie-aware burned-share-mass capture@20% from 40.17% to 57.16% versus
the transparent historical-recurrence benchmark. RMSE was marginally higher
(0.110995 versus 0.110595), and the high-burn 2025 outcome remained difficult.
This supports cautious comparative screening on completed historical years; it
does not yet validate the target-free 2026 operational estimate, whose outcome
is not available.

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

The completed evidence supports the published 2026 annual comparative exposure layer for broad location comparison. Its retained model is not a buyer recommendation. Each published annual estimate must carry its forecast year, input cutoff, documented model specification, and calibration limitation.

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

Measure how many residentially relevant cells and municipalities have meaningful wildfire exposure. Housing-market data is outside the completed project scope unless a future research version documents and validates it.

### Risk and sensitivity

Test model uncertainty, false reassurance, target thresholds, the fixed 2 km buffer, temporal stability, geographic generalisation, source-release dependency, and competitor overlap.

## Success criteria

### Required completion criteria

- use documented public data sources;
- build the reproducible 1 km cell-year dataset using the retained nine-predictor contract;
- return a score, insufficient-evidence status, or documented exclusion for every canonical cell, with coverage revalidated for each annual release;
- represent every mainland municipality containing eligible cells;
- publish a comparative estimate, insufficient-evidence status, or documented exclusion only when mandatory data is complete;
- produce clear maps, machine-readable score/rank tables, uncertainty flags, and limitations;
- document annual rescoring and model retraining separately.

### Model evaluation targets

- compare the model with a historical-fire-frequency baseline on future-year data;
- require performance above random ranking;
- target capture of at least 40% of affected cells within the highest-risk 20% of predictions;
- consider any future automated recommendation category only after separate evidence and governance review; it is not part of this project.

These are evaluation targets, not guaranteed project outcomes.

## Readiness assessment

- Decision-maker and decision: **ready**
- Measurable business and data questions: **ready**
- Completion criteria and evaluation targets: **validated historical evaluation and published 2026 comparative estimate; annual update cycle documented**
- Minimum schema: **aligned with the workbook**
- Analysis-to-decision alignment: **ready**
- 60-second explanation: **ready**

## Annual-maintenance checks

1. Register and validate each new annual ICNF and ERA5-Land source before use.
2. Revalidate CRS, schema, checksums, licensing/terms, and geographic coverage.
3. Revalidate the annual source cutoff, model checksum, coverage, and missing-data status before publishing a comparative estimate.
4. Evaluate the already-published estimate when the corresponding ICNF outcome becomes available, then refit the unchanged selected specification for the following cycle.
