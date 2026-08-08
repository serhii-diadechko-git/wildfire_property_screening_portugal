"""Create/reuse the CAOP boundary, municipalities, and canonical 1 km grid."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.reference_preparation import (  # noqa: E402
    prepare_caop_reference_layers,
    prepare_canonical_mainland_grid,
)


if __name__ == "__main__":
    print(json.dumps({
        "caop_references": prepare_caop_reference_layers(),
        "canonical_grid": prepare_canonical_mainland_grid(),
    }, indent=2))
