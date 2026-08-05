# Capstone presentation validation

Validation date: 2026-08-05  
Author: Serhii Diadechko  
Presentation: `reports/presentation/wildfire_exposure_screening_capstone_presentation.pptx`  
PDF export: `reports/presentation/wildfire_exposure_screening_capstone_presentation.pdf`

## Outcome

The 13-slide, 16:9 capstone presentation was created from validated repository artefacts. Its central conclusion is unchanged: the tested next-year regressions did not pass the predeclared validation gate, so no predictive model was accepted; the final deliverable is a reproducible historical comparative screening layer based directly on observed ICNF burned-area recurrence for 2016–2025.

The presentation consistently describes **1 km mainland grid cells with fire recurrence measured in a 2 km context**. It does not present lower exposure as safety, call regression output a probability, rank the safest places, or make a property purchase recommendation.

## Slide outline and sources

| Slide | Purpose | Repository sources recorded in speaker notes |
|---:|---|---|
| 1 | Title and evidence-led project conclusion | `README.md`; `reports/validation/train_validation_model_selection.md`; `reports/validation/historical_exposure_screening_and_icnf_comparison.md`; capstone kickoff workbook |
| 2 | Decision problem, national scope and scope boundary | `README.md`; historical screening/comparison report; spatial-output registry |
| 3 | Why mainland Portugal was analysed nationally | `README.md`; national-panel validation report; spatial-output registry |
| 4 | Reproducible workflow and separation of evidence roles | data dictionary; canonical readiness report; model-selection report; historical screening/comparison report |
| 5 | Zero-heavy target and complementary model metrics | national-panel EDA; model-selection report; success criteria |
| 6 | Validation-only comparison and rejection of both candidates | validated baseline/model figure; model-selection Markdown and JSON reports |
| 7 | Fictional buyer workflow demonstrating appropriate use | historical screening/comparison report; QGIS README; fictional explanatory example explicitly labelled as such |
| 8 | Final observed historical-exposure screening map and bands | validated national map; historical screening/comparison report; ICNF annual burned-area cartography, 2016–2025 |
| 9 | National band distribution | validated summary-table figure; band-summary CSV; historical screening/comparison report |
| 10 | Historical exposure versus official ICNF structural hazard | validated comparison map; historical screening/comparison report; ICNF SRUP structural hazard 2020–2030 |
| 11 | Descriptive cross-tab, correspondence and disagreement | validated cross-tab figure; cross-tab CSV; historical screening/comparison report |
| 12 | Evidence-to-use contract, limitations and deliverables | validated decision/limitations figure; spatial-output registry; QGIS validation report; QGIS project; `README.md` |
| 13 | Likely assessor questions and concise evidence-backed answers | model-selection report; historical screening/comparison report; spatial-output registry; success criteria |

## Speaker-note validation

- Speaker notes are present on all 13 slides.
- Every note includes a key takeaway and a `[Sources]` section.
- Notes contain at least 132 words per slide, supporting an approximately 45–75 second spoken explanation depending on delivery pace.
- Methodological nuance and likely assessor Q&A are included where relevant.
- No absolute personal filesystem path appears in visible slide text or speaker notes.

## Numerical and terminology checks

The deck was programmatically checked for the following validated values:

- national grid: 89,112 cells;
- evidence window: 2016–2025;
- exposure distribution: 36,645 lower (41.12%), 29,919 moderate (33.57%), 22,548 higher (25.30%);
- Capture@20%: historical recurrence 55.88%, Random Forest 28.62%, Tweedie 49.46%;
- broad descriptive correspondence: 43.59%;
- selected cross-tab counts: 6,794, 14,014, 3,805 and 2,375 cells.

The validation also confirmed that the deck preserves these distinctions:

- historical exposure is observed comparative evidence, not a forecast;
- ICNF structural hazard is an independent official comparison layer, not a model target or accuracy benchmark;
- 1 km is the sole analytical grid resolution;
- 2 km is an outward recurrence context, not a second grid;
- no predictive model advanced to final testing.

## Rendering and packaging QA

- Artifact-tool PowerPoint generation completed with 13 slides.
- All 13 PowerPoint slide renders were inspected individually; clipping found during draft review was corrected before packaging.
- The official slide-overflow test passed: `Test passed. No overflow detected.`
- Microsoft PowerPoint opened the deck and exported the PDF successfully.
- The PDF contains 13 pages; all 13 pages were rasterised and visually inspected.
- PPTX size: 2,267,140 bytes.
- PDF size: 964,722 bytes.
- PPTX SHA-256: `12F2B493ADB13C0DE6E2476BC6D7F66E5FEDDAD5FB00BD90DFD0F5A74B1AB429`.
- PDF SHA-256: `7B886B80B27B13F3221A287677DBA680E1F27F875F5FB27D28BEA5F667B488B6`.

## Validation decision

**Passed.** The PPTX and PDF are complete, visually readable, numerically consistent with validated project artefacts, and appropriately limited to historical comparative wildfire-exposure screening.
