"""Guardrails for the reusable, explanatory notebook layer."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def code_sources(notebook_name: str) -> str:
    """Return all executable source from one notebook without executing it."""

    notebook = json.loads((PROJECT_ROOT / "notebooks" / notebook_name).read_text(encoding="utf-8"))
    code = ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"]
    for index, source in enumerate(code, start=1):
        compile(source, f"{notebook_name}:cell-{index}", "exec")
    return "\n".join(code)


class NotebookReviewLayerTests(unittest.TestCase):
    def test_every_review_notebook_has_compilable_python_cells(self) -> None:
        expected = [
            "00_environment_test.ipynb",
            "01_data_collection.ipynb",
            "02_data_preparation.ipynb",
            "03_eda.ipynb",
            "04_modelling.ipynb",
            "05_evaluation_recommendations.ipynb",
            "06_final_charts.ipynb",
        ]
        for notebook_name in expected:
            source = code_sources(notebook_name)
            self.assertNotIn("C:\\Personal\\", source, notebook_name)

    def test_notebooks_keep_their_declared_review_boundaries(self) -> None:
        environment = code_sources("00_environment_test.ipynb")
        collection = code_sources("01_data_collection.ipynb")
        preparation = code_sources("02_data_preparation.ipynb")
        presentation = code_sources("06_final_charts.ipynb")
        self.assertNotIn("savefig", environment)
        self.assertIn("collection-ledger", (PROJECT_ROOT / "notebooks/01_data_collection.ipynb").read_text(encoding="utf-8"))
        self.assertIn("feature-contract", (PROJECT_ROOT / "notebooks/02_data_preparation.ipynb").read_text(encoding="utf-8"))
        self.assertIn("validate_final_visuals", presentation)
        self.assertNotIn("build_national_panel", collection + preparation + presentation)
        self.assertIn("REBUILD_NATIONAL_PANEL = False", preparation)
        self.assertIn("SHOW_LIVE_MODEL_DIAGNOSTICS = True", presentation)

    def test_eda_notebook_is_executable_artifact_review(self) -> None:
        source = code_sources("03_eda.ipynb")
        self.assertIn("src.notebook_support", source)
        self.assertIn("national_panel_model_readiness_eda.json", source)
        self.assertNotIn("build_national_panel", source)
        self.assertNotIn(".fit(", source)

    def test_modelling_notebook_is_executable_artifact_review(self) -> None:
        source = code_sources("04_modelling.ipynb")
        self.assertIn("src.notebook_support", source)
        self.assertIn("final_temporal_test_metrics.json", source)
        self.assertIn("nine_feature_hurdle.joblib", source)
        self.assertNotIn(".fit(", source)
        self.assertNotIn("GridSearchCV", source)
        self.assertIn("model_component_frame", source)
        self.assertNotIn("plot_prediction_diagnostics", source)
        self.assertNotIn("REBUILD_MODEL_DIAGNOSTICS", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
