"""Public-package checks: portable paths, source access, and runnable entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.project_run import default_reproduction_stages, load_source_manifest, raw_data_preflight, validation_command


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_TEXT_ROOTS = (ROOT / "README.md", ROOT / "docs", ROOT / "notebooks", ROOT / "qgis", ROOT / "scripts", ROOT / "src")


class PublicReproducibilityTests(unittest.TestCase):
    def test_source_manifest_is_complete_and_machine_readable(self) -> None:
        manifest = load_source_manifest()
        self.assertEqual(manifest["manifest_version"], "1.0")
        self.assertGreaterEqual(len(manifest["sources"]), 5)
        keys = {source["key"] for source in manifest["sources"]}
        self.assertTrue({"icnf_annual_burned_areas", "caop_2025", "copernicus_clc", "copernicus_dem_glo30", "era5_land_jjas"}.issubset(keys))
        self.assertEqual(json.loads((ROOT / "data/source_manifest.json").read_text(encoding="utf-8")), manifest)

    def test_preflight_reports_groups_without_writing_raw_data(self) -> None:
        result = raw_data_preflight()
        self.assertEqual(result["raw_directory"], "data/raw")
        self.assertTrue(result["raw_data_is_git_ignored"])
        self.assertGreaterEqual(len(result["groups"]), 6)
        for group in result["groups"]:
            self.assertIn(group["status"], {"ready", "missing"})
            self.assertEqual(group["expected_files"], group["present_files"] + len(group["missing_files"]))

    def test_public_text_has_no_known_personal_absolute_path(self) -> None:
        forbidden = ("c:/personal/", "c:\\personal\\", "sdyadechko", "/users/", "/home/")
        files: list[Path] = []
        for root in PUBLIC_TEXT_ROOTS:
            if root.is_file():
                files.append(root)
            else:
                files.extend(path for path in root.rglob("*") if path.suffix in {".py", ".md", ".ipynb", ".bat", ".json"})
        for path in files:
            content = path.read_text(encoding="utf-8", errors="replace").lower()
            self.assertFalse(any(token in content for token in forbidden), path.relative_to(ROOT))

    def test_public_docs_expose_data_and_one_command_workflow(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        data_readme = (ROOT / "data/README.md").read_text(encoding="utf-8")
        notebook_readme = (ROOT / "notebooks" / "README.md").read_text(encoding="utf-8")
        self.assertIn("scripts/run_project.py --mode preflight", readme)
        self.assertIn("--mode reproduce --confirm-rebuild", readme)
        self.assertIn("VS Code", readme)
        self.assertIn("VS Code", notebook_readme)
        self.assertNotIn("python -m jupyter lab", readme.lower())
        self.assertNotIn("python -m jupyter lab", notebook_readme.lower())
        self.assertNotIn("jupyterlab", (ROOT / "requirements.txt").read_text(encoding="utf-8").lower())
        self.assertIn("source_manifest.json", data_readme)
        self.assertIn("data/raw/", data_readme)

    def test_reproduction_stages_are_explicit_and_platform_neutral(self) -> None:
        stages = default_reproduction_stages(include_qgis=False)
        self.assertGreaterEqual(len(stages), 10)
        self.assertEqual(stages[0].name, "environment")
        self.assertEqual(stages[-1].name, "full test suite")
        self.assertIn("model diagnostics", [stage.name for stage in stages])
        for stage in stages:
            self.assertNotIn("C:\\", " ".join(stage.command))
            self.assertNotIn("/Users/", " ".join(stage.command))

    def test_fresh_checkout_validation_has_a_bootstrap_scope(self) -> None:
        command, scope = validation_command()
        self.assertIn("unittest", command)
        self.assertIn("bootstrap" if scope.startswith("bootstrap") else "full", scope)

    def test_public_launcher_bootstraps_the_repository_virtual_environment(self) -> None:
        launcher = (ROOT / "scripts" / "run_project.py").read_text(encoding="utf-8")
        self.assertIn("_use_project_venv_if_available()", launcher)
        self.assertIn("os.execv", launcher)
        self.assertIn('ROOT / ".venv"', launcher)

    def test_windows_qgis_helper_uses_discovery_not_a_pinned_installation(self) -> None:
        batch = (ROOT / "scripts/run_qgis_presentation_project.bat").read_text(encoding="utf-8")
        self.assertNotIn("QGIS 3.44.12", batch)
        self.assertIn("QGIS_ROOT", batch)
        self.assertIn("ProgramFiles", batch)


if __name__ == "__main__":
    unittest.main(verbosity=2)
