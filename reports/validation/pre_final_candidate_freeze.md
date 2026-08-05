# Pre-final candidate freeze

Updated 2026-08-05. This record freezes candidate artefacts after train/validation work only. It does **not** open, score, or otherwise use final-test predictor years T=2022-2024.

## Frozen candidates

| Candidate | Purpose | Training / validation | Feature contract | Current reference artefact |
|---|---|---|---|---|
| Historical recurrence baseline | Simple, interpretable comparator. It maps `fire_years_previous_10y_2km` to the mean `burned_share_next_year` observed for that count in training data only. | Train T=2015-2019; validate T=2020-2021 | `fire_years_previous_10y_2km` only | `data/processed/model_v2_feature_experiments/models/baseline_7/historical_fire_baseline.joblib`; SHA-256 `DE4FD5FF7B3D5A9FCB32ED93342A9F477EE60D0C6C2CABCC7A09D34D8B12C495` |
| Nine-feature hurdle regressor | Primary continuous burned-share candidate. Its output is an expected burned share, not a probability or a buyer-facing threshold. | Train T=2015-2019; validate T=2020-2021 | The seven canonical predictors plus `warm_season_max_monthly_2m_temperature_c` and `warm_season_min_monthly_soil_water_layer1` | `data/processed/model_v2_feature_experiments/models/climate_extremes_9/hurdle_hist_gradient_regressor.joblib`; SHA-256 `3E4C46D3397905D29F986238BE956C43289EE4061F97299F6F9F39C24AC0049A` |

The nine-feature artefact was refitted with the fixed project seed and produced identical validation predictions; its saved-model reload also produced identical predictions. The machine-readable validation evidence is `data/processed/model_v2_feature_experiments/isolated_climate_pair_validation.json` (SHA-256 `50981C3D18DCF09615DB745EA44FEBBF25244BFCEF9A592F440D18B57D0E4A04`).

## Interpretation of the freeze

The nine-feature model had lower combined validation MAE and higher burned-share-mass capture than the seven-feature hurdle model, but its MAE was weaker in 2021 than in 2020. This is recorded as a stability limitation, not a reason to alter the fitted artefact or tune on validation data. No further feature search or hyperparameter search is authorised by this freeze.

This freezes the candidate definitions, predictor order, hyperparameters, and seed. It does **not** prohibit a controlled refit if earlier training years are added: each candidate must then be refit on the expanded training years only, revalidated on the still-reserved validation years, and fingerprinted in a new freeze record. The existing artefacts remain preserved reference versions.

The final temporal test remains reserved. Any future final-test protocol must evaluate the subsequently frozen candidates unchanged and must not use its results to refit, select features, or tune hyperparameters.
