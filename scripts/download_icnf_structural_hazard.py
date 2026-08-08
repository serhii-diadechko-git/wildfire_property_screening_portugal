"""Acquire the one official ICNF structural-hazard WCS coverage, without overwrite."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.source_registry import ICNF_STRUCTURAL_HAZARD_2020_2030


RECORD = ICNF_STRUCTURAL_HAZARD_2020_2030


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Perform the official WCS retrieval")
    args = parser.parse_args()
    request = {
        "service": "WCS", "request": "GetCoverage", "version": "1.0.0",
        "coverage": RECORD.wcs_coverage_id, "crs": RECORD.crs, "response_crs": RECORD.crs,
        "bbox": ",".join(str(value) for value in RECORD.bounds),
        "width": str(RECORD.dimensions[0]), "height": str(RECORD.dimensions[1]),
        "format": "GeoTIFF",
    }
    target = ROOT / RECORD.raw_path
    if not args.download:
        print({"url": RECORD.service_url, "request": request, "target": str(target)})
        return
    if target.exists():
        digest = hashlib.sha256(target.read_bytes()).hexdigest().upper()
        if digest != RECORD.sha256:
            raise ValueError(f"Existing raw file checksum differs from registry: {digest}")
        print({"status": "already_present_validated", "path": str(target), "bytes": target.stat().st_size, "sha256": digest})
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(RECORD.service_url, params=request, stream=True, timeout=600)
    response.raise_for_status()
    if "xml" in response.headers.get("content-type", "").lower():
        raise ValueError("WCS returned XML instead of the GeoTIFF coverage")
    with target.open("xb") as handle:
        for chunk in response.iter_content(1024 * 1024):
            if chunk:
                handle.write(chunk)
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    checksum = digest.hexdigest().upper()
    if checksum != RECORD.sha256:
        raise ValueError(f"Downloaded checksum differs from registered source: {checksum}")
    print({"path": str(target), "bytes": target.stat().st_size, "sha256": checksum})


if __name__ == "__main__":
    main()
