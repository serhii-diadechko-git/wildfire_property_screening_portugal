"""Compatibility import for historical baseline joblib artefacts.

The original seven-feature selection workflow was retired. Historical serialized
baseline models still reference this module path, so the estimator remains
available without preserving the superseded training implementation.
"""

from src.modeling import HistoricalFireMeanRegressor

__all__ = ["HistoricalFireMeanRegressor"]
