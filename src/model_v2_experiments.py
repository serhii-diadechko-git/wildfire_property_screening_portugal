"""Backward-compatibility import for previously serialized hurdle models.

Historical joblib artefacts recorded this module path.  Keep the symbol available
so those immutable artefacts can be loaded, while all maintained code imports the
estimator from :mod:`src.modeling`.
"""

from src.modeling import HurdleHistGradientRegressor

__all__ = ["HurdleHistGradientRegressor"]
