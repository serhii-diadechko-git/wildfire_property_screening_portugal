"""Canonical analytical feature-table contract and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from src.config import CLC, TEMPORAL


PREDICTOR_COLUMNS = (
    "built_up_share",
    "forest_shrub_share_2km",
    "mean_slope_2km",
    "fire_years_previous_10y_2km",
    "warm_season_mean_2m_temperature_c",
    "warm_season_total_precipitation_mm",
    "warm_season_mean_soil_water_layer1",
)
TARGET_COLUMN = "burned_share_next_year"
IDENTIFIER_COLUMNS = (
    "cell_year_id",
    "cell_id",
    "observation_year",
)
SOURCE_METADATA_COLUMNS = (
    "outcome_year",
    "historical_fire_start_year",
    "historical_fire_end_year",
    "climate_reference_year",
    "land_cover_reference_year",
    "land_cover_release_id",
    "land_cover_release_date",
    "terrain_release_id",
)
TABLE_COLUMNS = IDENTIFIER_COLUMNS + SOURCE_METADATA_COLUMNS + PREDICTOR_COLUMNS + (TARGET_COLUMN,)
UNIQUE_KEY = ("cell_id", "observation_year")


@dataclass(frozen=True)
class FieldContract:
    dtype: str
    unit: str
    minimum: float | None
    maximum: float | None
    missing_rule: Literal["forbidden", "era5_land_mask_allowed"]
    source_year_rule: str


FIELD_CONTRACTS = {
    "built_up_share": FieldContract(
        "float64", "share_of_cell_land_area", 0.0, 1.0, "forbidden",
        "governed CLC reference year assigned to T",
    ),
    "forest_shrub_share_2km": FieldContract(
        "float64", "share_of_mainland_land_in_2km_outward_buffer", 0.0, 1.0, "forbidden",
        "governed CLC reference year assigned to T",
    ),
    "mean_slope_2km": FieldContract(
        "float64", "degrees", 0.0, 90.0, "forbidden",
        "static Copernicus DEM GLO-30 2021 release",
    ),
    "fire_years_previous_10y_2km": FieldContract(
        "int8", "count_of_distinct_years", 0.0, 10.0, "forbidden",
        "inclusive T-10 through T-1",
    ),
    "warm_season_mean_2m_temperature_c": FieldContract(
        "float64", "degrees_Celsius", -20.0, 60.0, "era5_land_mask_allowed",
        "JJAS of T only",
    ),
    "warm_season_total_precipitation_mm": FieldContract(
        "float64", "millimetres_JJAS_total", 0.0, 3000.0, "era5_land_mask_allowed",
        "day-weighted JJAS of T only",
    ),
    "warm_season_mean_soil_water_layer1": FieldContract(
        "float64", "m3_per_m3", 0.0, 1.0, "era5_land_mask_allowed",
        "JJAS of T only",
    ),
    TARGET_COLUMN: FieldContract(
        "float64", "share_of_cell_land_area", 0.0, 1.0, "forbidden",
        "ICNF burned-area geometry in T+1",
    ),
}


def source_years(predictor_year: int) -> dict[str, int | tuple[int, ...]]:
    """Return explicit source years and reject years outside the canonical panel."""
    if not TEMPORAL.predictor_start_year <= predictor_year <= TEMPORAL.predictor_end_year:
        raise ValueError("Predictor year is outside the canonical 2015-2024 scope")
    history = TEMPORAL.historical_years(predictor_year)
    if history[-1] >= predictor_year:
        raise ValueError("Historical fire context must end before T")
    return {
        "predictor_year": predictor_year,
        "history_years": history,
        "climate_year": predictor_year,
        "land_cover_reference_year": CLC.reference_year(predictor_year),
        "outcome_year": TEMPORAL.outcome_year(predictor_year),
    }


def validate_feature_table(
    table: pd.DataFrame,
    *,
    expected_years: tuple[int, ...],
    expected_cell_ids: tuple[str, ...],
) -> dict[str, object]:
    """Validate schema, ranges, missingness, uniqueness, and temporal alignment."""
    missing_columns = [column for column in TABLE_COLUMNS if column not in table.columns]
    extra_columns = [column for column in table.columns if column not in TABLE_COLUMNS]
    if missing_columns or extra_columns:
        raise ValueError(f"Feature-table schema mismatch; missing={missing_columns}, extra={extra_columns}")
    if table.duplicated(list(UNIQUE_KEY)).any():
        raise ValueError("Duplicate cell_id x observation_year analytical key")
    expected_keys = {(cell_id, year) for cell_id in expected_cell_ids for year in expected_years}
    observed_keys = set(zip(table.cell_id, table.observation_year, strict=True))
    if observed_keys != expected_keys:
        raise ValueError("Pilot analytical keys do not match the declared sample")
    if not table.cell_year_id.equals(table.cell_id + "_" + table.observation_year.astype(str)):
        raise ValueError("cell_year_id is not deterministic")

    temporal_errors: list[str] = []
    for row in table.itertuples(index=False):
        years = source_years(int(row.observation_year))
        expected_history = years["history_years"]
        checks = (
            row.outcome_year == years["outcome_year"],
            row.climate_reference_year == years["climate_year"],
            row.land_cover_reference_year == years["land_cover_reference_year"],
            row.historical_fire_start_year == expected_history[0],
            row.historical_fire_end_year == expected_history[-1],
        )
        if not all(checks):
            temporal_errors.append(row.cell_year_id)
    if temporal_errors:
        raise ValueError(f"Temporal alignment failed for {temporal_errors[:5]}")

    for column, contract in FIELD_CONTRACTS.items():
        values = table[column]
        if contract.missing_rule == "forbidden" and values.isna().any():
            raise ValueError(f"Unexpected missing values in {column}")
        finite = values.dropna().astype(float)
        if not np.isfinite(finite).all():
            raise ValueError(f"Non-finite values in {column}")
        if contract.minimum is not None and (finite < contract.minimum - 1e-9).any():
            raise ValueError(f"{column} below allowed range")
        if contract.maximum is not None and (finite > contract.maximum + 1e-9).any():
            raise ValueError(f"{column} above allowed range")
    fire_values = table.fire_years_previous_10y_2km
    if not np.equal(fire_values, np.floor(fire_values)).all():
        raise ValueError("Historical-fire year count must be integral")

    climate = list(PREDICTOR_COLUMNS[-3:])
    climate_masks = table[climate].isna()
    if not climate_masks.eq(climate_masks.iloc[:, 0], axis=0).all().all():
        raise ValueError("ERA5-Land mask must be identical across all three climate features")

    return {
        "row_count": len(table),
        "expected_row_count": len(expected_keys),
        "unique_analytical_key": True,
        "years": tuple(sorted(table.observation_year.unique())),
        "cell_count": table.cell_id.nunique(),
        "missingness": {column: int(count) for column, count in table.isna().sum().items()},
    }
