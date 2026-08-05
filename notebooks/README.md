# Notebook responsibilities and execution order

Notebooks are thin orchestration and inspection layers. Reusable calculations live in `src/`, executable runners live in `scripts/`, and validated results live in `reports/validation/`.

1. `00_environment_test.ipynb` — environment, import, CRS and output-path checks only.
2. `01_data_collection.ipynb` — immutable source inventory and provenance only; no new collection.
3. `02_data_preparation.ipynb` — preparation and validation evidence for canonical inputs.
4. `03_eda.ipynb` — descriptive EDA and spatial/temporal evidence.
5. `04_modelling.ipynb` — records the fixed train/validation experiment and why no predictive model was selected; it runs no new modelling.
6. `05_evaluation_recommendations.ipynb` — inspects the historical/descriptive exposure screening and official ICNF comparison created by `scripts/build_historical_exposure_screening.py`.
7. `06_final_charts.ipynb` — presentation-ready figures and tables only.

The predictive modelling gate is closed. The final deliverable is a historical wildfire-exposure screening layer for broad location comparison, not a prediction, probability, property-level safety assessment, or purchase recommendation.
