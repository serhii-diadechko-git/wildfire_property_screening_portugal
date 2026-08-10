"""Build the T=2022-2024 labelled matrix for post-selection operational refitting.

This deliberately copies validated T=2022-2024 feature/label rows without
fitting, scoring, comparing, or selecting a model. It is separate from the
archived v1 final-test script so a clean rebuild does not present those older
results as evaluation evidence for the final nine-feature model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.extended_final_test import build_final_feature_matrix


if __name__ == "__main__":
    print(json.dumps(build_final_feature_matrix(), indent=2))
