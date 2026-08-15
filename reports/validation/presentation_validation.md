# Capstone presentation validation

Validation date: 2026-08-15.

Presentation: `reports/presentation/wildfire_exposure_screening_capstone_final.pptx`

## Outcome

The retained editable capstone deck contains nine 16:9 slides and nine
speaker-note sections. It presents one concise project story:

1. the broad-area wildfire-exposure screening problem and reproducible
   data-science/GIS workflow;
2. the ICNF, CLC/DEM, and ERA5-Land source roles;
3. the time-ordered model-development flow: preparation, training,
   validation, final temporal evaluation, refit, and target-free 2026 estimate;
4. observed 2016-2025 recurrence, official ICNF structural-hazard context, and
   the separate target-free 2026 comparative estimate;
5. the transparent historical-recurrence benchmark and final nine-feature
   model; and
6. responsible use for narrowing broad location-search areas before local
   investigation.

The deck does not call a model estimate a probability, safety guarantee,
property-level forecast, insurance estimate, or purchase recommendation.

## Slide evidence

| Slide | Verified purpose | Primary repository evidence |
|---:|---|---|
| 1 | Project purpose and the reproducible data science, ML, and GIS workflow | `README.md`; `docs/project_brief.md` |
| 2 | Analytical record and source roles | `docs/data_dictionary.md`; `docs/source_plan.md` |
| 3 | Historical preparation, training, validation, final temporal evaluation, refit, and 2026-estimate flow | `docs/data_dictionary.md`; `docs/model_learning_and_2026_estimate.md`; `docs/operational_forecast_cycle.md` |
| 4 | Observed historical recurrence and separate 2026 comparative estimate | historical-screening and operational-validation reports |
| 5 | Historical recurrence and official ICNF structural hazard as complementary context | `qgis/README.md`; historical comparison report |
| 6 | Historical-recurrence benchmark versus the final nine-feature model in the final temporal evaluation | `final_temporal_test_2022_2024.md`; `model_final_decision.md` |
| 7 | Broad-area screening use case | `docs/project_brief.md`; `docs/operational_forecast_cycle.md` |
| 8 | Compare the three evidence layers, then verify locally | `qgis/README.md`; spatial-output registry |
| 9 | Project conclusion and annual refresh/evaluation cycle | `README.md`; `docs/operational_forecast_cycle.md` |

## Numerical and terminology checks

- Canonical grid: 89,112 mainland 1 km cells.
- Registered ICNF source coverage: 2000-2025. This is archive coverage, not one
  model-fitting or evaluation period.
- Historical-screening evidence window: 2016-2025. This is separate descriptive
  evidence; recurrence is measured in a mainland-masked 2 km context.

| Model stage | Predictor years `T` | Observed outcomes `T+1` |
|---|---:|---:|
| Development fitting | 2010-2019 | 2011-2020 |
| Development validation | 2020-2021 | 2021-2022 |
| Final temporal evaluation | 2022-2024 | 2023-2025 |
| Operational refit | 2010-2024 | 2011-2025 |
| Current annual estimate | 2025 | 2026 outcome pending |

- Final-evaluation historical-recurrence benchmark: MAE 0.0292, RMSE 0.1106, and
  tie-aware burned-share-mass capture@20% 40.2%.
- Final-evaluation nine-feature model: MAE 0.0209, RMSE 0.1110, and
  tie-aware burned-share-mass capture@20% 57.2%.
- The 2026 annual output is target-free, derived from 2025 predictor inputs,
  and awaits independent evaluation after ICNF publishes the observed 2026
  outcome.
- The official ICNF structural-hazard layer is a separate 25 m official
  reference summarized to a predominant 1 km class. It is not a model target,
  prediction, or accuracy benchmark.

## Package check

- PPTX package check: 9 slides and 9 speaker-note sections.
- PPTX size: 290,799 bytes.
- PPTX SHA-256: `4D196BB4190B0950223D0F78A995A483886ECD1C920BC54F0B57D6596FE94EA1`.
- Render and overflow check: passed for all nine slides.
- Template-fidelity check: passed; the temporal wording update preserves the
  existing slide geometry and layout.

This report validates presentation content, paths, notes, and terminology.
Render/overflow verification should be rerun after any future manual slide edit.
