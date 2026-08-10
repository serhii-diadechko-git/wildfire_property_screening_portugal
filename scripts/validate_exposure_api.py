"""Validate the local API against the actual published 2026 spatial outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.exposure_api import GRID_TO_WGS84, ExposureStore, create_app


def main() -> None:
    store = ExposureStore.from_project_root()
    representative = store.cells.iloc[len(store.cells) // 2].geometry.representative_point()
    longitude, latitude = GRID_TO_WGS84.transform(representative.x, representative.y)
    client = TestClient(create_app(store=store))
    health = client.get("/health")
    lookup = client.get("/v1/exposure", params={"longitude": longitude, "latitude": latitude})
    schema = client.get("/openapi.json")
    if health.status_code != 200 or lookup.status_code != 200 or schema.status_code != 200:
        raise RuntimeError(f"API validation failed: health={health.status_code}, lookup={lookup.status_code}, schema={schema.status_code}")
    payload = lookup.json()
    if len(payload["context_buffers"]) != 3 or payload["containing_cell"]["forecast_year"] != 2026:
        raise RuntimeError("API response breaks the published 2026 lookup contract")
    print(json.dumps({
        "status": "passed",
        "cell_id": payload["containing_cell"]["cell_id"],
        "forecast_year": payload["containing_cell"]["forecast_year"],
        "context_buffers_km": [item["radius_km"] for item in payload["context_buffers"]],
        "openapi_paths": sorted(schema.json()["paths"]),
    }, indent=2))


if __name__ == "__main__":
    main()
