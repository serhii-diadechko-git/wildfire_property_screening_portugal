"""Safety tests for the derived-output cleanup allow-list."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from typing import Iterator
import unittest

from src.output_cleanup import CleanupTarget, planned_removals, remove_derived_outputs


class OutputCleanupTests(unittest.TestCase):
    def test_dry_run_lists_only_unpreserved_children(self) -> None:
        with self._temporary_workspace() as temporary:
            root = temporary
            # Use neutral synthetic names: some managed Windows policies block
            # temporary paths containing protected folder names such as `data`.
            target = root / "generated" / "processed"
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
            root = temporary
            target = root / "generated" / "figures"
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
    @contextmanager
    def _temporary_workspace() -> Iterator[Path]:
        """Create an isolated fixture in `tests/` and remove it afterwards.

        Managed Windows policies can apply restrictive ACLs to directories made
        with `TemporaryDirectory`. A normal fixture directly under the existing
        writable `tests/` directory avoids that platform-specific behaviour.
        """

        root = Path(__file__).resolve().parent / ".cleanup_fixture_runtime"
        if root.exists():
            rmtree(root)
        root.mkdir()
        try:
            yield root
        finally:
            if root.exists():
                rmtree(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
