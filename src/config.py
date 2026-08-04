"""Approved spatial, temporal, and pilot configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SpatialConfig:
    analysis_crs: str = "EPSG:3763"
    grid_size_metres: int = 1_000
    context_buffer_metres: int = 2_000


SPATIAL = SpatialConfig()


@dataclass(frozen=True)
class TemporalDesign:
    """The approved retrospective cell-year design."""

    predictor_start_year: int = 2015
    predictor_end_year: int = 2024
    training_years: tuple[int, int] = (2015, 2019)
    validation_years: tuple[int, int] = (2020, 2021)
    final_test_years: tuple[int, int] = (2022, 2024)
    historical_fire_window_years: int = 10
    required_icnf_start_year: int = 2005
    required_icnf_end_year: int = 2025

    def historical_years(self, predictor_year: int) -> tuple[int, ...]:
        return tuple(range(predictor_year - self.historical_fire_window_years, predictor_year))

    def outcome_year(self, predictor_year: int) -> int:
        return predictor_year + 1


@dataclass(frozen=True)
class Era5LandFeatureConfig:
    """T-only coarse climate context; values are never downscaled."""

    season_months: tuple[int, ...] = (6, 7, 8, 9)
    variables: tuple[str, ...] = (
        "2m_temperature",
        "total_precipitation",
        "volumetric_soil_water_layer_1",
    )
    features: tuple[str, ...] = (
        "warm_season_mean_2m_temperature_c",
        "warm_season_total_precipitation_mm",
        "warm_season_mean_soil_water_layer1",
    )
    assignment_method: str = "containing_era5_land_cell"


@dataclass(frozen=True)
class PilotConfig:
    """The reproducible 2023 predictor to 2024 outcome pilot request."""

    predictor_year: int = 2023
    outcome_year: int = 2024
    historical_fire_years: tuple[int, ...] = tuple(range(2013, 2023))
    clc_release: str = "CLC 2018"
    clc_role: str = "broad release-aware land-cover context; not annual parcel-level land cover"


TEMPORAL = TemporalDesign()
ERA5_LAND = Era5LandFeatureConfig()


@dataclass(frozen=True)
class Era5LandCdsConfig:
    """Smallest approved CDS request for the 2023 predictor-year pilot."""

    dataset_id: str = "reanalysis-era5-land-monthly-means"
    product_type: str = "monthly_averaged_reanalysis"
    # The current CDS dataset metadata declares GRIB as its file format.
    data_format: str = "grib"
    download_format: str = "unarchived"
    # CDS order: North, West, South, East. Rounded outward from CAOP mainland.
    mainland_portugal_area: tuple[float, float, float, float] = (42.2, -9.6, 36.8, -6.0)
    pilot_raw_output: str = (
        "data/raw/climate/era5_land/"
        "era5_land_monthly_jjas_2023_mainland_portugal.grib"
    )


ERA5_LAND_CDS = Era5LandCdsConfig()
PILOT_2023_TO_2024 = PilotConfig()
