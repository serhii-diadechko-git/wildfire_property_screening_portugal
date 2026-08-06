"""Public, platform-neutral project-run orchestration helpers.

The repository never embeds a personal filesystem path, credential, or raw-data
mirror.  This module turns the existing reusable scripts into a clear project
preflight, validation, and intentionally explicit full-reproduction workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Iterable

from src.paths import PROJECT_ROOT, RAW_DATA_DIR, RUN_LOGS_DIR, project_relative
from src.source_registry import (
    CAOP_2025,
    CLC_2006_V2020_20U1,
    CLC_2012_V2020_20U1,
    CLC_2018_V2020_20U1,
    COP_DEM_GLO30_TILES,
    ERA5_LAND_AVAILABLE_ARCHIVES,
    ERA5_LAND_PRECIPITATION_CORRECTIONS,
    ICNF_2000_2008_COMBINED,
    ICNF_ANNUAL_ARCHIVES,
    ICNF_STRUCTURAL_HAZARD_2020_2030,
)


MANIFEST_PATH = PROJECT_ROOT / "data" / "source_manifest.json"


@dataclass(frozen=True)
class RunStage:
    """One explicit, logged processing step."""

    name: str
    command: tuple[str, ...]
    explanation: str


def load_source_manifest() -> dict[str, object]:
    """Read and minimally validate the public source-access manifest."""
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing public source manifest: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    required = {"manifest_version", "purpose", "raw_data_policy", "sources"}
    missing = required.difference(manifest)
    if missing or not isinstance(manifest["sources"], list):
        raise ValueError(f"Invalid source manifest; missing={sorted(missing)}")
    for source in manifest["sources"]:
        fields = {"key", "provider", "official_url", "terms_url", "access", "redistribution_status"}
        if not fields.issubset(source):
            raise ValueError(f"Source manifest entry is incomplete: {source.get('key', '<unknown>')}")
    return manifest


def _registered_raw_groups() -> dict[str, tuple[Path, ...]]:
    """Return local raw paths required for the current public workflow."""
    icnf = (ICNF_2000_2008_COMBINED, *ICNF_ANNUAL_ARCHIVES.values())
    era5 = (*ERA5_LAND_AVAILABLE_ARCHIVES.values(), *ERA5_LAND_PRECIPITATION_CORRECTIONS.values())
    clc = (CLC_2006_V2020_20U1, CLC_2012_V2020_20U1, CLC_2018_V2020_20U1)
    return {
        "ICNF annual burned areas": tuple(PROJECT_ROOT / record.raw_path for record in icnf),
        "CAOP 2025": (PROJECT_ROOT / CAOP_2025.raw_path,),
        "Copernicus CLC packages": tuple(PROJECT_ROOT / str(record.raw_path) for record in clc if record.raw_path),
        "Copernicus DEM GLO-30 tiles": tuple(PROJECT_ROOT / record.raw_path for record in COP_DEM_GLO30_TILES.values()),
        "ERA5-Land JJAS GRIBs": tuple(PROJECT_ROOT / record.raw_path for record in era5),
        "ICNF structural-hazard raster": (PROJECT_ROOT / ICNF_STRUCTURAL_HAZARD_2020_2030.raw_path,),
    }


def raw_data_preflight() -> dict[str, object]:
    """Check local raw-input presence without opening, downloading, or writing files."""
    manifest = load_source_manifest()
    groups: list[dict[str, object]] = []
    for label, paths in _registered_raw_groups().items():
        missing = [project_relative(path) for path in paths if not path.is_file()]
        groups.append(
            {
                "source_group": label,
                "expected_files": len(paths),
                "present_files": len(paths) - len(missing),
                "missing_files": missing,
                "status": "ready" if not missing else "missing",
            }
        )
    missing_total = sum(len(group["missing_files"]) for group in groups)
    return {
        "manifest_version": manifest["manifest_version"],
        "raw_directory": project_relative(RAW_DATA_DIR),
        "raw_data_is_git_ignored": True,
        "status": "ready" if missing_total == 0 else "blocked_missing_raw_inputs",
        "missing_file_count": missing_total,
        "groups": groups,
    }


def default_reproduction_stages(*, include_qgis: bool) -> tuple[RunStage, ...]:
    """Declare the ordered full rebuild using existing, tested script entrypoints."""
    # Keep the declared plan portable and resolve the invoking interpreter only
    # when a stage is actually launched.
    python = "{python}"
    stages = [
        RunStage("environment", (python, "tests/validate_environment.py"), "Validate pinned packages and the environment notebook."),
        RunStage("source validation", (python, "-m", "unittest", "tests.test_collection_validation", "tests.test_clc_validation", "tests.test_era5_land_validation", "-v"), "Validate registered raw source contracts."),
        RunStage("national panel", (python, "scripts/build_national_panel.py", "--stage", "all"), "Build/reuse bounded national feature components and panel."),
        RunStage("training panel", (python, "scripts/build_extended_training_panel.py", "--stage", "all"), "Build/reuse the labelled 2010-2021 development panel."),
        RunStage("model refit", (python, "scripts/refit_extended_training_models.py"), "Refit the frozen nine-feature candidate and validate only 2020-2021."),
        RunStage("final temporal evaluation", (python, "scripts/run_extended_final_temporal_test.py"), "Run the frozen 2022-2024 temporal comparison."),
        RunStage("model diagnostics", (python, "scripts/build_model_diagnostics.py"), "Build durable final-test regression tables and diagnostic figures."),
        RunStage("operational preparation", (python, "scripts/prepare_operational_forecast.py"), "Build/reuse labelled nine-feature artifacts and validate the forecast cutoff."),
        RunStage("operational score", (python, "scripts/score_operational_forecast.py"), "Create/reuse the target-free 2026 comparative estimate."),
        RunStage("historical screening", (python, "scripts/build_historical_exposure_screening.py", "--validate-existing"), "Validate the separate observed-history screening layer."),
        RunStage("figures", (python, "scripts/build_final_visuals.py"), "Regenerate validated charts and summary visuals."),
    ]
    if include_qgis:
        stages.append(
            RunStage(
                "QGIS projects",
                (python, "scripts/build_qgis_presentation_project.py"),
                "Regenerate the historical QGIS project; requires a Python environment with PyQGIS available.",
            )
        )
    stages.append(
        RunStage("full test suite", (python, "-m", "unittest", "discover", "-s", "tests", "-v"), "Run all repository tests."),
    )
    return tuple(stages)


def _run_stage(stage: RunStage, log_handle) -> dict[str, object]:
    """Run one stage, streaming concise status while keeping full output in a log."""
    command = tuple(sys.executable if item == "{python}" else item for item in stage.command)
    print(f"\n[{stage.name}] {stage.explanation}")
    print("  command:", " ".join(command))
    process = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_handle.write(f"\n## {stage.name}\n\n$ {' '.join(command)}\n\n{process.stdout}\n")
    log_handle.flush()
    summary = process.stdout.strip().splitlines()[-1] if process.stdout.strip() else "no output"
    result = {"stage": stage.name, "return_code": process.returncode, "last_output_line": summary}
    if process.returncode:
        raise RuntimeError(f"Stage '{stage.name}' failed. See the run log for full output.")
    print(f"  completed: {summary}")
    return result


def _output_inventory() -> list[dict[str, object]]:
    """List the important public outputs without assuming they exist."""
    candidates = (
        ("nine-feature model", PROJECT_ROOT / "data/processed/final_model_2010_2024/nine_feature_hurdle.joblib"),
        ("2026 score table", PROJECT_ROOT / "data/processed/operational_forecasts/forecast_2026_scores.parquet"),
        ("2026 QGIS-ready estimate", PROJECT_ROOT / "data/processed/spatial_outputs/estimated_comparative_wildfire_exposure_2026.gpkg"),
        ("historical screening", PROJECT_ROOT / "data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg"),
        ("historical QGIS project", PROJECT_ROOT / "qgis/wildfire_exposure_screening_portugal.qgz"),
        ("2026 QGIS project", PROJECT_ROOT / "qgis/wildfire_exposure_screening_portugal_2026.qgz"),
        ("release validation", PROJECT_ROOT / "reports/validation/project_release_validation.md"),
    )
    return [
        {"name": name, "path": project_relative(path), "exists": path.is_file(), "bytes": path.stat().st_size if path.is_file() else None}
        for name, path in candidates
    ]


def write_run_summary(*, mode: str, preflight: dict[str, object], stages: Iterable[dict[str, object]] = ()) -> Path:
    """Write one local, Git-ignored, human-readable run record."""
    RUN_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RUN_LOGS_DIR / f"project_run_{timestamp}.md"
    lines = [
        "# Project run summary",
        "",
        f"- UTC timestamp: {datetime.now(timezone.utc).isoformat()}",
        f"- Mode: `{mode}`",
        f"- Raw-input preflight: **{preflight['status']}**",
        f"- Missing raw files: {preflight['missing_file_count']}",
        "",
        "## Raw source preflight",
        "",
        "| Source group | Present / expected | Status |",
        "|---|---:|---|",
    ]
    for group in preflight["groups"]:
        lines.append(f"| {group['source_group']} | {group['present_files']} / {group['expected_files']} | {group['status']} |")
    if preflight["missing_file_count"]:
        lines.extend(["", "Missing files are listed in the terminal preflight JSON. Obtain them only from the official sources in `data/source_manifest.json`."])
    if stages:
        lines.extend(["", "## Executed stages", "", "| Stage | Status | Last output line |", "|---|---|---|"])
        for stage in stages:
            status = "passed" if stage["return_code"] == 0 else "failed"
            lines.append(f"| {stage['stage']} | {status} | {stage['last_output_line'].replace('|', '\\|')} |")
    lines.extend(["", "## Output inventory", "", "| Output | Path | Present |", "|---|---|---|"])
    for output in _output_inventory():
        lines.append(f"| {output['name']} | `{output['path']}` | {output['exists']} |")
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "The model output is a continuous comparative estimated burned share for broad 1 km mainland cells. It is not a probability, property-level safety guarantee, insurance estimate, or purchase recommendation. Historical recurrence is a separate observed-evidence context layer.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_reproduction(*, include_qgis: bool = False) -> tuple[Path, tuple[dict[str, object], ...]]:
    """Run the declared full rebuild after raw preflight has succeeded."""
    preflight = raw_data_preflight()
    if preflight["status"] != "ready":
        report = write_run_summary(mode="reproduce_blocked", preflight=preflight)
        raise RuntimeError(f"Raw-input preflight is blocked. Read {project_relative(report)} and data/README.md.")
    RUN_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    detail_log = RUN_LOGS_DIR / f"project_reproduce_{timestamp}.log"
    completed: list[dict[str, object]] = []
    with detail_log.open("w", encoding="utf-8") as log:
        log.write("# Full project reproduction log\n")
        for stage in default_reproduction_stages(include_qgis=include_qgis):
            completed.append(_run_stage(stage, log))
    report = write_run_summary(mode="reproduce", preflight=preflight, stages=completed)
    return report, tuple(completed)
