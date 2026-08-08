import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExtendedEra5AcquisitionScriptTests(unittest.TestCase):
    def test_dry_run_lists_2010_to_2025_without_network(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/download_era5_land_extended_years.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        lines = [line for line in result.stdout.splitlines() if line.startswith("{")]
        requests = [json.loads(line) for line in lines]
        self.assertEqual([item["year"] for item in requests], list(range(2010, 2026)))
        self.assertIn("--download", result.stdout)


if __name__ == "__main__":
    unittest.main()
