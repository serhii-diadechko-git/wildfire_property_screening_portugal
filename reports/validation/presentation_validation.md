# Capstone presentation validation

Validation date: 2026-08-06

Author: Serhii Diadechko

Presentation: `reports/presentation/v2_wildfire_exposure_screening_capstone_presentation.pptx`

PDF export: `reports/presentation/v2_wildfire_exposure_screening_capstone_presentation.pdf`

## Outcome

The retained 13-slide, 16:9 presentation was refreshed after the final temporal evaluation and operational refit. It now presents two complementary, explicitly separated products:

1. observed 2016-2025 historical recurrence screening for broad location comparison; and
2. the frozen nine-feature hurdle model used for cautious annual comparative estimates.

The deck no longer contains the superseded conclusion that no model advanced. It records the frozen `T=2022-2024` comparison: the hurdle improved all-row MAE and Capture@20% versus the historical-recurrence baseline, while RMSE was similar and the unusually high-burn `T=2024` outcome was underpredicted. The published 2026 output remains a target-free comparative estimate, not a probability, property-level safety guarantee, insurance estimate, or purchase recommendation.

## Updated slide evidence

| Slide | Verified purpose | Primary repository evidence |
|---:|---|---|
| 1 | Current project conclusion and two-product distinction | `README.md`; final-test and operational-validation reports |
| 3 | National scope and 15 labelled predictor years | national-panel and final-test reports |
| 4 | Separation of observed history, frozen ML evaluation and official comparison | data dictionary; final-test report; operational cycle |
| 5 | Zero-heavy target and complementary error/ranking diagnostics | panel EDA; final-test report; success criteria |
| 6 | Frozen baseline versus nine-feature final-test comparison | final-test metrics JSON and regenerated comparison figure |
| 12 | Evidence-to-use contract and current deliverables | model decision; operational validation; spatial-output registry |
| 13 | Updated assessor questions and evidence-backed answers | final-test, model-decision, operational and historical-screening reports |

Slides 2 and 7-11 retain the validated historical-screening, QGIS and ICNF-comparison material. Their data, thresholds, styling and interpretation were not changed.

## Numerical and terminology checks

- Canonical grid: 89,112 mainland cells.
- Historical-screening evidence window: 2016-2025.
- Frozen model fit years: `T=2010-2019`; validation years: `T=2020-2021`; final temporal test: `T=2022-2024`.
- Final-test historical-recurrence baseline: MAE 0.0292, RMSE 0.1106, Capture@20% 48.2%.
- Final-test nine-feature hurdle: MAE 0.0214, RMSE 0.1107, Capture@20% 50.0%.
- Historical exposure remains observed evidence, separate from annual model estimates.
- ICNF structural hazard remains an independent official comparison layer, not a model target or accuracy benchmark.
- The deck consistently distinguishes 1 km analytical cells from recurrence measured in a 2 km context.
- No absolute personal filesystem path or retired model-selection report reference remains in visible text or speaker notes.
- Speaker notes are present on all 13 slides.

## Rendering and packaging QA

- The existing deck layout, visual theme, slide order and historical-screening figures were preserved.
- The embedded slide-6 chart was replaced with the frozen final-temporal comparison generated from `data/processed/extended_model_selection_2010_2021/final_temporal_test_metrics.json`.
- Targeted slide renders were inspected during editing.
- Microsoft PowerPoint exported a new 13-page PDF from the corrected PPTX.
- All 13 PDF pages were rasterised and visually inspected as a contact sheet; no clipping, overlap or unreadable content was found.
- Official slide-overflow test: `Test passed. No overflow detected.`
- PPTX size: 2,252,018 bytes.
- PDF size: 949,545 bytes.
- PPTX SHA-256: `0BEDB6E077C035893F60E9D5D127C3C4F9A3643779B5FFEBAC82491EC99884A3`.
- PDF SHA-256: `C9F41F718951CD8D19F8132B15618D47140D4509F333005B682BD499D91FF0E9`.

## Validation decision

**Passed.** The PPTX and PDF are visually readable and consistent with the final nine-feature model state, the separate historical-screening output, and the documented operational limitations.
