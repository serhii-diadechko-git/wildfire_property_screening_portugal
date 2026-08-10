# Capstone presentation validation

Validation date: 2026-08-09.

Presentation: `reports/presentation/wildfire_exposure_screening_capstone_final.pptx`

## Outcome

The retained editable capstone deck contains eight 16:9 slides and eight
speaker-note sections. It presents one concise project story:

1. the broad-area wildfire-exposure screening problem and reproducible
   data-science/GIS workflow;
2. the ICNF, CLC/DEM, and ERA5-Land source roles;
3. observed 2016-2025 recurrence, official ICNF structural-hazard context, and
   the separate target-free 2026 comparative estimate;
4. the transparent historical-recurrence benchmark and accepted nine-feature
   the final nine-feature model; and
5. responsible use for narrowing broad location-search areas before local
   investigation.

The deck does not call a model estimate a probability, safety guarantee,
property-level forecast, insurance estimate, or purchase recommendation.

## Slide evidence

| Slide | Verified purpose | Primary repository evidence |
|---:|---|---|
| 1 | Project purpose and the reproducible data science, ML, and GIS workflow | `README.md`; `docs/project_brief.md` |
| 2 | Analytical record and source roles | `docs/data_dictionary.md`; `docs/source_plan.md` |
| 3 | Observed historical recurrence and separate 2026 comparative estimate | historical-screening and operational-validation reports |
| 4 | Historical recurrence and official ICNF structural hazard as complementary context | `qgis/README.md`; historical comparison report |
| 5 | Historical-recurrence benchmark versus the final nine-feature model on the held-out final test | `final_temporal_test_2022_2024.md`; `model_final_decision.md` |
| 6 | Broad-area screening use case | `docs/project_brief.md`; `docs/operational_forecast_cycle.md` |
| 7 | Compare the three evidence layers, then verify locally | `qgis/README.md`; spatial-output registry |
| 8 | Project conclusion and annual refresh/evaluation cycle | `README.md`; `docs/operational_forecast_cycle.md` |

## Numerical and terminology checks

- Canonical grid: 89,112 mainland 1 km cells.
- Historical-screening evidence window: 2016-2025; recurrence is measured in a
  mainland-masked 2 km context.
- Model-development fit years: `T=2010-2019`; validation years: `T=2020-2021`;
  held-out final temporal test: `T=2022-2024` with outcomes 2023-2025.
- Final-test historical-recurrence benchmark: MAE 0.0292, RMSE 0.1106, and
  tie-aware burned-share-mass capture@20% 40.2%.
- Final-test final nine-feature model: MAE 0.0209, RMSE 0.1110, and
  tie-aware burned-share-mass capture@20% 57.2%.
- The 2026 annual output is target-free, derived from 2025 predictor inputs,
  and awaits independent evaluation after ICNF publishes the observed 2026
  outcome.
- The official ICNF structural-hazard layer is a separate 25 m official
  reference summarized to a predominant 1 km class. It is not a model target,
  prediction, or accuracy benchmark.

## Package check

- PPTX package check: 8 slides and 8 speaker-note sections.
- PPTX size: 301,973 bytes.
- PPTX SHA-256: `877A15FD593BB89E33676B680B5A5082DFE307CF19B0ABB15D4700F60792CD7B`.

This report validates presentation content, paths, notes, and terminology.
Render/overflow verification should be rerun after any future manual slide edit.
