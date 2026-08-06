"""Safety tests for the derived-output cleanup allow-list."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.output_cleanup import CleanupTarget, planned_removals, remove_derived_outputs


class OutputCleanupTests(unittest.TestCase):
    def test_dry_run_lists_only_unpreserved_children(self) -> None:
        with self._temporary_workspace() as temporary:
            root = Path(temporary)
            target = root / "data" / "processed"
            target.mkdir(parents=True)
            (target / ".gitkeep").write_text("", encoding="utf-8")
            output = target / "nested" / "output.parquet"
            output.parent.mkdir()
            output.write_text("derived", encoding="utf-8")
            planned = planned_removals((CleanupTarget(target, frozenset({".gitkeep"})),))
            self.assertEqual(planned, [target / "nested"])
            self.assertTrue(output.exists())

    def test_confirmed_cleanup_preserves_allow_list_and_removes_nested_output(self) -> None:
        with self._temporary_workspace() as temporary:
            root = Path(temporary)
            target = root / "reports" / "figures"
            target.mkdir(parents=True)
            keep = target / "README.md"
            keep.write_text("keep", encoding="utf-8")
            output = target / "chart.png"
            output.write_text("derived", encoding="utf-8")
            removed = remove_derived_outputs((CleanupTarget(target, frozenset({"README.md"})),))
            self.assertEqual(removed, [output])
            self.assertTrue(keep.exists())
            self.assertFalse(output.exists())

    @staticmethod
    def _temporary_workspace() -> TemporaryDirectory[str]:
        """Create an isolated temporary directory under the ignored repo tmp folder.

        Some managed Windows environments deny access to the system temporary
        directory while allowing normal workspace writes. The test still never
        targets project data and removes its own temporary workspace.
        """

        project_root = Path(__file__).resolve().parents[1]
        temporary_root = project_root / "tmp"
        temporary_root.mkdir(exist_ok=True)
        return TemporaryDirectory(dir=temporary_root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
