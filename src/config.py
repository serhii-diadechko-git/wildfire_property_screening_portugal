"""Initial project configuration.

The values below are planning assumptions from the approved project documentation.
They may change only after the feasibility pilot and must then be updated consistently.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SpatialConfig:
    analysis_crs: str = "EPSG:3763"
    grid_size_metres: int = 1_000
    context_buffer_metres: int = 2_000


SPATIAL = SpatialConfig()
