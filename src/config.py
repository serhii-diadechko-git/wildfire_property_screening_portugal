"""Approved spatial, temporal, and pilot configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SpatialConfig:
    analysis_crs: str = "EPSG:3763"
    grid_size_metres: int = 1_000
    context_buffer_metres: int = 2_000


SPATIAL = SpatialConfig()


@dataclass(frozen=True)
class ClcGovernanceConfig:
    """Retrospective CLC reference-layer assignment for the approved panel."""

    current_package_release_id: str = "V2020_20u1"
    assignment_by_predictor_year: tuple[tuple[int, int], ...] = (
        (2015, 2006),
        (2016, 2012),
        (2017, 2012),
        (2018, 2012),
        (2019, 2018),
        (2020, 2018),
        (2021, 2018),
        (2022, 2018),
        (2023, 2018),
        (2024, 2018),
        (2025, 2018),
    )
    prepared_path_by_reference_year: tuple[tuple[int, str], ...] = (
        (2006, "data/processed/clc/u2012_clc2006_v2020_20u1_pt.gpkg"),
        (2012, "data/processed/clc/u2018_clc2012_v2020_20u1_pt.gpkg"),
        (2018, "data/processed/clc/u2018_clc2018_v2020_20u1_pt.gpkg"),
    )
    prepared_layer_by_reference_year: tuple[tuple[int, str], ...] = (
        (2006, "u2012_clc2006_v2020_20u1_pt"),
        (2012, "u2018_clc2012_v2020_20u1_pt"),
        (2018, "u2018_clc2018_v2020_20u1_pt"),
    )
    area_processing_crs: str = "EPSG:3035"
    reconstruction_rule: str = (
        "reference_year_not_after_predictor_year; use the current official revised "
        "package for each assigned historical reference layer"
    )

    def reference_year(self, predictor_year: int) -> int:
        assignments = dict(self.assignment_by_predictor_year)
        if predictor_year not in assignments:
            raise ValueError("Predictor year is outside the approved CLC assignment")
        reference_year = assignments[predictor_year]
        if reference_year > predictor_year:
            raise ValueError("CLC reference year must not be after predictor year")
        return reference_year

    def prepared_dataset(self, predictor_year: int) -> tuple[str, str]:
        """Return the configured Portugal GeoPackage and layer for predictor year."""
        reference_year = self.reference_year(predictor_year)
        return (
            dict(self.prepared_path_by_reference_year)[reference_year],
            dict(self.prepared_layer_by_reference_year)[reference_year],
        )


@dataclass(frozen=True)
class ExtendedTrainingClcConfig:
    """Separate governed CLC assignment for the proposed backward extension.

    This deliberately does not alter the canonical 2015-2024 configuration or
    its validated panel artefacts.
    """

    assignment_by_predictor_year: tuple[tuple[int, int], ...] = tuple(
        [(year, 2006) for year in range(2010, 2016)]
        + [(year, 2012) for year in range(2016, 2019)]
        + [(year, 2018) for year in range(2019, 2022)]
    )

    def reference_year(self, predictor_year: int) -> int:
        assignments = dict(self.assignment_by_predictor_year)
        if predictor_year not in assignments:
            raise ValueError("Predictor year is outside the approved extended-training scope")
        reference_year = assignments[predictor_year]
        if reference_year > predictor_year:
            raise ValueError("CLC reference year must not be after predictor year")
        return reference_year


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
class ExtendedTrainingDesign:
    """Backward-only training extension; canonical final-test rows stay unopened."""

    predictor_start_year: int = 2010
    predictor_end_year: int = 2021
    training_years: tuple[int, int] = (2010, 2019)
    validation_years: tuple[int, int] = (2020, 2021)
    reserved_final_test_years: tuple[int, int] = (2022, 2024)
    historical_fire_window_years: int = 10

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
    assignment_method: str = "containing_valid_era5_land_cell_else_nearest_valid_land_cell"


@dataclass(frozen=True)
class OperationalForecastConfig:
    """Annual, next-calendar-year scoring contract.

    A score for calendar year ``Y`` uses predictors from the completed prior
    year ``Y-1``.  The model may be refit only through predictor year ``Y-2``
    because that is the latest row with an observed ``T+1`` ICNF label.  This
    keeps the prediction target unavailable at scoring time by design.
    """

    first_labeled_predictor_year: int = 2010
    current_forecast_year: int = 2026
    feature_count: int = 9

    def predictor_year(self, forecast_year: int) -> int:
        return forecast_year - 1

    def latest_labeled_predictor_year(self, forecast_year: int) -> int:
        return forecast_year - 2

    def latest_observed_outcome_year(self, forecast_year: int) -> int:
        return forecast_year - 1

    def history_years(self, forecast_year: int) -> tuple[int, ...]:
        predictor_year = self.predictor_year(forecast_year)
        return tuple(range(predictor_year - 10, predictor_year))


@dataclass(frozen=True)
class PilotConfig:
    """The reproducible 2023 predictor to 2024 outcome pilot request."""

    predictor_year: int = 2023
    outcome_year: int = 2024
    historical_fire_years: tuple[int, ...] = tuple(range(2013, 2023))
    clc_release: str = "CLC 2018"
    clc_role: str = "broad retrospective land-cover context; not annual parcel-level land cover"


TEMPORAL = TemporalDesign()
ERA5_LAND = Era5LandFeatureConfig()
CLC = ClcGovernanceConfig()
EXTENDED_TRAINING = ExtendedTrainingDesign()
EXTENDED_TRAINING_CLC = ExtendedTrainingClcConfig()
OPERATIONAL_FORECAST = OperationalForecastConfig()


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
