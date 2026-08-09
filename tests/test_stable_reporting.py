"""Checks that tracked validation evidence stays stable across identical runs."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
import sys
import unittest

from src.project_run import RunStage, _run_stage
from src.reporting import write_json_if_changed, write_text_if_changed


ROOT = Path(__file__).resolve().parents[1]


class StableReportingTests(unittest.TestCase):
    def test_helpers_publish_once_then_preserve_identical_evidence(self) -> None:
        path = ROOT / "reports" / "run_logs" / ".test_stable_reporting_evidence.json"
        try:
            self.assertTrue(write_json_if_changed(path, {"row_count": 89_112}))
            first_content = path.read_text(encoding="utf-8")
            self.assertFalse(write_json_if_changed(path, {"row_count": 89_112}))
            self.assertEqual(path.read_text(encoding="utf-8"), first_content)
            self.assertTrue(write_text_if_changed(path, "changed\n"))
        finally:
            path.unlink(missing_ok=True)

    def test_run_stage_records_volatile_duration_in_the_ignored_run_log(self) -> None:
        log = StringIO()
        stage = RunStage("test stage", (sys.executable, "-c", "print('stable evidence')"), "test")
        result = _run_stage(stage, log)
        self.assertEqual(result["return_code"], 0)
        self.assertGreaterEqual(result["elapsed_seconds"], 0)
        self.assertIn("stable evidence", log.getvalue())

    def test_tracked_validation_reports_exclude_run_specific_metadata(self) -> None:
        for name in (
            "era5_coastal_fallback_analysis.json",
            "national_panel_model_readiness_eda.json",
            "historical_exposure_screening_and_icnf_comparison.json",
        ):
            payload = json.loads((ROOT / "reports" / "validation" / name).read_text(encoding="utf-8"))
            self.assertNotIn("created_utc", payload, name)
        national_report = (ROOT / "reports" / "validation" / "national_panel_2015_2024_validation.md").read_text(encoding="utf-8")
        self.assertIn("Git-ignored `reports/run_logs/`", national_report)
        self.assertNotIn("## Component duration evidence", national_report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
