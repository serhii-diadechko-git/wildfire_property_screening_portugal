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
)


REGISTERED_SOURCES = {record.key: record for record in (CAOP_2025, ICNF_2024)}
