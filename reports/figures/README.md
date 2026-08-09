# Generated figures

This directory is intentionally Git-ignored because maps and charts are
derived outputs. Run `python scripts/run_project.py --mode reproduce
--confirm-rebuild` after placing validated raw inputs in `data/raw/` to create
the current figures. The project validates their stable names and provenance.

Model-evaluation visuals are regenerated from the frozen final temporal test by
`python scripts/build_model_diagnostics.py` (or by the full project runner):

- `model_final_test_metric_comparison.png`
- `model_final_test_observed_vs_estimated.png`
- `model_final_test_binned_observed_vs_estimated.png`

They are regression diagnostics, not probability-calibration or property-risk
maps.

The same run also creates:

- panel EDA charts for target sparsity, predictor distributions, correlations,
  and temporal drift;
- historical-exposure and official ICNF comparison maps/charts;
- the target-free 2026 comparative-estimate map; and
- final decision/limitations and summary-table visuals.

`notebooks/06_final_charts.ipynb` renders the same diagnostics live from
validated artefacts without overwriting exported PNGs. It is the final visual
narrative; the PNG files are durable presentation artefacts rather than
independent calculations. Use `python scripts/build_final_visuals.py` or the
full project runner to regenerate files deliberately.
