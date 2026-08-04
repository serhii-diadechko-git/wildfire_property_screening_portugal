"""Tests for the retrospective, reference-year-safe CLC assignment."""

import unittest

from src.config import CLC, TEMPORAL
from src.source_registry import CLC_GOVERNED_RELEASES


class ClcGovernanceTests(unittest.TestCase):
    def test_assignments_match_the_canonical_retrospective_rule(self) -> None:
        expected = {
            2015: 2006,
            2016: 2012,
            2017: 2012,
            2018: 2012,
            2019: 2018,
            2020: 2018,
            2021: 2018,
            2022: 2018,
            2023: 2018,
            2024: 2018,
        }
        observed = {
            year: CLC.reference_year(year)
            for year in range(TEMPORAL.predictor_start_year, TEMPORAL.predictor_end_year + 1)
        }
        self.assertEqual(observed, expected)
        self.assertTrue(all(reference_year <= year for year, reference_year in observed.items()))

    def test_governed_registry_uses_current_revised_packages(self) -> None:
        self.assertEqual(set(CLC_GOVERNED_RELEASES), {"2015", "2016-2018", "2019-2024"})
        self.assertTrue(
            all(record.release_id == "V2020_20u1" for record in CLC_GOVERNED_RELEASES.values())
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
