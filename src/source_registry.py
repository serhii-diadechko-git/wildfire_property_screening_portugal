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
    field_names: tuple[str, ...],
) -> SourceRecord:
    """Create one manually acquired, immutable annual ICNF provenance record."""
    filename = f"ardida_{year}.zip"
    return SourceRecord(
        key=f"icnf_{year}",
        dataset_edition_or_year=f"ICNF annual burned areas, {year}",
        official_source_url=_ICNF_URL,
        licence_or_terms_reference=_ICNF_TERMS,
        access_date="2026-08-04",
        acquisition_method="manual browser download",
        raw_path=f"data/raw/wildfire/icnf_burned_areas/{filename}",
        filename=filename,
        expected_sha256=checksum,
        required_members=tuple(f"ardida_{year}{suffix}" for suffix in _ICNF_MEMBERS),
        validation_facts=IcnfValidationFacts(
            feature_count=feature_count,
            non_empty_geometry_count=feature_count,
            invalid_geometry_count=invalid_geometry_count,
            field_names=field_names,
            required_fields=("Ano", "AreaHaSIG"),
        ),
    )


ICNF_2013 = _icnf_record(2013, "0B611EDABEE80665E9FB8EBCBAE4B2792A51EDAC7635ADCCCAA7821BC120A9C2", 3150, 111, ("Ano", "AreaHaSIG"))
ICNF_2014 = _icnf_record(2014, "B10723986742F3F801A9C811495470A2C2D4A1F393BB758334215D1F85C3E57C", 1100, 72, _ICNF_STANDARD_FIELDS)
ICNF_2015 = _icnf_record(2015, "0BA69E168349A39E67E1AF851629DD04E814E071B685DEFE87D31196396845DD", 1651, 83, _ICNF_STANDARD_FIELDS)
ICNF_2016 = _icnf_record(2016, "DAD27A6A87E2AA6D31C07DFE3715FCDAE333CBA08B06C5E91AA54E4CB5841189", 2838, 111, _ICNF_STANDARD_FIELDS)
ICNF_2017 = _icnf_record(2017, "7C44B43278797F58489A88834F3E386DD84C5EE0382F31BE2CC49ABBE0647D64", 2765, 27, _ICNF_STANDARD_FIELDS)
ICNF_2018 = _icnf_record(2018, "8EB051B45F1B675F5357AF4C484A0EC2537CEF27D66BDE08E6826DC658C0A726", 537, 24, _ICNF_STANDARD_FIELDS)
ICNF_2019 = _icnf_record(2019, "2CD7B31CA6992BC388B8228AD3731CC1372D3380535BC504E389747500446296", 1725, 54, _ICNF_STANDARD_FIELDS)
ICNF_2020 = _icnf_record(2020, "D64AD2DE1B02D67B001437AE33FE015979BB5768DFAE2DF64F3A293A66EE3BE9", 1777, 22, _ICNF_STANDARD_FIELDS)
ICNF_2021 = _icnf_record(2021, "75845B062236B6299BEA9B03A666B41725EDD67C9B6D996FFA457FAE2CA19FC4", 918, 1, _ICNF_STANDARD_FIELDS)
ICNF_2022 = _icnf_record(2022, "EDA0BF60B17B5878D6CEF3BC17ECB6B845EA9479241A3138DED23DEA54605382", 1786, 13, ("id",) + _ICNF_STANDARD_FIELDS)

PILOT_ICNF_HISTORY = (
    ICNF_2013, ICNF_2014, ICNF_2015, ICNF_2016, ICNF_2017,
    ICNF_2018, ICNF_2019, ICNF_2020, ICNF_2021, ICNF_2022,
)
PILOT_ICNF_ARCHIVES = {2013: ICNF_2013, 2014: ICNF_2014, 2015: ICNF_2015, 2016: ICNF_2016, 2017: ICNF_2017,
                       2018: ICNF_2018, 2019: ICNF_2019, 2020: ICNF_2020, 2021: ICNF_2021, 2022: ICNF_2022,
                       2024: ICNF_2024}

REGISTERED_SOURCES = {record.key: record for record in (CAOP_2025, *PILOT_ICNF_HISTORY, ICNF_2024)}
