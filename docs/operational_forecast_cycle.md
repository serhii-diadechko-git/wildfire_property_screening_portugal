# Annual operational estimate runbook

This document records the existing 2026 pipeline and the revised pre-year
workflow from the October 2026 review. The legacy scripts remain pinned to
2026; they are not yet a generic annual publisher. For the scientific learning
logic, target formula, model components, and temporal split, first read
[From historical evidence to the 2026 estimate](model_learning_and_2026_estimate.md).

## Operational rule

For forecast year `Y`:

1. Issue at **12:00 UTC on 31 December `Y-1`**, with an input cutoff of
   **23:59:59 UTC on 30 December `Y-1`**. The target is the entire next calendar
   year, 1 January–31 December `Y`.
2. Score predictor year `T=Y-1`: JJAS climate ends in September, and fire history
   covers `Y-11` through `Y-2`. Check actual publication and acquisition dates,
   including revisions, rather than inferring availability from these years.
3. Train only through completed **outcome `Y-2`**, hence predictor year `Y-3`.
   Outcome `Y-1` is not complete at the issue date. If `Y-2` is still unavailable,
   block the model release; do not silently change the evaluated cutoff.
4. Keep `burned_share_next_year` absent from scoring inputs. Refit both model
   stages and any learned preprocessing inside this training boundary; keep
   the nine features and model parameters fixed unless separately developed.
5. Evaluate the saved forecast only after ICNF publishes complete outcome `Y`,
   recording the outcome version. A provisional in-year total is not the target.

This is a rolling data update, not a new model-selection experiment. Changing
features, thresholds, algorithms, or model parameters requires a separately
versioned research and validation cycle.

## Current published cycle

| Item | Current value |
|---|---|
| Forecast year `Y` | 2026 |
| Predictor year `T` | 2025 |
| Historical ICNF window | 2015-2024 |
| Climate input | ERA5-Land JJAS 2025 |
| Operational refit evidence | `T=2010-2024`, observed outcomes 2011-2025 |
| Target in scoring matrix | Absent by design |
| Coverage | 89,112 mainland Portugal 1 km cells |
| Recorded creation | 9 August 2026, during the target year |
| Outcome comparison | Await complete ICNF 2026; it will not prove a pre-year issue |

This existing artifact does not satisfy the new December issue protocol. Its
predictions, model, manifests, maps and presentation remain unchanged.

## Current commands

Run from the repository root after required raw inputs have passed preflight:

```text
python scripts/prepare_operational_forecast.py
python scripts/score_operational_forecast.py
```

The scoring command validates and reuses matching published artifacts rather
than silently overwriting them. The current scripts are intentionally pinned to
the validated 2026 source cutoff. A future annual cycle must first register and
validate its new source years and update the controlled year configuration.

For a complete clean reproduction of all derived project outputs, use the root
workflow documented in the [project README](../README.md):

```text
python scripts/run_project.py --mode reproduce --confirm-rebuild
```

## Current outputs

| Path | Purpose |
|---|---|
| `data/processed/operational_forecasts/forecast_2026_nine_feature_matrix.parquet` | Target-free 2025 predictor matrix. |
| `data/processed/final_model_2010_2024/nine_feature_hurdle.joblib` | Saved operational model; the filename is retained for backward compatibility. |
| `data/processed/final_model_2010_2024/model_metadata.json` | Feature order, evidence cutoff, model version, and checksums. |
| `data/processed/operational_forecasts/forecast_2026_scores.parquet` | Canonical tabular 2026 estimates. |
| `data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg` | QGIS-ready 2026 layer. |
| `data/processed/web_map/estimated_comparative_wildfire_exposure_2026.geojson` | Browser-ready derivative of the spatial output. |
| `qgis/wildfire_exposure_screening_portugal_2026.qgz` | Portable QGIS presentation project. |

These outputs are continuous comparative estimated burned shares. They are not
observed 2026 outcomes, probabilities that whole cells will burn,
property-level assessments, insurance estimates, or purchase recommendations.

## Controlled 2027 update

For a 31 December 2026 issue, register completed **2025** fire outcomes and
**JJAS 2026** climate; train through predictor 2024 / outcome 2025, and score
predictor 2026 for outcome 2027. Do not wait for or train on full-year 2026.
The 2026 estimate is evaluated on a separate schedule when its outcome is
published. That new labelled year first becomes eligible for the next pre-year
cycle under this conservative rule.

Before any 2027 publication, register and validate the new raw inputs and
parameterise the legacy 2026 preparation/scoring code with this issue protocol.
That integration and the 2026 JJAS input have **not** been certified by this
review. Run the new standalone date gate first:

```text
python scripts/check_forecast_availability.py --manifest path/to/issue_inventory.json
```

Use [the inventory template](forecast_issue_inventory.example.json). It
deliberately fails until real evidence is supplied. Include every raw archive,
corrected precipitation file, terrain tile and spatial reference source used.
For each file record source, reference years, complete observation-period end,
version, verified availability timestamp, acquisition timestamp, official
release/evidence URL, local path and SHA-256. An archived first-seen receipt can
establish availability by a date; a filesystem modification time cannot.
The checker validates dates, required source groups/years, file existence and
hashes. A human must check the provider evidence and inventory completeness;
then run the existing geometry, variables, units, coverage and feature tests.
It is a standalone gate, not yet wired into automatic publication.

Save each proposed issue in a new directory named with year, issue timestamp
and model version. Archive the exact input inventory, fit parameters, training
years, environment, code commit, baseline scores, model checksum and predictions
before viewing outcomes. Never overwrite an issued forecast. Corrections get
a new revision and an explanation; evaluate the originally issued version as
well. Late issues must be labelled as estimates made during the target year.

## Monitoring and fallback

The decision is broad mainland-area comparison for further local research.
An annual top-20% shortlist is a diagnostic fixed search budget, not a safety
threshold or a measure of economic value. Compare it with recurrence, observed
history and the separate official structural-hazard layer. Do not interpret a
low rank as safe.

Before issue, block missing cells, changed CRS/denominators, unexpected feature
order/ranges, missing source releases and any target in the score table. Record
feature distributions and shifts against training years. Review large climate
shifts and stale CLC coverage; do not repair them by fitting to future data.

After a completed outcome arrives, report annual and cumulative MAE/RMSE,
positive-cell errors, zero share, tie-aware mass/positive capture and
predicted/observed mean (also area-weighted totals). Predeclare review triggers:

- Prediction/observed annual burned total below **0.5**: severe underprediction
  review; stop using estimated quantities for resource planning.
- Mass capture no better than recurrence in **two consecutive completed years**:
  suspend ML-led prioritisation pending review; keep recurrence as the comparator.
- Material source-definition, grid, land-cover or climate distribution change:
  revalidate the full chain before another issue.

These are proposed operational review triggers, not fitted or validated risk
thresholds. The retrospective severe years already fail the quantity trigger;
therefore precise annual quantities are not endorsed today. Do not wait for
two years when an input or publication check fails.

If ML adds no dependable ranking value, present the separately labelled,
availability-checked historical recurrence evidence and official hazard context.
The recurrence regressor can remain a transparent annual comparator only if
its own training labels and fire-history inputs pass their date/quality checks.
Do not treat a failed climate gate as evidence of low exposure. If fire history
or labels are unavailable, publish no new predictive score and clearly date any
older descriptive map. For national totals the training-period mean is the
simplest reference supported by this review; no safety guarantee follows.

Future model changes require selection on earlier inner temporal folds and
locked specifications before a new evaluation period. Outcomes 2011–2025 have
been reused and cannot become untouched again. See the
[full reliability review](forecast_reliability_review.md).

## Fail-closed safeguards

The operational code must stop rather than publish when:

- a required predictor-year source is missing or fails validation;
- an observed target appears in the target-free scoring matrix;
- the feature names or order differ from saved model metadata;
- the model evidence cutoff is later than the newest observed outcome;
- required cell coverage, uniqueness, ranges, or climate assignments fail; or
- an existing artifact does not match its recorded configuration and checksum.

After an intentional annual update, run the focused checks:

```text
python -m unittest tests.test_operational_forecast tests.test_era5_land_validation -v
python scripts/run_project.py --mode validate
```

Notebooks are review and presentation layers, not the annual scoring engine.
Their roles and execution order are documented in
[notebooks/README.md](../notebooks/README.md).
