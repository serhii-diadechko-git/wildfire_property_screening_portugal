"""Fail-closed publication-date audit for a prospective annual forecast.

This standalone gate does not change the legacy 2026 scoring engine. Passing
it is necessary but does not certify provider receipts or model usefulness.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.forecast_review import sha256


def utc_time(value: str) -> datetime:
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.tzinfo is None:
        raise ValueError("Timestamps must have an explicit timezone")
    return date.astimezone(timezone.utc)


def check_availability(manifest: dict, root: Path, as_of: datetime) -> dict:
    """Check actual files, release/acquisition evidence, years and annual scope.

    Each input record names one immutable file (a source may have many files).
    Empty/unknown dates fail; a historical reference year is not a release date.
    """
    problems = []
    if as_of.tzinfo is None:
        raise ValueError("as_of must include timezone")
    year = int(manifest["forecast_year"])
    issue = datetime(year - 1, 12, 31, 12, tzinfo=timezone.utc)
    cutoff = datetime(year - 1, 12, 30, 23, 59, 59, tzinfo=timezone.utc)
    if manifest.get("issue_at") != issue.isoformat() or manifest.get("input_cutoff") != cutoff.isoformat():
        problems.append("Issue/cutoff must match the pre-year annual protocol")
    if manifest.get("latest_training_outcome_year") != year - 2:
        problems.append("Training must end at outcome Y-2 under this protocol")
    if manifest.get("predictor_year") != year - 1:
        problems.append("Scoring predictor year must be Y-1")
    if as_of > issue:
        problems.append("Issue date has passed: cannot certify an on-time prospective issue retrospectively")
    requirements = {"icnf": set(range(2000, year - 1)), "era5_land": set(range(2010, year)),
                    "clc": {2006, 2012, 2018}, "terrain": set(), "grid": set()}
    covered = {key: set() for key in requirements}
    present = set()
    seen_paths = set()
    records = manifest.get("inputs", [])
    for i, record in enumerate(records):
        label = f"input {i}: {record.get('source', 'unknown')}"
        source = record.get("source")
        if source not in requirements:
            problems.append(f"{label}: unsupported source")
            continue
        present.add(source)
        years = record.get("reference_years", [])
        if not isinstance(years, list) or any(type(y) is not int for y in years):
            problems.append(f"{label}: reference_years must be integer years")
            continue
        covered[source].update(years)
        if not record.get("version") or not record.get("release_evidence_url"):
            problems.append(f"{label}: missing version or publication evidence")
        released = None
        try:
            released = utc_time(record["available_at"])
            acquired = utc_time(record["acquired_at"])
            if released > min(cutoff, as_of) or acquired > min(cutoff, as_of):
                problems.append(f"{label}: source not available and acquired by cutoff/as-of")
            if acquired < released:
                problems.append(f"{label}: acquisition predates stated publication")
        except (ValueError, KeyError, TypeError, AttributeError):
            problems.append(f"{label}: unknown or invalid publication/acquisition timestamp")
        if source in ("icnf", "era5_land"):
            if record.get("completed_period") is not True:
                problems.append(f"{label}: incomplete or provisional observation period")
            max_year = year - 2 if source == "icnf" else year - 1
            if not years or max(years) > max_year:
                problems.append(f"{label}: invalid dynamic source years")
            try:
                period_end = utc_time(record["observation_end"])
                expected_end = datetime(max(years), 12 if source == "icnf" else 9,
                                        31 if source == "icnf" else 30, 23, 59, 59, tzinfo=timezone.utc)
                if period_end != expected_end or released is None or period_end >= released:
                    problems.append(f"{label}: observations must finish before publication, with the required full annual/JJAS period")
            except (ValueError, KeyError, TypeError, AttributeError, UnboundLocalError):
                problems.append(f"{label}: invalid observation end")
        path_value = record.get("path", "")
        path = (root / path_value).resolve()
        if not path_value or not path.is_relative_to(root.resolve()) or path_value in seen_paths:
            problems.append(f"{label}: missing, duplicate or non-project file path")
            continue
        seen_paths.add(path_value)
        if not path.is_file() or not record.get("sha256"):
            problems.append(f"{label}: missing file or checksum")
        elif sha256(path).lower() != record["sha256"].lower():
            problems.append(f"{label}: checksum mismatch")
    for source, years in requirements.items():
        if source not in present or not years.issubset(covered[source]):
            problems.append(f"{source}: missing required source/years {sorted(years - covered[source])}")
    return {"forecast_year": year, "assessed_at": as_of.isoformat(),
            "status": "blocked" if problems else "ready_for_model_and_input_validation",
            "issues": problems,
            "limitation": "Provider evidence requires human verification; this gate alone does not publish or certify forecasts."}
