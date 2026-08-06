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
