"""Focused checks for the non-predictive QGIS presentation deliverables."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
import unittest

import pandas as pd

from src.final_visuals import FIGURE_PATHS


ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = ROOT / "qgis" / "wildfire_exposure_screening_portugal.qgz"
SCREENING_METRICS_PATH = ROOT / "reports" / "validation" / "historical_exposure_screening_and_icnf_comparison.json"
CROSSTAB_PATH = ROOT / "reports" / "tables" / "historical_exposure_band_by_icnf_hazard_class.csv"
QGIS_MAPS = [
    ROOT / "reports" / "figures" / "historical_wildfire_exposure_screening_mainland_portugal.png",
    ROOT / "reports" / "figures" / "historical_exposure_and_official_icnf_structural_hazard_comparison.png",
]


class PresentationOutputTests(unittest.TestCase):
    def test_final_figures_use_validated_non_predictive_evidence(self) -> None:
        metrics = json.loads(SCREENING_METRICS_PATH.read_text(encoding="utf-8"))
        self.assertTrue(metrics["no_predictive_claim"])
        cross = pd.read_csv(CROSSTAB_PATH)
        self.assertEqual(int(cross.cell_count.sum()), 89_112)
        for path in [*FIGURE_PATHS.values(), *QGIS_MAPS]:
            self.assertTrue(path.exists(), path)
            self.assertGreater(path.stat().st_size, 5_000)

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
