"""Focused contract tests for the historical/descriptive screening output."""

import hashlib
import json
from pathlib import Path
import unittest

import pyogrio

from src.historical_exposure_screening import (
    BAND_ORDER,
    FORBIDDEN_OUTPUT_FIELDS,
    METRICS_PATH,
    OUTPUT_LAYER,
    OUTPUT_PATH,
)
from src.source_registry import ICNF_STRUCTURAL_HAZARD_2020_2030


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


class HistoricalExposureScreeningTests(unittest.TestCase):
    def test_official_hazard_raw_source_is_immutable_and_registered(self) -> None:
        """The GeoTIFF is the reproducible raw input; metadata sidecars are optional evidence."""
        record = ICNF_STRUCTURAL_HAZARD_2020_2030
        path = ROOT / record.raw_path
        self.assertEqual(path.stat().st_size, record.size_bytes)
        self.assertEqual(sha256(path), record.sha256)
        self.assertEqual(record.crs, "EPSG:3763")
        self.assertEqual(record.resolution_metres, 25.0)

    def test_output_is_complete_spatial_and_non_predictive(self) -> None:
        info = pyogrio.read_info(OUTPUT_PATH, layer=OUTPUT_LAYER)
        self.assertEqual(info["features"], 89_112)
        self.assertEqual(str(info["crs"]), "EPSG:3763")
        self.assertEqual(info["geometry_type"], "Polygon")
        fields = set(info["fields"])
        self.assertFalse(fields.intersection(FORBIDDEN_OUTPUT_FIELDS))
        self.assertIn("fire_years_history_10y_2km", fields)
        self.assertIn("official_icnf_hazard_class", fields)

    def test_report_records_window_thresholds_and_exact_rerun(self) -> None:
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(metrics["evidence_snapshot"]["history_years"], list(range(2016, 2026)))
        self.assertEqual(metrics["thresholds"]["lower_max"], 1)
        self.assertEqual(metrics["thresholds"]["moderate_max"], 3)
        self.assertEqual(
            [item["historical_exposure_band"] for item in metrics["band_summary"]],
            list(BAND_ORDER),
        )
        self.assertEqual(sum(item["cell_count"] for item in metrics["band_summary"]), 89_112)
        self.assertTrue(metrics["deterministic_rerun"]["all_275_batches_recomputed_without_writes"])
        self.assertTrue(metrics["deterministic_rerun"]["analytical_values_exact"])
        self.assertTrue(metrics["no_predictive_claim"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
