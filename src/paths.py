"""Platform-neutral repository paths used by notebooks and scripts.

No user-specific path is stored in source control.  Every path is resolved
from this module's location inside a cloned repository.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
EXTERNAL_DATA_DIR = DATA_DIR / "external"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
BI_EXPORTS_DIR = REPORTS_DIR / "bi_exports"
TABLES_DIR = REPORTS_DIR / "tables"
VALIDATION_DIR = REPORTS_DIR / "validation"
RUN_LOGS_DIR = REPORTS_DIR / "run_logs"


def project_relative(path: Path) -> str:
    """Return a portable, forward-slash path relative to the repository root."""
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def ensure_output_directories() -> None:
    """Create generated-output directories when they do not exist."""
    for path in (
        INTERIM_DATA_DIR,
        PROCESSED_DATA_DIR,
        FIGURES_DIR,
        BI_EXPORTS_DIR,
        TABLES_DIR,
        VALIDATION_DIR,
        RUN_LOGS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
