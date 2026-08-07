"""Focused contracts for Notebook 06 historical-screening reporting helpers."""

from __future__ import annotations

import unittest

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import box

from src.historical_screening_reporting import (
    HAZARD_ORDER,
    HISTORICAL_ORDER,
    HistoricalScreeningArtifacts,
    historical_screening_display_tables,
    plot_historical_and_icnf_maps,
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

    def test_optional_operational_layer_adds_a_third_map_panel(self) -> None:
        historical = gpd.GeoDataFrame(
            {
                "historical_exposure_band": ["lower", "higher"],
                "official_icnf_hazard_class": ["low", "high"],
            },
            geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
            crs="EPSG:3763",
        )
        operational = gpd.GeoDataFrame(
            {
                "prediction_input_year": [2025, 2025],
                "forecast_year": [2026, 2026],
                "predicted_burned_share_next_year": [0.0, 0.1],
                "predicted_exposure_percentile": [0.5, 0.9],
            },
            geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
            crs="EPSG:3763",
        )

        figure = plot_historical_and_icnf_maps(historical, operational)

        self.assertEqual(len(figure.axes), 3)
        self.assertEqual(figure.axes[0].get_legend().get_title().get_text(), "Historical exposure bands — 1 km cells")
        self.assertEqual(
            figure.axes[1].get_legend().get_title().get_text(),
            "ICNF structural hazard class — predominant class per 1 km cell",
        )
        self.assertIn("2026 estimated comparative wildfire exposure", figure.axes[2].get_title())
        self.assertEqual(figure.axes[2].get_legend().get_title().get_text(), "Estimated comparative exposure")


if __name__ == "__main__":
    unittest.main(verbosity=2)
