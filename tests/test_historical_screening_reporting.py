"""Focused contracts for Notebook 06 historical-screening reporting helpers."""

from __future__ import annotations

import unittest

import matplotlib.pyplot as plt
import pandas as pd

from src.historical_screening_reporting import (
    HAZARD_ORDER,
    HISTORICAL_ORDER,
    HistoricalScreeningArtifacts,
    historical_screening_display_tables,
    plot_historical_icnf_crosstab,
)


class HistoricalScreeningReportingTests(unittest.TestCase):
    def tearDown(self) -> None:
        plt.close("all")

    def test_tables_and_heatmap_keep_the_documented_order(self) -> None:
        matrix = pd.DataFrame(
            [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12], [13, 14, 15, 16, 17, 18]],
            index=HISTORICAL_ORDER,
            columns=HAZARD_ORDER,
        )
        artifacts = HistoricalScreeningArtifacts(
            screening=None,  # The table helper does not need geometry.
            band_summary=pd.DataFrame({"historical_exposure_band": HISTORICAL_ORDER, "share_of_cells": [0.4, 0.3, 0.3]}),
            hazard_summary=pd.DataFrame({"official_icnf_hazard_class": HAZARD_ORDER, "share_of_cells": [0.1] * 6}),
            cross_matrix=matrix,
        )

        bands, hazards, returned_matrix = historical_screening_display_tables(artifacts)
        self.assertEqual(bands["historical_exposure_band"].tolist(), list(HISTORICAL_ORDER))
        self.assertEqual(hazards["official_icnf_hazard_class"].tolist(), list(HAZARD_ORDER))
        self.assertEqual(returned_matrix.columns.tolist(), list(HAZARD_ORDER))
        self.assertEqual(len(plot_historical_icnf_crosstab(matrix).axes), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
