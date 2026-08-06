"""Stable ERA5-Land source selection and JJAS derivation helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

from src.source_registry import ERA5_LAND_AVAILABLE_ARCHIVES, ERA5_LAND_PRECIPITATION_CORRECTIONS


ROOT = Path(__file__).resolve().parents[1]


def era5_source_paths(predictor_year: int) -> dict[str, Path]:
    """Select validated annual GRIBs, including mandatory precipitation corrections."""
    if predictor_year not in ERA5_LAND_AVAILABLE_ARCHIVES:
        raise ValueError(f"No registered ERA5-Land file for {predictor_year}")
    annual = ERA5_LAND_AVAILABLE_ARCHIVES[predictor_year]
    precipitation = ERA5_LAND_PRECIPITATION_CORRECTIONS.get(predictor_year, annual)
    if predictor_year in (2022, 2023) and precipitation is annual:
        raise ValueError(f"Corrected precipitation source is mandatory for {predictor_year}")
    return {
        "temperature_and_soil_water": ROOT / annual.raw_path,
        "precipitation": ROOT / precipitation.raw_path,
    }


def jjas_total_precipitation_mm(values_m_per_day: np.ndarray, months: tuple[int, ...]) -> np.ndarray:
    """Convert monthly mean daily precipitation in metres/day to a JJAS total."""
    days = {6: 30, 7: 31, 8: 31, 9: 30}
    if months != (6, 7, 8, 9):
        raise ValueError(f"Expected ordered JJAS months, found {months}")
    weights = np.asarray([days[month] for month in months], dtype="float64")[:, None, None]
    all_missing = np.isnan(values_m_per_day).all(axis=0)
    totals = np.nansum(values_m_per_day * weights, axis=0) * 1000.0
    totals[all_missing] = np.nan
    return totals


def read_grib_variable(path: Path, short_name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[int, ...]]:
    """Read one GRIB short-name without creating persistent cfgrib indexes."""
    dataset = xr.open_dataset(
        path,
        engine="cfgrib",
        backend_kwargs={"indexpath": "", "filter_by_keys": {"shortName": short_name}},
    )
    try:
        variable = next(iter(dataset.data_vars))
        values = np.asarray(dataset[variable].values, dtype="float64")
        time_coordinate = "time" if "time" in dataset.coords else "valid_time"
        months = tuple(
            int(str(value.astype("datetime64[M]"))[-2:])
            for value in dataset[time_coordinate].values
        )
        return (
            np.asarray(dataset.latitude.values, dtype="float64"),
            np.asarray(dataset.longitude.values, dtype="float64"),
            values,
            months,
        )
    finally:
        dataset.close()
