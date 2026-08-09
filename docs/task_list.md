# Current Task List

The validated project state is a Model V2 nine-feature annual continuous burned-share model plus a separate historical recurrence screening layer. Model V2 was selected using fit `T=2010-2019` and complete validation `T=2020-2021`, with no `T=2022-2024` rows read during selection. The frozen configuration then completed its one held-out final evaluation on `T=2022-2024`, before the operational model was refit through `T=2024` / observed outcome 2025 and the 2026 comparative estimate was published.

## Completed analytical workflow

- [x] Register immutable CAOP, ICNF 2000-2025, governed CLC 2006/2012/2018, Copernicus DEM GLO-30, and ERA5-Land sources.
- [x] Create and validate the 89,112-cell EPSG:3763 canonical 1 km grid.
- [x] Derive 2 km mainland-masked context buffers; 2 km is context, not a second grid.
- [x] Build and validate the bounded national spatial components used by the final nine-feature model.
- [x] Resolve systematic ERA5-Land coastal masking with the validated nearest-valid-land-cell fallback.
- [x] Extend model training backward to `T=2010` using the governed source rules.
- [x] Compare the historical-recurrence baseline and predeclared nine-feature two-stage regression configurations on `T=2020-2021`.
- [x] Select documented Model V2 from validation-only evidence, then evaluate the frozen configuration once on held-out `T=2022-2024` data.
- [x] Refit Model V2 through observed outcome 2025.
- [x] Publish the target-free 2026 comparative estimate and QGIS-ready layer.
- [x] Publish the separate 2016-2025 historical recurrence screening and ICNF comparison.
- [x] Produce the QGIS projects, presentation figures, reports, and final capstone deck.

## Current maintenance cycle

- [x] Consolidate reusable model, climate, evaluation, and geospatial helpers.
- [x] Consolidate the final nine-feature feature, model, climate, and geospatial implementation.
- [x] Move the canonical geometry lookup to `data/processed/reference/canonical_mainland_grid_1km.gpkg`.
- [x] Complete the public-reproducibility, notebook, documentation, and presentation consolidation.
- [x] Release the repository's own code, notebooks, documentation, and original figures under the MIT License; provider datasets remain subject to their own terms.

## Next annual update (forecast year 2027)

- [ ] Acquire and register ICNF burned areas for 2026 after official publication.
- [ ] Acquire and validate ERA5-Land JJAS 2026 after the completed predictor year is available.
- [ ] Add the labelled `T=2025` row using observed outcome 2026.
- [ ] Refit the unchanged nine-feature specification through `T=2025`.
- [ ] Derive the target-free `T=2026` matrix and publish the 2027 comparative estimate.
- [ ] Validate checksums, source cutoffs, missingness, model reload, QGIS paths, and report wording.

The annual cycle is defined in [operational_forecast_cycle.md](operational_forecast_cycle.md). Any new feature, threshold, classifier, or tuning exercise is a new research version and must not silently alter the documented Model V2 operational contract.
