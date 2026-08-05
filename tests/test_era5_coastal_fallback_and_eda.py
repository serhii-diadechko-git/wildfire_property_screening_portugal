"""Tests for the accepted climate fallback, GIS outputs and EDA gate."""

import json
import unittest

import pyogrio

from src.config import ERA5_LAND
from src.era5_coastal_fallback import (
    ANALYSIS_JSON_PATH,
    QA_GPKG_PATH,
    QA_LAYER,
    SNAPSHOT_GPKG_PATH,
    SNAPSHOT_LAYER,
    validate_fallback_panel,
)
from src.panel_eda import EDA_JSON_PATH


class Era5CoastalFallbackAndEdaTests(unittest.TestCase):
    def test_fallback_distance_and_source_extent_gate(self) -> None:
        metrics = json.loads(ANALYSIS_JSON_PATH.read_text(encoding="utf-8"))
        self.assertEqual(metrics["affected_cell_count"], 1_506)
        self.assertTrue(metrics["source_extent"]["mask_invariant_across_2015_2024"])
        self.assertEqual(metrics["selected_source_on_request_boundary_count"], 0)
        self.assertFalse(metrics["new_acquisition_required"])
        self.assertLess(metrics["distance_km"]["maximum"], 20.0)
        self.assertTrue(metrics["all_selected_sources_valid_across_years_and_variables"])

    def test_canonical_assignment_method_records_the_fallback(self) -> None:
        self.assertEqual(
            ERA5_LAND.assignment_method,
            "containing_valid_era5_land_cell_else_nearest_valid_land_cell",
        )

    def test_fallback_preserves_panel_contract(self) -> None:
        result = validate_fallback_panel()
        self.assertEqual(result["row_count"], 891_120)
        self.assertEqual(result["updated_climate_row_count"], 15_060)
        self.assertEqual(result["climate_missing_count_after"], 0)
        self.assertTrue(result["all_non_climate_values_exact"])
        self.assertTrue(result["all_unaffected_climate_values_exact"])

    def test_gis_outputs_are_qgis_ready(self) -> None:
        qa_info = pyogrio.read_info(QA_GPKG_PATH, layer=QA_LAYER)
        snapshot_info = pyogrio.read_info(SNAPSHOT_GPKG_PATH, layer=SNAPSHOT_LAYER)
        self.assertEqual(qa_info["features"], 1_506)
        self.assertEqual(snapshot_info["features"], 89_112)
        self.assertIn("3763", qa_info["crs"])
        self.assertIn("3763", snapshot_info["crs"])

    def test_eda_gate_and_no_missing_predictors(self) -> None:
        metrics = json.loads(EDA_JSON_PATH.read_text(encoding="utf-8"))
        self.assertEqual(metrics["row_count"], 891_120)
        self.assertTrue(all(value == 0 for value in metrics["missingness"].values()))
        self.assertGreater(metrics["target"]["overall_zero_proportion"], 0.9)
        self.assertEqual(metrics["model_design_decision"]["gate"], "Model-design gate passed — modelling may begin")
        self.assertTrue(metrics["model_design_decision"]["binary_target_still_deferred"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
