"""Focused checks for the non-predictive QGIS presentation deliverables."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
import unittest

import pandas as pd

from src.final_visuals import FIGURE_PATHS, QGIS_FIGURE_PATHS, validate_final_visuals


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "qgis" / "wildfire_exposure_screening_portugal.qgz"
OPERATIONAL_PROJECT_PATH = ROOT / "qgis" / "wildfire_exposure_screening_portugal_2026.qgz"
SCREENING_METRICS_PATH = ROOT / "reports" / "validation" / "historical_exposure_screening_and_icnf_comparison.json"
CROSSTAB_PATH = ROOT / "reports" / "tables" / "historical_exposure_band_by_icnf_hazard_class.csv"
NOTEBOOK_PATHS = [
    ROOT / "notebooks" / "05_evaluation_recommendations.ipynb",
    ROOT / "notebooks" / "06_final_charts.ipynb",
]


class PresentationOutputTests(unittest.TestCase):
    def test_final_figures_use_validated_non_predictive_evidence(self) -> None:
        metrics = json.loads(SCREENING_METRICS_PATH.read_text(encoding="utf-8"))
        self.assertTrue(metrics["no_predictive_claim"])
        cross = pd.read_csv(CROSSTAB_PATH)
        self.assertEqual(int(cross.cell_count.sum()), 89_112)
        for path in FIGURE_PATHS.values():
            self.assertTrue(path.exists(), path)
            self.assertGreater(path.stat().st_size, 5_000)

    def test_qgis_layout_exports_validate_when_present(self) -> None:
        """Layout PNGs are optional because normal reproduction does not require PyQGIS."""
        if not all(path.exists() for path in QGIS_FIGURE_PATHS.values()):
            self.skipTest("Run reproduce with --with-qgis to validate optional QGIS layout exports")
        result = validate_final_visuals()
        self.assertEqual(result["figure_count"], 6)
        self.assertEqual(result["history_window"], "2016-2025")
        self.assertEqual(result["canonical_cell_count"], 89_112)
        self.assertFalse(result["images_rewritten"])
        self.assertTrue(all(item["status"] == "verified_existing" for item in result["figures"].values()))

    def test_qgis_project_contains_required_relative_layer_paths_and_layouts(self) -> None:
        self.assertTrue(PROJECT_PATH.exists())
        with zipfile.ZipFile(PROJECT_PATH) as archive:
            project_member = next(name for name in archive.namelist() if name.endswith(".qgs"))
            project_xml = archive.read(project_member).decode("utf-8")
        for text in (
            "01 Historical exposure screening",
            "02 Official ICNF comparison",
            "03 Context",
            "04 QA reference",
            "Historical Wildfire Exposure Screening",
            "Historical Exposure and Official ICNF Structural Hazard",
            "../data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg",
            "../data/processed/reference/mainland_boundary_caop2025.gpkg",
            "Cell ID",
        ):
            self.assertIn(text, project_xml)

    def test_operational_qgis_project_adds_the_separate_2026_layer_by_relative_path(self) -> None:
        self.assertTrue(OPERATIONAL_PROJECT_PATH.exists())
        with zipfile.ZipFile(OPERATIONAL_PROJECT_PATH) as archive:
            project_member = next(name for name in archive.namelist() if name.endswith(".qgs"))
            project_xml = archive.read(project_member).decode("utf-8")
        for text in (
            "00 Annual comparative estimate",
            "2026 estimated comparative wildfire exposure",
            "../data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg",
            "predicted_burned_share_next_year",
            "Comparative 1 km screening estimate only",
        ):
            self.assertIn(text, project_xml)
        self.assertNotIn("C:/Personal/", project_xml)
        self.assertNotIn("C:\\Personal\\", project_xml)

    def test_consolidated_notebooks_link_real_presentation_outputs(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in NOTEBOOK_PATHS)
        for text in (
            "1 km mainland grid cells with fire recurrence measured in a 2 km context",
            "data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg",
            "qgis/wildfire_exposure_screening_portugal.qgz",
            "reports/validation/historical_exposure_screening_and_icnf_comparison.md",
            "validate_final_visuals",
        ):
            self.assertIn(text, combined)

    def test_notebooks_do_not_embed_absolute_personal_paths(self) -> None:
        for path in (ROOT / "notebooks").glob("*.ipynb"):
            content = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("c:\\\\personal\\\\", content, path)
            self.assertNotIn("c:/personal/", content, path)
