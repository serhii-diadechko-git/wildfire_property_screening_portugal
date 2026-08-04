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

- [ ] Download one recent ICNF burned-area dataset.
- [ ] Inspect its CRS, fields, geometry validity, and feature count.
- [ ] Acquire and validate governed CLC 2006/2012/2018 packages, classes, coverage, and release-availability evidence.
- [ ] Download a Copernicus DEM sample.
- [ ] Validate ERA5-Land JJAS temperature, day-weighted precipitation, and layer-1 soil-water inputs.
- [ ] Build a 1 km pilot grid for one selected area.
- [ ] Create the initial 2 km buffer around each pilot cell.
- [ ] Prove that the required sources can produce one complete cell-year record.
- [ ] Test the built-up share as a residential-relevance proxy.
- [ ] Measure source coverage and mandatory-feature completeness.
- [ ] Record licences, source URLs, versions, and download dates.
- [ ] Decide whether the provisional 95% coverage target is realistic.
- [ ] Make a go/no-go decision on national processing.

## Phase 2 - Repository and reproducibility

- [ ] Create environment and dependency files.
- [ ] Configure paths, years, CRS, 1 km grid size, and 2 km buffer.
- [ ] Keep raw, interim, and processed data separate.
- [ ] Add data-download instructions without committing large source files.
- [ ] Add logging and data-validation checks.
- [ ] Record source versions and collection dates in a machine-readable file.

## Phase 3 - National data preparation

- [ ] Create the mainland boundary and 1 km analytical grid.
- [ ] Fix the working CRS and CAOP version.
- [ ] Prepare annual ICNF burned-area layers.
- [ ] Prepare comparable land-cover layers.
- [ ] Calculate `built_up_share` inside each 1 km cell.
- [ ] Calculate `forest_shrub_share_2km` inside each 2 km buffer.
- [ ] Derive `mean_slope_2km` from Copernicus DEM.
- [ ] Calculate `fire_years_previous_10y_2km` without temporal leakage.
- [ ] Aggregate JJAS mean temperature, day-weighted total precipitation, and mean layer-1 soil water from predictor year `T` only.
- [ ] Calculate `burned_share_next_year` for each 1 km cell.
- [ ] Create `cell_year_id` and the required technical identifiers.
- [ ] Validate the residential-relevance rule.
- [ ] Produce the first MVP modelling table.
- [ ] Report national and municipality-level coverage.

## Phase 4 - Exploratory analysis

- [ ] Report temporal and geographic coverage.
- [ ] Analyse missing values and geometry problems.
- [ ] Map historical burned areas and recurrence.
- [ ] Analyse the `burned_share_next_year` distribution.
- [ ] Define and document the `burned_next_year` threshold.
- [ ] Analyse class imbalance and positive-class prevalence.
- [ ] Compare outcomes across the agreed MVP features.
- [ ] Document possible spatial and temporal leakage.

## Phase 5 - Modelling and acceptance evaluation

- [ ] Freeze model-acceptance rules before reviewing final test results.
- [ ] Build the historical-fire regression baseline using `fire_years_previous_10y_2km`.
- [ ] Train a Random Forest Regressor for continuous `burned_share_next_year`.
- [ ] Use temporal train, validation, and test splits.
- [ ] Add a geographic holdout or spatial cross-validation where practical.
- [ ] Evaluate regression with MAE and RMSE by later year.
- [ ] Only after target-distribution review and a documented threshold decision, optionally derive `burned_next_year`, train logistic regression, and evaluate precision, recall, F1, ROC-AUC, PR-AUC, calibration, capture@20%, and prevalence.
- [ ] Compare each model with the historical baseline.
- [ ] Compare results by year and region.
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
