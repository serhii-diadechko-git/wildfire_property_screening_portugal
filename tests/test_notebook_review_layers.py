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


if __name__ == "__main__":
    unittest.main(verbosity=2)
