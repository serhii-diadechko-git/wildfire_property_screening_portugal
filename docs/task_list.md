# Task List - Data Collection and Analysis

> Canonical sequence: resolve source blockers, build/validate the full panel, then freeze modelling decisions before final T=2022–2024 evaluation. The 2023→2024 work is a feasibility pilot only.

## Phase 0 - Freeze the MVP

- [ ] Confirm the project title and decision statement.
- [ ] Use `reports/validation/canonical_full_scope_readiness.md` as the authoritative design gate.
- [ ] Freeze the required source list.
- [ ] Freeze the 1 km grid and initial 2 km context buffer for the pilot.
- [ ] Freeze the MVP columns listed in `docs/data_dictionary.md`.
- [ ] Review the completion criteria and model targets in `docs/success_criteria.md`.

## Phase 1 - Data-feasibility pilot

- [x] Download and register the required ICNF annual burned-area archives.
- [x] Inspect their CRS, fields, geometry validity, and feature counts.
- [x] Acquire and validate the current official revised CLC 2006/2012/2018 packages and Portugal clips, and enforce `reference_year <= T`.
- [x] Acquire and validate the mainland Copernicus DEM GLO-30 tiles.
- [x] Validate ERA5-Land JJAS temperature, day-weighted precipitation, and layer-1 soil-water inputs.
- [x] Reuse the canonical 1 km grid in a representative 10-cell pilot.
- [x] Create mainland-masked 2 km outward context buffers for the pilot cells.
- [x] Prove that the required sources can produce the canonical seven predictors and continuous target.
- [x] Test the built-up share as a residential-relevance proxy.
- [x] Measure source coverage and mandatory-feature completeness.
- [x] Record licences, source URLs, versions, and download dates.
- [x] Confirm national processing feasibility with documented ERA5-Land water-mask missingness.
- [x] Approve national panel construction after the deterministic representative pilot.

## Phase 2 - Repository and reproducibility

- [ ] Create environment and dependency files.
- [ ] Configure paths, years, CRS, 1 km grid size, and 2 km buffer.
- [ ] Keep raw, interim, and processed data separate.
- [ ] Add data-download instructions without committing large source files.
- [ ] Add logging and data-validation checks.
- [ ] Record source versions and collection dates in a machine-readable file.

## Phase 3 - National data preparation

- [x] Reuse and validate the mainland boundary and 89,112-cell 1 km analytical grid.
- [x] Fix the working CRS and CAOP version.
- [x] Prepare annual ICNF burned-area layers with logged derived-only geometry repair.
- [x] Prepare governed CLC 2006/2012/2018 land-cover components.
- [x] Calculate `built_up_share` inside each 1 km cell.
- [x] Calculate `forest_shrub_share_2km` inside each mainland-masked 2 km buffer.
- [x] Derive `mean_slope_2km` from Copernicus DEM in a metric projected CRS.
- [x] Calculate `fire_years_previous_10y_2km` without temporal leakage.
- [x] Aggregate JJAS mean temperature, day-weighted total precipitation, and mean layer-1 soil water from predictor year `T` only.
- [x] Calculate `burned_share_next_year` for each 1 km cell.
- [x] Create deterministic `cell_year_id` and the required technical identifiers.
- [ ] Validate the residential-relevance rule.
- [x] Produce and validate the canonical 891,120-row analytical panel for panel EDA.
- [ ] Report national and municipality-level coverage.

## Phase 4 - Exploratory analysis

- [x] Report temporal and national-grid coverage.
- [x] Analyse missing values and resolve systematic ERA5-Land coastal masking.
- [ ] Map historical burned areas and recurrence.
- [x] Analyse the `burned_share_next_year` distribution and temporal zero inflation.
- [ ] Define and document the `burned_next_year` threshold.
- [x] Analyse zero/positive prevalence while keeping the classification threshold deferred.
- [x] Compare predictor and target distributions, correlations, extremes, and temporal splits.
- [x] Document spatial and temporal leakage controls for the panel.

## Phase 5 - Modelling and acceptance evaluation

- [x] Freeze train/validation regression metrics and the provisional-selection rule before reviewing validation results.
- [ ] Freeze final model-acceptance rules before reviewing final test results.
- [x] Build the historical-fire regression baseline using `fire_years_previous_10y_2km` on training years only.
- [x] Train a deterministic, intentionally limited Random Forest Regressor candidate for continuous `burned_share_next_year`.
- [x] Assess a deterministic Tweedie regression candidate for the exact-zero plus continuous-positive target without deriving a classification threshold.
- [ ] Use temporal train, validation, and test splits.
- [ ] Add a geographic holdout or spatial cross-validation where practical.
- [x] Evaluate train/validation regression overall and by validation year with MAE/RMSE, positive-target MAE/RMSE, mean predicted versus observed burned share, and positive-cell capture@20%; keep the zero-prediction error as a reference only.
- [ ] Only after target-distribution review and a documented threshold decision, optionally derive `burned_next_year`, train logistic regression, and evaluate precision, recall, F1, ROC-AUC, PR-AUC, calibration, capture@20%, and prevalence.
- [x] Compare each train/validation candidate with the historical baseline under the predeclared gate; no candidate passed, so the final test remains unopened.
- [ ] Compare final evaluation results by year and region only after a candidate earns final-test access.
- [ ] Record whether the model is accepted for predictive recommendation.

## Phase 6 - Residential screening and recommendations

- [ ] Produce scores only for cells with complete mandatory data.
- [ ] Mark incomplete cases as insufficient evidence.
- [ ] Calculate score stability and uncertainty flags.
- [ ] Define recommendation categories before reviewing final locations.
- [ ] Compare results with the official ICNF structural hazard map.
- [ ] Flag major disagreements for caution.
- [ ] Produce ranked summaries by grid cell and administrative area.
- [ ] If the model is not accepted, publish descriptive and historical results instead of predictive shortlist categories.

## Phase 7 - Market and value analysis

- [ ] Review ICNF, MapaFogos, A Minha Terra, EFFIS, and related tools.
- [ ] Build the competitor and segment matrix.
- [ ] Compare coverage, resolution, time horizon, update frequency, and buyer focus.
- [ ] Quantify the number of eligible locations with meaningful exposure.
- [ ] State the capstone's added value without claiming unique market novelty.

## Phase 8 - Sensitivity and responsible-use checks

- [ ] Test at least one alternative context-buffer distance if practical.
- [ ] Test at least one alternative target threshold.
- [ ] Test one alternative grid size only if the MVP is already complete and processing is feasible.
- [ ] Analyse ranking stability across years and models.
- [ ] Identify missing-data and out-of-distribution cases.
- [ ] Document false-positive and false-negative consequences.
- [ ] Finalise the insufficient-evidence rule.

## Phase 9 - Final delivery

- [ ] Clean notebooks and move reusable logic into `src/`.
- [ ] Recheck consistency between the workbook, README, and all files in `docs/`.
- [ ] Report completed deliverables separately from achieved model performance.
- [ ] Produce at least two maps, one performance figure, and one ranked table.
- [ ] Write the recommendation and limitations.
- [ ] State whether the model was accepted for predictive recommendation.
- [ ] Verify that every analysis supports the property-location decision.
- [ ] Rehearse the 60-second pitch.
- [ ] Submit the completed workbook and repository outputs.
