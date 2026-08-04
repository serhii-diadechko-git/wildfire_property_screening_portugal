"""Immutable source provenance records registered by the project.

This module records only sources that are already present locally.  It does not
download, rename, or modify source files.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceRecord:
    key: str
    dataset_edition_or_year: str
    official_source_url: str
    licence_or_terms_reference: str
    access_date: str
    acquisition_method: str
    raw_path: str
    filename: str
    expected_sha256: str
    required_members: tuple[str, ...]
    validation_facts: "IcnfValidationFacts | None" = None


@dataclass(frozen=True)
class IcnfValidationFacts:
    """Observed read-only facts for one original ICNF archive."""

    feature_count: int
    non_empty_geometry_count: int
    invalid_geometry_count: int
    field_names: tuple[str, ...] | None
    required_fields: tuple[str, ...]
    geometry_types: tuple[str, ...] = ()
    crs: str = "EPSG:3763"
    coverage: str = "Mainland Portugal"
    null_geometry_count: int = 0
    year_values: tuple[int, ...] = ()


@dataclass(frozen=True)
class InterimDerivativeRecord:
    """Provenance for a reproducible interim derivative, never a raw source."""

    key: str
    input_source_path: str
    boundary_path: str
    output_path: str
    clip_method: str
    crs: str
    registered_date: str
    validation_facts: "ClcInterimValidationFacts | None" = None


@dataclass(frozen=True)
class ClcInterimValidationFacts:
    """Observed read-only facts for the CLC mainland interim derivative."""

    layer_name: str
    feature_count: int
    geometry_type: str
    class_code_field: str
    unique_valid_clc_code_count: int
    null_geometry_count: int
    empty_geometry_count: int
    invalid_geometry_count: int


@dataclass(frozen=True)
class Era5LandValidationFacts:
    """Observed read-only facts for one immutable ERA5-Land GRIB."""

    grid_shape: tuple[int, int, int]
    months: tuple[str, ...]
    grib_short_names: tuple[str, ...]
    missing_value_counts: tuple[tuple[str, int], ...]
    units: tuple[tuple[str, str], ...] = ()
    step_types: tuple[tuple[str, str], ...] = ()
    step_ranges: tuple[tuple[str, str], ...] = ()
    stream: str = "moda"
    precipitation_status: str = "validated"
    validation_note: str = ""


@dataclass(frozen=True)
class Era5LandRawRecord:
    """Provenance and observed facts for one immutable CDS GRIB retrieval."""

    key: str
    dataset_id: str
    official_source_url: str
    licence_or_terms_reference: str
    retrieval_date: str
    acquisition_method: str
    raw_path: str
    filename: str
    sha256: str
    product_type: str
    year: int
    months: tuple[str, ...]
    time: str
    variables: tuple[str, ...]
    area_north_west_south_east: tuple[float, float, float, float]
    data_format: str
    validation_facts: Era5LandValidationFacts


@dataclass(frozen=True)
class ClcRawRecord:
    """CLC package provenance and validation status."""

    key: str
    reference_year: int
    release_id: str
    release_date: str
    official_source_url: str
    availability_evidence_url: str
    licence_or_terms_reference: str
    access_date: str
    raw_path: str | None
    filename: str | None
    sha256: str | None
    crs: str
    coverage: str
    format: str
    class_code_field: str
    class_mapping: tuple[tuple[str, tuple[str, ...]], ...]
    validation_status: str
    catalogue_dataset_uid: str | None = None
    catalogue_file_id: str | None = None


@dataclass(frozen=True)
class EvidenceRecord:
    """Immutable official evidence file used for release governance."""

    key: str
    official_source_url: str
    access_date: str
    raw_path: str
    filename: str
    sha256: str


@dataclass(frozen=True)
class CopDemTileRecord:
    """One immutable Copernicus DEM GLO-30 COG tile."""

    tile_id: str
    official_source_url: str
    raw_path: str
    filename: str
    sha256: str
    crs: str = "EPSG:4326"
    dimensions: tuple[int, int] = (3600, 3600)
    resolution_arc_seconds: float = 1.0
    data_type: str = "float32"


@dataclass(frozen=True)
class CopDemCollectionRecord:
    """Collection-level provenance and spatial policy for the DEM tile set."""

    key: str
    dataset_name: str
    release_id: str
    official_source_url: str
    licence_or_terms_reference: str
    access_date: str
    acquisition_method: str
    coverage_requirement: str
    crs: str
    resolution: str
    format: str
    tile_ids: tuple[str, ...]
    ocean_no_source_tiles: tuple[str, ...]
    coastal_data_rule: str


CAOP_2025 = SourceRecord(
    key="caop_2025",
    dataset_edition_or_year="CAOP 2025 Mainland Portugal boundary",
    official_source_url="https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop",
    licence_or_terms_reference="Available without charge; see docs/source_plan.md.",
    access_date="2026-08-03",
    acquisition_method="manual browser download",
    raw_path="data/raw/boundaries/dgt_caop/CAOP_Continente_2025-gpkg.zip",
    filename="CAOP_Continente_2025-gpkg.zip",
    expected_sha256="87CD67F4B1FBADF23D9324E6FB231FF05531E4DB347AF36CCC7C6CBABE3ECD1D",
    required_members=("Continente_CAOP2025.gpkg",),
)

ICNF_2024 = SourceRecord(
    key="icnf_2024",
    dataset_edition_or_year="ICNF annual burned areas, 2024",
    official_source_url="https://geocatalogo.icnf.pt/catalogo_tema5.html",
    licence_or_terms_reference="Public data with attribution requirements; see docs/source_plan.md.",
    access_date="2026-08-03",
    acquisition_method="manual browser download",
    raw_path="data/raw/wildfire/icnf_burned_areas/ardida_2024.zip",
    filename="ardida_2024.zip",
    expected_sha256="B12C74C4D79F928DC55B46977FD0AAF082EDCB05B75474342BB14B4FEC626965",
    required_members=("ardida_2024.shp", "ardida_2024.shx", "ardida_2024.dbf", "ardida_2024.prj"),
    validation_facts=IcnfValidationFacts(
        feature_count=1558,
        non_empty_geometry_count=1558,
        invalid_geometry_count=0,
        field_names=None,
        required_fields=("Cod_SGIF", "Ano", "DH_Inicio", "AreaHaSIG"),
    ),
)


_ICNF_URL = "https://geocatalogo.icnf.pt/catalogo_tema5.html"
_ICNF_TERMS = "Public data with attribution requirements; see docs/source_plan.md."
_ICNF_MEMBERS = (".shp", ".shx", ".dbf", ".prj")
_ICNF_STANDARD_FIELDS = (
    "Cod_SGIF", "Cod_ANEPC", "Ano", "DH_Inicio", "DH_1Interv", "DH_Fim",
    "Duracao_m", "PI_DICOFRE", "PI_NUTS3", "PI_Distrit", "PI_Conc", "PI_Freg",
    "PI_Local", "Causa_Cod", "Causa_Tipo", "Causa_Desc", "AreaHaSIG", "AreaHaSGIF",
    "AreaHaPov", "AreaHaMato", "AreaHaAgri", "Edicao",
)


def _icnf_record(
    year: int,
    checksum: str,
    feature_count: int,
    invalid_geometry_count: int,
    field_names: tuple[str, ...] | None,
    *,
    official_source_url: str = _ICNF_URL,
    acquisition_method: str = "manual browser download",
    geometry_types: tuple[str, ...] = (),
    required_fields: tuple[str, ...] = ("Ano", "AreaHaSIG"),
) -> SourceRecord:
    """Create one manually acquired, immutable annual ICNF provenance record."""
    filename = f"ardida_{year}.zip"
    return SourceRecord(
        key=f"icnf_{year}",
        dataset_edition_or_year=f"ICNF annual burned areas, {year}",
        official_source_url=official_source_url,
        licence_or_terms_reference=_ICNF_TERMS,
        access_date="2026-08-04",
        acquisition_method=acquisition_method,
        raw_path=f"data/raw/wildfire/icnf_burned_areas/{filename}",
        filename=filename,
        expected_sha256=checksum,
        required_members=tuple(f"ardida_{year}{suffix}" for suffix in _ICNF_MEMBERS),
        validation_facts=IcnfValidationFacts(
            feature_count=feature_count,
            non_empty_geometry_count=feature_count,
            invalid_geometry_count=invalid_geometry_count,
            field_names=field_names,
            required_fields=required_fields,
            geometry_types=geometry_types,
            year_values=(year,),
        ),
    )


ICNF_2013 = _icnf_record(2013, "0B611EDABEE80665E9FB8EBCBAE4B2792A51EDAC7635ADCCCAA7821BC120A9C2", 3150, 111, ("Ano", "AreaHaSIG"))
ICNF_2012 = _icnf_record(2012, "F98281D4F3A03E10BC9F34952EE1E9E6B0990DAF6FBB1602455AF75997696AE4", 2971, 41, None)
ICNF_2014 = _icnf_record(2014, "B10723986742F3F801A9C811495470A2C2D4A1F393BB758334215D1F85C3E57C", 1100, 72, _ICNF_STANDARD_FIELDS)
ICNF_2015 = _icnf_record(2015, "0BA69E168349A39E67E1AF851629DD04E814E071B685DEFE87D31196396845DD", 1651, 83, _ICNF_STANDARD_FIELDS)
ICNF_2016 = _icnf_record(2016, "DAD27A6A87E2AA6D31C07DFE3715FCDAE333CBA08B06C5E91AA54E4CB5841189", 2838, 111, _ICNF_STANDARD_FIELDS)
ICNF_2017 = _icnf_record(2017, "7C44B43278797F58489A88834F3E386DD84C5EE0382F31BE2CC49ABBE0647D64", 2765, 27, _ICNF_STANDARD_FIELDS)
ICNF_2018 = _icnf_record(2018, "8EB051B45F1B675F5357AF4C484A0EC2537CEF27D66BDE08E6826DC658C0A726", 537, 24, _ICNF_STANDARD_FIELDS)
ICNF_2019 = _icnf_record(2019, "2CD7B31CA6992BC388B8228AD3731CC1372D3380535BC504E389747500446296", 1725, 54, _ICNF_STANDARD_FIELDS)
ICNF_2020 = _icnf_record(2020, "D64AD2DE1B02D67B001437AE33FE015979BB5768DFAE2DF64F3A293A66EE3BE9", 1777, 22, _ICNF_STANDARD_FIELDS)
ICNF_2021 = _icnf_record(2021, "75845B062236B6299BEA9B03A666B41725EDD67C9B6D996FFA457FAE2CA19FC4", 918, 1, _ICNF_STANDARD_FIELDS)
ICNF_2022 = _icnf_record(2022, "EDA0BF60B17B5878D6CEF3BC17ECB6B845EA9479241A3138DED23DEA54605382", 1786, 13, ("id",) + _ICNF_STANDARD_FIELDS)
ICNF_2023 = _icnf_record(
    2023,
    "D236FE3B0B1C6DB27FDB2B2098BA32267EA071364EBA9260AA8A3424919295CA",
    1736,
    11,
    ("id",) + _ICNF_STANDARD_FIELDS,
    official_source_url="https://si.icnf.pt/shp/ardida_2023",
    acquisition_method="scripted HTTPS retrieval from the official ICNF catalogue endpoint",
    geometry_types=("Polygon", "MultiPolygon"),
    required_fields=("Cod_SGIF", "Ano", "DH_Inicio", "AreaHaSIG"),
)
ICNF_2025 = _icnf_record(
    2025,
    "61EB2DDE27F7E348F3B8302CD0412C7502D5F7C8324F11B68C94A9CEBA10FDC0",
    2084,
    2,
    _ICNF_STANDARD_FIELDS,
    official_source_url="https://si.icnf.pt/shp/ardida_2025",
    acquisition_method="scripted HTTPS retrieval from the official ICNF catalogue endpoint",
    geometry_types=("Polygon", "MultiPolygon"),
    required_fields=("Cod_SGIF", "Ano", "DH_Inicio", "AreaHaSIG"),
)

PILOT_ICNF_HISTORY = (
    ICNF_2013, ICNF_2014, ICNF_2015, ICNF_2016, ICNF_2017,
    ICNF_2018, ICNF_2019, ICNF_2020, ICNF_2021, ICNF_2022,
)
PILOT_ICNF_ARCHIVES = {2013: ICNF_2013, 2014: ICNF_2014, 2015: ICNF_2015, 2016: ICNF_2016, 2017: ICNF_2017,
                       2018: ICNF_2018, 2019: ICNF_2019, 2020: ICNF_2020, 2021: ICNF_2021, 2022: ICNF_2022,
                       2024: ICNF_2024}

REGISTERED_SOURCES = {
    record.key: record
    for record in (CAOP_2025, ICNF_2012, *PILOT_ICNF_HISTORY, ICNF_2023, ICNF_2024, ICNF_2025)
}
PANEL_ICNF_ARCHIVES = {
    2012: ICNF_2012,
    **{year: record for year, record in PILOT_ICNF_ARCHIVES.items() if year != 2024},
    2023: ICNF_2023,
    2024: ICNF_2024,
    2025: ICNF_2025,
}

CLC_2018_MAINLAND_INTERIM = InterimDerivativeRecord(
    key="clc_2018_mainland_interim",
    input_source_path="data/raw/clc/u2018_clc2018_v2020_20u1_geoPackage.zip",
    boundary_path="data/interim/mainland_portugal_boundary.gpkg",
    output_path="data/interim/clc_2018_mainland.gpkg",
    clip_method="vector clip/intersection to the mainland boundary; validate as an existing interim derivative",
    crs="EPSG:3035",
    registered_date="2026-08-04",
    validation_facts=ClcInterimValidationFacts(
        layer_name="clc_2018_mainland",
        feature_count=54191,
        geometry_type="MultiPolygon",
        class_code_field="Code_18",
        unique_valid_clc_code_count=42,
        null_geometry_count=0,
        empty_geometry_count=0,
        invalid_geometry_count=0,
    ),
)

_CLC_RELEASE_LINEAGE_URL = (
    "https://land.copernicus.eu/en/technical-library/clc-release-lineage/@@download/file"
)
_CLC_LICENCE = (
    "https://land.copernicus.eu/en/data-policy — full, open and free access; source "
    "attribution and identification of adaptations are required."
)
_CLC_CLASS_MAPPING = (
    ("built_up_share", ("111", "112", "121", "122", "123", "124", "131", "132", "133", "141", "142")),
    ("forest_shrub_share_2km", ("311", "312", "313", "321", "322", "323", "324")),
)

CLC_2006_V17 = ClcRawRecord(
    key="clc_2006_v17",
    reference_year=2006,
    release_id="V17",
    release_date="2013-12-02",
    official_source_url="https://land.copernicus.eu/en/products/corine-land-cover/clc-2006",
    availability_evidence_url=_CLC_RELEASE_LINEAGE_URL,
    licence_or_terms_reference=_CLC_LICENCE,
    access_date="2026-08-04",
    raw_path=None,
    filename=None,
    sha256=None,
    crs="EPSG:3035",
    coverage="Europe, including mainland Portugal",
    format="historical archived vector package required",
    class_code_field="Code_06",
    class_mapping=_CLC_CLASS_MAPPING,
    validation_status=(
        "preserved historical release evidence only; this exact archived package is no "
        "longer required by the retrospective reconstruction rule"
    ),
)

CLC_2012_V18_5_1 = ClcRawRecord(
    key="clc_2012_v18_5_1",
    reference_year=2012,
    release_id="V18_5_1",
    release_date="2016-09-19",
    official_source_url="https://land.copernicus.eu/en/products/corine-land-cover/clc-2012",
    availability_evidence_url=_CLC_RELEASE_LINEAGE_URL,
    licence_or_terms_reference=_CLC_LICENCE,
    access_date="2026-08-04",
    raw_path=None,
    filename=None,
    sha256=None,
    crs="EPSG:3035",
    coverage="EEA39, including mainland Portugal",
    format="historical archived vector package required",
    class_code_field="Code_12",
    class_mapping=_CLC_CLASS_MAPPING,
    validation_status=(
        "preserved historical release evidence only; this exact archived package is no "
        "longer required by the retrospective reconstruction rule"
    ),
)

CLC_2018_V20 = ClcRawRecord(
    key="clc_2018_v20",
    reference_year=2018,
    release_id="V20",
    release_date="2019-05-01",
    official_source_url="https://land.copernicus.eu/en/products/corine-land-cover/clc2018",
    availability_evidence_url=_CLC_RELEASE_LINEAGE_URL,
    licence_or_terms_reference=_CLC_LICENCE,
    access_date="2026-08-04",
    raw_path=None,
    filename=None,
    sha256=None,
    crs="EPSG:3035",
    coverage="EEA39, including mainland Portugal",
    format="historical archived vector package required",
    class_code_field="Code_18",
    class_mapping=_CLC_CLASS_MAPPING,
    validation_status=(
        "preserved historical release evidence only; this exact archived package is no "
        "longer required by the retrospective reconstruction rule"
    ),
)

CLC_HISTORICAL_RELEASE_EVIDENCE = (
    CLC_2006_V17,
    CLC_2012_V18_5_1,
    CLC_2018_V20,
)

CLC_2006_V2020_20U1 = ClcRawRecord(
    key="clc_2006_v2020_20u1",
    reference_year=2006,
    release_id="V2020_20u1",
    release_date="2020 (exact day unavailable in the official product metadata)",
    official_source_url="https://land.copernicus.eu/en/products/corine-land-cover/clc-2006",
    availability_evidence_url=_CLC_RELEASE_LINEAGE_URL,
    licence_or_terms_reference=_CLC_LICENCE,
    access_date="2026-08-04",
    raw_path="data/raw/clc/u2012_clc2006_v2020_20u1_geoPackage.zip",
    filename="u2012_clc2006_v2020_20u1_geoPackage.zip",
    sha256=None,
    crs="EPSG:3035",
    coverage="Europe, including mainland Portugal",
    format="GeoPackage in ZIP",
    class_code_field="Code_06",
    class_mapping=_CLC_CLASS_MAPPING,
    validation_status=(
        "official revised package identified; local acquisition is pending authenticated "
        "Copernicus Land Monitoring Service access"
    ),
    catalogue_dataset_uid="d443c86fec2f49e08ff12c7decdbf2af",
    catalogue_file_id="46d516c6-b749-4064-a556-854b85ba5175",
)

CLC_2012_V2020_20U1 = ClcRawRecord(
    key="clc_2012_v2020_20u1",
    reference_year=2012,
    release_id="V2020_20u1",
    release_date="2020 (exact day unavailable in the official product metadata)",
    official_source_url="https://land.copernicus.eu/en/products/corine-land-cover/clc-2012",
    availability_evidence_url=_CLC_RELEASE_LINEAGE_URL,
    licence_or_terms_reference=_CLC_LICENCE,
    access_date="2026-08-04",
    raw_path="data/raw/clc/u2018_clc2012_v2020_20u1_geoPackage.zip",
    filename="u2018_clc2012_v2020_20u1_geoPackage.zip",
    sha256=None,
    crs="EPSG:3035",
    coverage="Europe, including mainland Portugal",
    format="GeoPackage in ZIP",
    class_code_field="Code_12",
    class_mapping=_CLC_CLASS_MAPPING,
    validation_status=(
        "official revised package identified; local acquisition is pending authenticated "
        "Copernicus Land Monitoring Service access"
    ),
    catalogue_dataset_uid="a5ee71470be04d66bcff498f94ceb5dc",
    catalogue_file_id="2c674919-0baf-44d6-9c13-a0a585cbe931",
)

CLC_2018_V2020_20U1 = ClcRawRecord(
    key="clc_2018_v2020_20u1",
    reference_year=2018,
    release_id="V2020_20u1",
    release_date="2020 (exact day unavailable in the preserved official metadata)",
    official_source_url="https://land.copernicus.eu/en/products/corine-land-cover/clc2018",
    availability_evidence_url=_CLC_RELEASE_LINEAGE_URL,
    licence_or_terms_reference=_CLC_LICENCE,
    access_date="2026-08-04",
    raw_path="data/raw/clc/u2018_clc2018_v2020_20u1_geoPackage.zip",
    filename="u2018_clc2018_v2020_20u1_geoPackage.zip",
    sha256="AC302982BE6EA027762CC1973123B452157B0C4AD536BB32167C486448316492",
    crs="EPSG:3035",
    coverage="Europe; validated mainland Portugal interim derivative",
    format="GeoPackage in ZIP",
    class_code_field="Code_18",
    class_mapping=_CLC_CLASS_MAPPING,
    validation_status=(
        "raw ZIP checksum and CRC validated; mainland derivative has 54,191 valid, non-empty "
        "MultiPolygon features and 42 valid CLC codes"
    ),
)

CLC_GOVERNED_RELEASES = {
    "2015": CLC_2006_V2020_20U1,
    "2016-2018": CLC_2012_V2020_20U1,
    "2019-2024": CLC_2018_V2020_20U1,
}

CLC_RELEASE_LINEAGE_EVIDENCE = EvidenceRecord(
    key="clc_release_lineage",
    official_source_url=_CLC_RELEASE_LINEAGE_URL,
    access_date="2026-08-04",
    raw_path="data/raw/clc/evidence/clc_release_lineage.pdf",
    filename="clc_release_lineage.pdf",
    sha256="CBFF53799AD7A73AEB3A83C67DBB5214C3D3D4FEBAD019E5B3B723D071A69941",
)
CLC_COUNTRY_COVERAGE_EVIDENCE = EvidenceRecord(
    key="clc_country_coverage_v20u1",
    official_source_url=(
        "https://land.copernicus.eu/en/technical-library/"
        "clc-country-coverage-1990-2018-v20u1/@@download/file"
    ),
    access_date="2026-08-04",
    raw_path="data/raw/clc/evidence/clc_country_coverage_v20u1.pdf",
    filename="clc_country_coverage_v20u1.pdf",
    sha256="5A265ADE38795CF486D839F31CCC8F423DDEC685F2D1B802B748A7A47CF68D7D",
)
CLC_NOMENCLATURE_EVIDENCE = EvidenceRecord(
    key="clc_nomenclature_guidelines",
    official_source_url=(
        "https://land.copernicus.eu/en/technical-library/"
        "clc-illustrated-nomenclature-guidelines/@@download/file"
    ),
    access_date="2026-08-04",
    raw_path="data/raw/clc/evidence/clc_nomenclature_guidelines.pdf",
    filename="clc_nomenclature_guidelines.pdf",
    sha256="8D69D31993481AA334E5391F717EB27558A5290AA039980D06FC5E937CC7F325",
)

ERA5_LAND_2023_JJAS_PILOT = Era5LandRawRecord(
    key="era5_land_2023_jjas_mainland_portugal",
    dataset_id="reanalysis-era5-land-monthly-means",
    official_source_url="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means",
    licence_or_terms_reference="CDS dataset terms accepted by the account holder before retrieval.",
    retrieval_date="2026-08-04",
    acquisition_method="CDS API retrieval",
    raw_path="data/raw/climate/era5_land/era5_land_monthly_jjas_2023_mainland_portugal.grib",
    filename="era5_land_monthly_jjas_2023_mainland_portugal.grib",
    sha256="333C9C63C810F44522A42DCC8654B0CE32C4895D62D4C79C2583244B07B83C08",
    product_type="monthly_averaged_reanalysis",
    year=2023,
    months=("06", "07", "08", "09"),
    time="00:00",
    variables=("2m_temperature", "total_precipitation", "volumetric_soil_water_layer_1"),
    area_north_west_south_east=(42.2, -9.6, 36.8, -6.0),
    data_format="grib",
    validation_facts=Era5LandValidationFacts(
        grid_shape=(4, 55, 37),
        months=("06", "07", "08", "09"),
        grib_short_names=("2t", "tp", "swvl1"),
        missing_value_counts=(("2t", 1928), ("tp", 1928), ("swvl1", 1928)),
        units=(("2t", "K"), ("tp", "m"), ("swvl1", "m**3 m**-3")),
        step_types=(("2t", "avgid"), ("tp", "avgad"), ("swvl1", "avgua")),
        step_ranges=(("2t", "1-24"), ("tp", "0-24"), ("swvl1", "0")),
        precipitation_status="blocked-known-upstream-issue",
        validation_note=(
            "The official ECMWF ERA5-Land documentation marks monthly accumulated variables "
            "from September 2022 through February 2024 as incorrect. The raw file remains an "
            "immutable pilot artifact, but its precipitation must not enter the national panel."
        ),
    ),
)

_ERA5_TRAINING_SHA256 = {
    2015: "6EDF9352FD95A0BBC5A404BDB0BED73309A01763E424B501CB21FB4E459C1692", 2016: "594C17D2CE2E4BF71D06F38CC6628993DC053FE74240383B25ACB78A98BF90FA",
    2017: "DD4B37392C445A0C94AFE62853CC3AA0A23DF4B34076EE788EC230158220070C", 2018: "93AF3DE52CD3F3C88547C680D0D1431638877C1CD11E4E98149E0744A9D3CED4",
    2019: "267FBC7544C6505D9221499B3AD7A3C3EB587267BA4DDCA94D713BE9CD45513C", 2020: "7FC86BCE3358FE95C63670167ADC3AC9A73AC60C39BC9C66E806AB9E7EA94060",
    2021: "47CCEB82F8322DFD92ECC3497A10467E80E13DCDB6AE8A7F9C802561611EE2F5",
}
ERA5_LAND_TRAINING_ARCHIVES = {
    year: Era5LandRawRecord(f"era5_land_{year}_jjas_mainland_portugal", "reanalysis-era5-land-monthly-means", "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means", "CDS dataset terms accepted by the account holder before retrieval.", "2026-08-04", "CDS API retrieval", f"data/raw/climate/era5_land/era5_land_monthly_jjas_{year}_mainland_portugal.grib", f"era5_land_monthly_jjas_{year}_mainland_portugal.grib", checksum, "monthly_averaged_reanalysis", year, ("06","07","08","09"), "00:00", ("2m_temperature","total_precipitation","volumetric_soil_water_layer_1"), (42.2,-9.6,36.8,-6.0), "grib", Era5LandValidationFacts((4,55,37),("06","07","08","09"),("2t","tp","swvl1"),()))
    for year, checksum in _ERA5_TRAINING_SHA256.items()
}


def _era5_full_scope_record(
    year: int,
    checksum: str,
    *,
    precipitation_step_type: str,
    precipitation_step_range: str,
    precipitation_status: str,
    validation_note: str,
) -> Era5LandRawRecord:
    """Create one raw full-scope ERA5-Land record with explicit GRIB semantics."""
    filename = f"era5_land_monthly_jjas_{year}_mainland_portugal.grib"
    return Era5LandRawRecord(
        key=f"era5_land_{year}_jjas_mainland_portugal",
        dataset_id="reanalysis-era5-land-monthly-means",
        official_source_url="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means",
        licence_or_terms_reference="Copernicus Climate Data Store CC-BY licence and dataset terms.",
        retrieval_date="2026-08-04",
        acquisition_method="CDS API retrieval",
        raw_path=f"data/raw/climate/era5_land/{filename}",
        filename=filename,
        sha256=checksum,
        product_type="monthly_averaged_reanalysis",
        year=year,
        months=("06", "07", "08", "09"),
        time="00:00",
        variables=("2m_temperature", "total_precipitation", "volumetric_soil_water_layer_1"),
        area_north_west_south_east=(42.2, -9.6, 36.8, -6.0),
        data_format="grib",
        validation_facts=Era5LandValidationFacts(
            grid_shape=(4, 55, 37),
            months=("06", "07", "08", "09"),
            grib_short_names=("2t", "tp", "swvl1"),
            missing_value_counts=(("2t", 1928), ("tp", 1928), ("swvl1", 1928)),
            units=(("2t", "K"), ("tp", "m"), ("swvl1", "m**3 m**-3")),
            step_types=(("2t", "avgid"), ("tp", precipitation_step_type), ("swvl1", "avgua")),
            step_ranges=(("2t", "1-24"), ("tp", precipitation_step_range), ("swvl1", "0")),
            precipitation_status=precipitation_status,
            validation_note=validation_note,
        ),
    )


ERA5_LAND_2022_JJAS = _era5_full_scope_record(
    2022,
    "816B12E0F93F109996AA4208EABEB73E3FF6C3694F3867D0A7603E970802E6F0",
    precipitation_step_type="avgad",
    precipitation_step_range="0-24",
    precipitation_status="blocked-known-upstream-issue",
    validation_note=(
        "The official ECMWF ERA5-Land documentation marks monthly accumulated variables "
        "from September 2022 through February 2024 as incorrect. JJAS 2022 precipitation "
        "must not be used; acquire the documented by-hour-of-day 00:00 replacement."
    ),
)

ERA5_LAND_2024_JJAS = _era5_full_scope_record(
    2024,
    "40A363CD2C265CBB1E0D587F992B638AD96E66DBAF293DB2E3A8ECAA313522E7",
    precipitation_step_type="avgas",
    precipitation_step_range="23-24",
    precipitation_status="validated-post-fix",
    validation_note=(
        "JJAS 2024 is after the official March 2024 fix. Its precipitation GRIB encoding "
        "differs from the older files (avgas, step 23-24) and is intentionally allow-listed."
    ),
)


def _era5_corrected_precipitation_record(year: int, checksum: str) -> Era5LandRawRecord:
    """Register the separate official by-hour-of-day precipitation workaround."""
    filename = (
        "era5_land_monthly_by_hour_00_jjas_total_precipitation_"
        f"{year}_mainland_portugal.grib"
    )
    return Era5LandRawRecord(
        key=f"era5_land_{year}_jjas_corrected_precipitation",
        dataset_id="reanalysis-era5-land-monthly-means",
        official_source_url="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means",
        licence_or_terms_reference="Copernicus Climate Data Store CC-BY licence and dataset terms.",
        retrieval_date="2026-08-04",
        acquisition_method="CDS API retrieval using the official by-hour-of-day workaround",
        raw_path=f"data/raw/climate/era5_land/{filename}",
        filename=filename,
        sha256=checksum,
        product_type="monthly_averaged_reanalysis_by_hour_of_day",
        year=year,
        months=("06", "07", "08", "09"),
        time="00:00",
        variables=("total_precipitation",),
        area_north_west_south_east=(42.2, -9.6, 36.8, -6.0),
        data_format="grib",
        validation_facts=Era5LandValidationFacts(
            grid_shape=(4, 55, 37),
            months=("06", "07", "08", "09"),
            grib_short_names=("tp",),
            missing_value_counts=(("tp", 1928),),
            units=(("tp", "m"),),
            step_types=(("tp", "avgas"),),
            step_ranges=(("tp", "23-24"),),
            stream="mnth",
            precipitation_status="validated-official-workaround",
            validation_note=(
                "Separate immutable precipitation-only replacement retrieved with "
                "monthly_averaged_reanalysis_by_hour_of_day at 00:00. It replaces only "
                "the affected precipitation field; temperature and soil water remain in "
                "the original annual GRIB."
            ),
        ),
    )


ERA5_LAND_2022_CORRECTED_PRECIPITATION = _era5_corrected_precipitation_record(
    2022,
    "7AAF9EADA365270AF5F0876C64635F30532E1FD52C961369F82040EA6B670B3B",
)
ERA5_LAND_2023_CORRECTED_PRECIPITATION = _era5_corrected_precipitation_record(
    2023,
    "726B7F239862AF6A9011E77617741D344ACE040B8D5DF648336FAEAF7E67D511",
)
ERA5_LAND_PRECIPITATION_CORRECTIONS = {
    2022: ERA5_LAND_2022_CORRECTED_PRECIPITATION,
    2023: ERA5_LAND_2023_CORRECTED_PRECIPITATION,
}

ERA5_LAND_FULL_SCOPE_ARCHIVES = {
    **ERA5_LAND_TRAINING_ARCHIVES,
    2022: ERA5_LAND_2022_JJAS,
    2023: ERA5_LAND_2023_JJAS_PILOT,
    2024: ERA5_LAND_2024_JJAS,
}


_COP_DEM_BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com"
_COP_DEM_TILE_SHA256 = {
    "N36_00_W008_00": "C22117319EC62455978EA2DB4A53CCBE3FB8242F8B06751E0203D244A7777C4B",
    "N36_00_W009_00": "C0263D579D3655CD5C09C20C9E99B3A8888951CE066F2FBD96D73BE4260C649A",
    "N37_00_W008_00": "2D9B199976C8C899A2264AA360DFE2451E54DDEC10C814F6029B7EF0549966F3",
    "N37_00_W009_00": "A3EB9F2D344CF407E0DAC80808E2EF4F5D3452E4BA8B00C8D1D1AA274C23D6DF",
    "N38_00_W007_00": "AADEE74AAD31B67BC4987C3BACFDAF812F855AE45F813CB03F8633FC44239E09",
    "N38_00_W008_00": "F3CB8C992C4975863CD2204BD15B88ED16A5C383B10A602FE927B53BF327A917",
    "N38_00_W009_00": "EA19DC693D73F638A9D50A12E108C211EA39C0BE775D252B45F96DD38066BA9A",
    "N38_00_W010_00": "5679589263F12D21ECE43C475FD7FE17FB69854B41E513CB9AEE25C9441D1C9F",
    "N39_00_W007_00": "67E034CC87CD1FECFBBD5FCE631CBE9EFA67F2407E582AAAA064D4F9DF80903A",
    "N39_00_W008_00": "9E598ACA06F934568FFBDD142A02BB1DF9B476973AAD3C6D23A7C32C77902419",
    "N39_00_W009_00": "1D57C2D490D68FF64583B54A3297F7C0934A66908C44BFC25C9AAB9576F58412",
    "N39_00_W010_00": "D9EAE6DFB209711E76327DEBB86F5F577F41A5946FB14469E8625E337E7E150B",
    "N40_00_W007_00": "BAB932F240C66B54FA5C2C314C3E1F4C222212A06CDF03EDAE298D5447E6ECED",
    "N40_00_W008_00": "BFEE8BBB9A2DB0784BD25ED1B27AB656B2CB30E8BBED47CD116ABC0212DE7BB5",
    "N40_00_W009_00": "CD2751FBF2EC30FBB06A7E65D6DC1EDA749B9B01D433ED275DF2453B897FA108",
    "N41_00_W007_00": "BBAD4C516282421B4CC5F2E1E243462613897827206FD79B60A1C7B6627125C9",
    "N41_00_W008_00": "860FB53B25E4EBC2A519458E8E457211E808C7F0F10D80A3B0DC4D4C03E22715",
    "N41_00_W009_00": "122E7F63F33715394BC44F792BEF58075CF8D6ADF7115D7A49605D427CE3BD24",
    "N42_00_W007_00": "416F52ED4A34068517AD4FE7D20E8142CE10687D425AE3115C58D6E422C03A8F",
    "N42_00_W008_00": "6F9EDB2498C2B09380CFB242E70070D75895FCCA5C6F415B31E14AC5692F639E",
    "N42_00_W009_00": "0EF055AE8C70EE79DBD642CB21A07EC5F7591A5390C69227B7B8E56805982658",
}


def _cop_dem_tile_record(tile_id: str, checksum: str) -> CopDemTileRecord:
    product = f"Copernicus_DSM_COG_10_{tile_id}_DEM"
    filename = f"{product}.tif"
    return CopDemTileRecord(
        tile_id=tile_id,
        official_source_url=f"{_COP_DEM_BASE_URL}/{product}/{filename}",
        raw_path=f"data/raw/terrain/copernicus_dem_glo30_2021/{filename}",
        filename=filename,
        sha256=checksum,
    )


COP_DEM_GLO30_TILES = {
    tile_id: _cop_dem_tile_record(tile_id, checksum)
    for tile_id, checksum in _COP_DEM_TILE_SHA256.items()
}
COP_DEM_GLO30 = CopDemCollectionRecord(
    key="copernicus_dem_glo30_2021_mainland_portugal_context",
    dataset_name="Copernicus DEM GLO-30 DGED",
    release_id="2021 public release; Copernicus DSM COG 10",
    official_source_url="https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM",
    licence_or_terms_reference=(
        "Copernicus DEM licence: free licence with attribution; see the official collection "
        "page and https://registry.opendata.aws/copernicus-dem/."
    ),
    access_date="2026-08-04",
    acquisition_method="scripted HTTPS retrieval from the official public Copernicus DEM bucket",
    coverage_requirement=(
        "CAOP 2025 mainland boundary buffered outward by 2,000 m in EPSG:3763; WGS84 bounds "
        "(-9.5402460460, 36.9436980978, -6.1651935023, 42.1723150969)"
    ),
    crs="EPSG:4326",
    resolution="1 arc-second (3600 x 3600 cells per 1-degree tile; approximately 30 m)",
    format="single-band float32 cloud-optimized GeoTIFF",
    tile_ids=tuple(COP_DEM_GLO30_TILES),
    ocean_no_source_tiles=("N37_00_W010_00",),
    coastal_data_rule=(
        "The official distribution omits ocean-only tiles. Future slope processing must mask "
        "to CAOP mainland land and exclude ocean-side values before the 2 km aggregation; it "
        "must not interpret numeric coastal/ocean elevations as mainland terrain."
    ),
)
