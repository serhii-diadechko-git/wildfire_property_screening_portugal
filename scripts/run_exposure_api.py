"""Start the local read-only exposure API from the repository root."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.exposure_api import app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Portugal wildfire-exposure lookup API.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address; default keeps the service local.")
    parser.add_argument("--port", type=int, default=8000, help="TCP port; default: 8000.")
    arguments = parser.parse_args()
    uvicorn.run(app, host=arguments.host, port=arguments.port, reload=False)


if __name__ == "__main__":
    main()
