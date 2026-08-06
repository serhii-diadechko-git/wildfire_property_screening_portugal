"""Compatibility import for the retained historical-baseline artefact.

Earlier serialized artefacts reference this module path.  Keep this small
import shim so those reproducible artefacts can still be loaded without
duplicating a second training implementation.
"""

from src.modeling import HistoricalFireMeanRegressor

__all__ = ["HistoricalFireMeanRegressor"]
