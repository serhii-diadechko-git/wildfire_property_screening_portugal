"""Fit the fixed nine-feature specification for future reproducible use.

The model specification was frozen before final testing. This post-test refit
uses only the development period T=2010-2021; it never incorporates the held-out
T=2022-2024 rows.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from src.extended_model_refit import FEATURE_MATRIX_PATH, NINE_FEATURES, RANDOM_SEED, ROOT
from src.feature_contract import TARGET_COLUMN
from src.model_v2_experiments import HurdleHistGradientRegressor


OUTPUT_DIR = ROOT / "data/processed/final_fixed_spec_model_2010_2021"
MODEL_PATH = OUTPUT_DIR / "nine_feature_hurdle.joblib"
METADATA_PATH = OUTPUT_DIR / "model_metadata.json"
DEVELOPMENT_YEARS = tuple(range(2010, 2022))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def refit() -> dict[str, object]:
    frame = pd.read_parquet(FEATURE_MATRIX_PATH)
    if tuple(sorted(int(value) for value in frame.observation_year.unique())) != DEVELOPMENT_YEARS:
        raise ValueError("Final fixed-specification refit requires exactly T=2010-2021")
    if frame[list(NINE_FEATURES) + [TARGET_COLUMN]].isna().any().any():
        raise ValueError("Development feature matrix contains missing values")
    model = HurdleHistGradientRegressor()
    with threadpool_limits(limits=1, user_api="openmp"):
        model.fit(frame.loc[:, NINE_FEATURES], frame[TARGET_COLUMN])
    sample = frame.loc[:999, NINE_FEATURES]
    expected = model.predict(sample)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporary_model = MODEL_PATH.with_suffix(".joblib.tmp")
    if temporary_model.exists():
        raise FileExistsError(f"Stale temporary model output requires inspection: {temporary_model}")
    payload = {
        "model": model,
        "model_name": "nine_feature_hurdle",
        "feature_order": list(NINE_FEATURES),
        "training_years": list(DEVELOPMENT_YEARS),
        "target": TARGET_COLUMN,
        "random_seed": RANDOM_SEED,
        "selection_evidence": "reports/validation/final_temporal_test_2022_2024.md",
        "held_out_final_test_years_excluded_from_refit": [2022, 2023, 2024],
        "output_interpretation": "continuous expected burned share; not a probability or recommendation",
    }
    joblib.dump(payload, temporary_model)
    os.replace(temporary_model, MODEL_PATH)
    reloaded = joblib.load(MODEL_PATH)["model"].predict(sample)
    if not np.array_equal(expected, reloaded):
        raise ValueError("Reloaded fixed-specification model changes predictions")
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model_path": MODEL_PATH.relative_to(ROOT).as_posix(),
        "model_sha256": _sha256(MODEL_PATH),
        "row_count": len(frame),
        "training_years": list(DEVELOPMENT_YEARS),
        "final_test_years_excluded": [2022, 2023, 2024],
        "feature_order": list(NINE_FEATURES),
        "target": TARGET_COLUMN,
        "reload_sample_predictions_identical": True,
    }
    temporary_metadata = METADATA_PATH.with_suffix(".json.tmp")
    temporary_metadata.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    os.replace(temporary_metadata, METADATA_PATH)
    return metadata
