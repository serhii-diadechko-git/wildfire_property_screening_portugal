# Capstone presentation validation

Validation date: 2026-08-07

Author: Serhii Diadechko

Presentation: `reports/presentation/v2_wildfire_exposure_screening_capstone_presentation.pptx`

## Outcome

The retained 13-slide, 16:9 presentation was refreshed after the final temporal evaluation and operational refit. It presents three explicitly separated views:

1. observed 2016-2025 historical recurrence screening for broad location comparison;
2. official ICNF structural-hazard context at the common 1 km comparison resolution; and
3. the frozen nine-feature two-part burned-share regression model (technical term: hurdle model) used for the target-free 2026 comparative estimate.

The deck no longer contains the superseded conclusion that no model advanced. It records the frozen `T=2022-2024` comparison: the two-part regression model improved all-row MAE and Capture@20% versus the historical-recurrence baseline, while RMSE was similar and the unusually high-burn `T=2024` outcome was underpredicted. The published 2026 output remains a target-free comparative estimate, not a probability, property-level safety guarantee, insurance estimate, or purchase recommendation.

## Updated slide evidence

| Slide | Verified purpose | Primary repository evidence |
|---:|---|---|
| 1 | Current project conclusion and two-product distinction | `README.md`; final-test and operational-validation reports |
| 3 | National scope and 15 labelled predictor years | national-panel and final-test reports |
| 4 | Separation of observed history, frozen ML evaluation and official comparison | data dictionary; final-test report; operational cycle |
| 5 | Zero-heavy target and complementary error/ranking diagnostics | panel EDA; final-test report; success criteria |
| 6 | Frozen baseline versus nine-feature final-test comparison | final-test metrics JSON and regenerated comparison figure |
| 10 | Side-by-side historical recurrence, official ICNF structural hazard, and 2026 model estimate | the two validated spatial GeoPackages and the existing plotting helper used by the final notebook |
| 12 | Evidence-to-use contract and current deliverables | model decision; operational validation; spatial-output registry |
| 13 | Updated assessor questions and evidence-backed answers | final-test, model-decision, operational and historical-screening reports |

Slides 2, 7-9, and 11 retain the validated historical-screening, QGIS and ICNF-comparison material. Slide 10 now displays all three complementary maps without changing their data, thresholds, styling, or interpretation.

## Numerical and terminology checks

- Canonical grid: 89,112 mainland cells.
- Historical-screening evidence window: 2016-2025.
- Frozen model fit years: `T=2010-2019`; validation years: `T=2020-2021`; final temporal test: `T=2022-2024`.
- Final-test historical-recurrence baseline: MAE 0.0292, RMSE 0.1106, deterministic positive-cell Capture@20% 48.2% (tie-aware 49.3%), burned-share-mass capture 40.2%.
- Final-test nine-feature two-part regression: MAE 0.0214, RMSE 0.1107, deterministic and tie-aware positive-cell Capture@20% 50.0%, burned-share-mass capture 60.0%.
- Historical exposure remains observed evidence, separate from annual model estimates.
- ICNF structural hazard remains an independent official comparison layer, not a model target or accuracy benchmark.
- The deck consistently distinguishes 1 km analytical cells from recurrence measured in a 2 km context.
- No absolute personal filesystem path or retired model-selection report reference remains in visible text or speaker notes.
- Speaker notes are present on all 13 slides.

## Rendering and packaging QA

- The existing deck layout, visual theme, slide order and historical-screening figures were preserved.
- The embedded slide-6 chart was replaced with the frozen final-temporal comparison generated from `data/processed/extended_model_selection_2010_2021/final_temporal_test_metrics.json`.
- All 13 slides were rendered; the updated slide 10 was inspected at full size.
- Template-fidelity validation passed with zero issues.
- Official slide-overflow test: `Test passed. No overflow detected.`
- PPTX size: 1,360,224 bytes.
- PPTX SHA-256: `7012E134925AEF6DE950C44C0CD5636E682A01685D3879307F2690CB05B4312B`.

## Validation decision

**Passed.** The editable PPTX is visually readable and consistent with the final nine-feature model state, the separate historical-screening output, and the documented operational limitations. A PDF export is intentionally not tracked because it is a duplicate delivery format.
