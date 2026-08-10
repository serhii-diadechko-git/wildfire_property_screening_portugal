"""Export the API's live FastAPI schema as a versioned OpenAPI JSON document."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.exposure_api import create_app


def main() -> None:
    path = ROOT / "docs/openapi/exposure_api.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(create_app().openapi(), indent=2) + "\n", encoding="utf-8")
    print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
