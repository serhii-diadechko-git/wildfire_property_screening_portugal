"""Read-only validation for the registered ERA5-Land pilot GRIB."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import xarray as xr

from src.config import ERA5_LAND, ERA5_LAND_CDS, PILOT_2023_TO_2024
from src.source_registry import ERA5_LAND_2023_JJAS_PILOT


GRIB_SHORT_NAMES = {
    # ECMWF GRIB's short name is 2t; cfgrib exposes it as the t2m data variable.
    "2m_temperature": "2t",
    "total_precipitation": "tp",
    "volumetric_soil_water_layer_1": "swvl1",
}


def calculate_sha256(path: Path) -> str:
    """Calculate an uppercase checksum without altering the raw file."""
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_era5_land_pilot_grib(project_root: Path) -> dict[str, object]:
    """Validate expected variables, months, spatial grid, and missing values in place."""
    path = project_root / ERA5_LAND_CDS.pilot_raw_output
    if not path.is_file():
        raise FileNotFoundError(f"Missing ERA5-Land raw GRIB: {path}")
    if calculate_sha256(path) != ERA5_LAND_2023_JJAS_PILOT.sha256:
        raise ValueError("ERA5-Land GRIB checksum differs from the registered immutable raw file")

    expected_months = tuple(f"{month:02d}" for month in ERA5_LAND.season_months)
    expected_area = list(ERA5_LAND_CDS.mainland_portugal_area)
    variable_results: dict[str, dict[str, object]] = {}
    reference_shape: tuple[int, int, int] | None = None
    reference_extent: tuple[float, float, float, float] | None = None

    for variable in ERA5_LAND.variables:
        short_name = GRIB_SHORT_NAMES[variable]
        dataset = xr.open_dataset(
            path,
            engine="cfgrib",
            backend_kwargs={"indexpath": "", "filter_by_keys": {"shortName": short_name}},
        )
        try:
            data_variable = next(iter(dataset.data_vars))
            expected_data_variable = "t2m" if short_name == "2t" else short_name
            if data_variable != expected_data_variable:
                raise ValueError(f"Expected data variable {expected_data_variable}, found {data_variable}")
            shape = (int(dataset.sizes["time"]), int(dataset.sizes["latitude"]), int(dataset.sizes["longitude"]))
            months = tuple(str(value.astype("datetime64[M]"))[-2:] for value in dataset.time.values)
            extent = (
                float(dataset.latitude.max()),
                float(dataset.longitude.min()),
                float(dataset.latitude.min()),
                float(dataset.longitude.max()),
            )
            missing_count = int(dataset[data_variable].isnull().sum().item())
            if months != expected_months:
                raise ValueError(f"Expected JJAS 2023 months {expected_months}, found {months}")
            if shape[0] != len(expected_months) or missing_count == shape[0] * shape[1] * shape[2]:
                raise ValueError(f"Unexpected all-missing or incomplete data for {short_name}")
            if reference_shape is None:
                reference_shape, reference_extent = shape, extent
            elif shape != reference_shape or extent != reference_extent:
                raise ValueError("ERA5-Land variables do not share the same grid")
            variable_results[variable] = {
                "grib_short_name": short_name,
                "shape": shape,
                "missing_value_count": missing_count,
                "unit": dataset[data_variable].attrs.get("units"),
            }
        finally:
            dataset.close()

    if reference_extent is None or any(abs(actual - expected) > 1e-9 for actual, expected in zip(reference_extent, expected_area)):
        raise ValueError(f"Expected CDS area {expected_area}, found {reference_extent}")
    facts = ERA5_LAND_2023_JJAS_PILOT.validation_facts
    observed_short_names = tuple(result["grib_short_name"] for result in variable_results.values())
    observed_missing_counts = tuple(
        (result["grib_short_name"], result["missing_value_count"])
        for result in variable_results.values()
    )
    if (reference_shape != facts.grid_shape or expected_months != facts.months
            or observed_short_names != facts.grib_short_names
            or observed_missing_counts != facts.missing_value_counts):
        raise ValueError("ERA5-Land GRIB no longer matches registered validation facts")
    return {
        "raw_path": ERA5_LAND_CDS.pilot_raw_output,
        "filename": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": calculate_sha256(path),
        "dataset_id": ERA5_LAND_CDS.dataset_id,
        "request": {
            "product_type": ERA5_LAND_CDS.product_type,
            "year": PILOT_2023_TO_2024.predictor_year,
            "months": expected_months,
            "time": "00:00",
            "variables": ERA5_LAND.variables,
            "area": expected_area,
            "data_format": ERA5_LAND_CDS.data_format,
        },
        "grid_shape_time_latitude_longitude": reference_shape,
        "area_north_west_south_east": reference_extent,
        "variables": variable_results,
        "missing_values": "Present only for ERA5-Land land-mask cells outside mainland land coverage; counts are reported per variable.",
    }
