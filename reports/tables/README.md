# Generated tables

This directory contains derived CSV summaries used by the GIS and presentation
outputs. It is Git-ignored because the tables are reproducible from the
validated raw inputs and project code. The one-command project runner records
every table it creates in its run summary.

Final-test model diagnostic tables are regenerated from saved frozen
T=2022–2024 predictions/metrics by `scripts/build_model_diagnostics.py`:

- `model_final_test_metrics.csv`
- `model_final_test_metrics_by_year.csv`
- `model_final_test_binned_observed_vs_estimated.csv`

Historical-screening distribution and ICNF comparison tables are regenerated
by `scripts/build_historical_exposure_screening.py` and displayed in
`notebooks/05_evaluation_recommendations.ipynb` and
`notebooks/06_final_charts.ipynb`. Tables are derived evidence, not manually
entered presentation numbers.
