"""Build the non-predictive historical wildfire-exposure screening layer."""

from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import rasterio
from rasterio.features import rasterize
from rasterio.windows import Window, from_bounds
import shapely

from src.config import SPATIAL
from src.national_panel import BUILD_ROOT as PANEL_BUILD_ROOT, GRID_CATALOG_PATH, GRID_PATH
from src.source_registry import ICNF_STRUCTURAL_HAZARD_2020_2030


ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / "data/interim/historical_exposure_screening"
CORE_BATCH_DIR = BUILD_ROOT / "core_batches"
HAZARD_BATCH_DIR = BUILD_ROOT / "hazard_batches"
OUTPUT_PATH = ROOT / "data/processed/spatial_outputs/historical_residential_wildfire_exposure_screening.gpkg"
OUTPUT_LAYER = "historical_exposure_screening"
METRICS_PATH = ROOT / "reports/validation/historical_exposure_screening_and_icnf_comparison.json"
REPORT_PATH = ROOT / "reports/validation/historical_exposure_screening_and_icnf_comparison.md"
TABLE_DIR = ROOT / "reports/tables"
BAND_TABLE_PATH = TABLE_DIR / "historical_exposure_band_summary.csv"
HAZARD_TABLE_PATH = TABLE_DIR / "icnf_hazard_class_summary.csv"
CROSSTAB_TABLE_PATH = TABLE_DIR / "historical_exposure_band_by_icnf_hazard_class.csv"

EVIDENCE_AS_OF_YEAR = 2025
HISTORY_START_YEAR = 2016
HISTORY_END_YEAR = 2025
HISTORY_YEARS = tuple(range(HISTORY_START_YEAR, HISTORY_END_YEAR + 1))
HISTORY_CONTEXT_COLUMNS = tuple(f"context_{year}" for year in HISTORY_YEARS)
HAZARD_PATH = ROOT / ICNF_STRUCTURAL_HAZARD_2020_2030.raw_path
HAZARD_CLASS_BY_CODE = dict(ICNF_STRUCTURAL_HAZARD_2020_2030.class_mapping)
HAZARD_CLASS_ORDER = ("null", "very_low", "low", "medium", "high", "very_high", "unmatched")
BAND_ORDER = ("lower", "moderate", "higher")
FORBIDDEN_OUTPUT_FIELDS = {
    "predicted_burned_share_next_year",
    "burned_share_next_year",
    "burned_next_year",
    "predicted_probability",
    "predicted_wildfire_probability",
    "outcome_year",
    "recommendation_category",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _catalog() -> dict[str, object]:
    catalog = json.loads(GRID_CATALOG_PATH.read_text(encoding="utf-8"))
    if catalog["cell_count"] != 89_112 or catalog["analysis_crs"] != SPATIAL.analysis_crs:
        raise ValueError("Canonical grid catalogue contract failed")
    return catalog


def _component_path(directory: Path, prefix: str, batch_id: str) -> Path:
    return directory / f"{prefix}_{batch_id}.parquet"


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".parquet.tmp")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary file requires inspection: {temporary}")
    frame.to_parquet(temporary, index=False)
    os.replace(temporary, path)
    path.with_suffix(".parquet.json").write_text(
        json.dumps({"rows": len(frame), "sha256": _sha256(path)}, indent=2),
        encoding="utf-8",
    )


def _validated_existing_batch(path: Path, expected_rows: int) -> pd.DataFrame | None:
    manifest = path.with_suffix(".parquet.json")
    if not path.exists() and not manifest.exists():
        return None
    if not path.exists() or not manifest.exists():
        raise FileExistsError(f"Incomplete restartable batch state: {path}")
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    if metadata["rows"] != expected_rows or metadata["sha256"] != _sha256(path):
        raise ValueError(f"Existing batch validation failed: {path}")
    return pd.read_parquet(path)


def derive_core_batch(batch: dict[str, object]) -> pd.DataFrame:
    """Combine already validated ICNF, CLC 2018 and slope components for one tile."""
    batch_id = str(batch["batch_id"])
    grid = pd.read_parquet(
        ROOT / str(batch["path"]),
        columns=["cell_id", "land_area_m2"],
    )
    icnf = pd.read_parquet(
        PANEL_BUILD_ROOT / "icnf_components" / f"icnf_{batch_id}.parquet",
        columns=["cell_id", *HISTORY_CONTEXT_COLUMNS],
    ).set_index("cell_id")
    clc = pd.read_parquet(
        PANEL_BUILD_ROOT / "clc" / "2018" / f"clc_2018_{batch_id}.parquet"
    ).set_index("cell_id")
    slope = pd.read_parquet(
        PANEL_BUILD_ROOT / "slope" / f"slope_{batch_id}.parquet"
    ).set_index("cell_id")
    cell_ids = grid.cell_id.to_numpy()
    recurrence = icnf.loc[cell_ids, list(HISTORY_CONTEXT_COLUMNS)].sum(axis=1).astype("int8")
    result = pd.DataFrame({
        "cell_id": cell_ids,
        "land_area_m2": grid.land_area_m2.to_numpy(dtype="float64"),
        "fire_years_history_10y_2km": recurrence.to_numpy(dtype="int8"),
        "forest_shrub_share_2km": clc.loc[cell_ids, "forest_shrub_share_2km"].to_numpy(dtype="float64"),
        "mean_slope_2km": slope.loc[cell_ids, "mean_slope_2km"].to_numpy(dtype="float64"),
        "built_up_share": clc.loc[cell_ids, "built_up_share"].to_numpy(dtype="float64"),
    })
    if result.isna().any().any() or not result.cell_id.is_unique:
        raise ValueError(f"Core descriptive component failed for {batch_id}")
    if not result.fire_years_history_10y_2km.between(0, 10).all():
        raise ValueError(f"Historical recurrence range failed for {batch_id}")
    return result


def build_core_batches(progress: Callable[[str], None] = print) -> tuple[pd.DataFrame, dict[str, int]]:
    pieces = []
    created = reused = 0
    for number, batch in enumerate(_catalog()["batches"], start=1):
        path = _component_path(CORE_BATCH_DIR, "core", str(batch["batch_id"]))
        frame = _validated_existing_batch(path, int(batch["row_count"]))
        if frame is None:
            frame = derive_core_batch(batch)
            _atomic_parquet(frame, path)
            created += 1
        else:
            reused += 1
        pieces.append(frame)
        if number == 1 or number % 25 == 0 or number == int(_catalog()["batch_count"]):
            progress(f"Core tile {number}/{_catalog()['batch_count']}: {batch['batch_id']}")
    result = pd.concat(pieces, ignore_index=True).sort_values("cell_id", kind="mergesort").reset_index(drop=True)
    if len(result) != 89_112 or not result.cell_id.is_unique:
        raise ValueError("Assembled core descriptive component lost or duplicated cells")
    return result, {"created": created, "reused": reused}


def recurrence_thresholds(values: pd.Series) -> dict[str, int | float | str]:
    """Use empirical national tertiles of the integer ten-year recurrence count."""
    q33 = float(values.quantile(1 / 3, interpolation="nearest"))
    q67 = float(values.quantile(2 / 3, interpolation="nearest"))
    lower_max = int(q33)
    moderate_max = int(q67)
    if not 0 <= lower_max < moderate_max < 10:
        raise ValueError(f"Recurrence tertiles do not form three useful bands: {q33}, {q67}")
    return {
        "method": "nearest integer empirical 33rd and 67th percentiles across all mainland cells",
        "q33": q33,
        "q67": q67,
        "lower_max": lower_max,
        "moderate_max": moderate_max,
    }


def assign_recurrence_bands(values: pd.Series, thresholds: dict[str, object]) -> pd.DataFrame:
    lower_max = int(thresholds["lower_max"])
    moderate_max = int(thresholds["moderate_max"])
    bands = np.select(
        [values <= lower_max, values <= moderate_max],
        ["lower", "moderate"],
        default="higher",
    )
    notes = {
        "lower": (
            f"0-{lower_max} recorded fire years in the 2 km context during "
            f"{HISTORY_START_YEAR}-{HISTORY_END_YEAR}; lower does not mean safe."
        ),
        "moderate": (
            f"{lower_max + 1}-{moderate_max} recorded fire years in the 2 km context during "
            f"{HISTORY_START_YEAR}-{HISTORY_END_YEAR}."
        ),
        "higher": (
            f"{moderate_max + 1}-10 recorded fire years in the 2 km context during "
            f"{HISTORY_START_YEAR}-{HISTORY_END_YEAR}."
        ),
    }
    return pd.DataFrame({
        "historical_exposure_band": bands,
        "historical_exposure_note": pd.Series(bands).map(notes),
    })


def validate_hazard_source() -> dict[str, object]:
    record = ICNF_STRUCTURAL_HAZARD_2020_2030
    if _sha256(HAZARD_PATH) != record.sha256:
        raise ValueError("Official ICNF hazard raster checksum changed")
    with rasterio.open(HAZARD_PATH) as source:
        facts = {
            "driver": source.driver,
            "crs": str(source.crs),
            "width": source.width,
            "height": source.height,
            "resolution_metres": list(source.res),
            "bounds": list(source.bounds),
            "nodata": source.nodata,
            "dtype": source.dtypes[0],
        }
    expected = (record.crs, *record.dimensions, record.nodata_value)
    observed = (facts["crs"], facts["width"], facts["height"], facts["nodata"])
    if observed != expected:
        raise ValueError(f"Official ICNF hazard raster contract changed: {observed} != {expected}")
    return facts | {"sha256": record.sha256}


def derive_hazard_batch(batch: dict[str, object], source: rasterio.io.DatasetReader) -> pd.DataFrame:
    """Assign predominant valid 25 m official class within each mainland cell polygon."""
    batch_id = str(batch["batch_id"])
    grid = pd.read_parquet(
        ROOT / str(batch["path"]),
        columns=["cell_id", "land_geometry_wkb"],
    )
    geometries = shapely.from_wkb(grid.land_geometry_wkb.to_numpy())
    raw_window = from_bounds(*batch["bounds_epsg3763"], transform=source.transform)
    window = raw_window.round_offsets().round_lengths().intersection(
        Window(0, 0, source.width, source.height)
    )
    hazard = source.read(1, window=window)
    transform = source.window_transform(window)
    labels = rasterize(
        ((geometry, index + 1) for index, geometry in enumerate(geometries)),
        out_shape=hazard.shape,
        transform=transform,
        fill=0,
        all_touched=False,
        dtype="int32",
    )
    total_land_pixels = np.bincount(labels.ravel(), minlength=len(grid) + 1)[1:]
    valid = (labels > 0) & np.isin(hazard, tuple(HAZARD_CLASS_BY_CODE))
    valid_labels = labels[valid]
    valid_codes = hazard[valid].astype("int16")
    class_counts = np.zeros((len(grid), 6), dtype="int32")
    if len(valid_labels):
        flat_pairs = (valid_labels - 1) * 6 + valid_codes
        class_counts = np.bincount(flat_pairs, minlength=len(grid) * 6).reshape(len(grid), 6)
    valid_pixel_count = class_counts.sum(axis=1)
    maximum = class_counts.max(axis=1)
    # Exact ties select the higher official class and are explicitly logged.
    modal_code = 5 - np.argmax(class_counts[:, ::-1], axis=1)
    tied = (class_counts == maximum[:, None]).sum(axis=1) > 1
    unmatched = valid_pixel_count == 0
    modal_code = modal_code.astype("int16")
    modal_code[unmatched] = -1
    class_name = pd.Series(modal_code).map(HAZARD_CLASS_BY_CODE).fillna("unmatched")
    coverage_share = np.divide(
        valid_pixel_count,
        total_land_pixels,
        out=np.zeros(len(grid), dtype="float64"),
        where=total_land_pixels > 0,
    )
    modal_share = np.divide(
        maximum,
        valid_pixel_count,
        out=np.zeros(len(grid), dtype="float64"),
        where=valid_pixel_count > 0,
    )
    return pd.DataFrame({
        "cell_id": grid.cell_id,
        "official_icnf_hazard_code": modal_code,
        "official_icnf_hazard_class": class_name,
        "icnf_valid_pixel_count": valid_pixel_count.astype("int32"),
        "icnf_hazard_coverage_share": coverage_share,
        "icnf_modal_class_share": modal_share,
        "icnf_modal_tie": tied & ~unmatched,
    })


def build_hazard_batches(progress: Callable[[str], None] = print) -> tuple[pd.DataFrame, dict[str, int]]:
    validate_hazard_source()
    pieces = []
    created = reused = 0
    catalog = _catalog()
    with rasterio.open(HAZARD_PATH) as source:
        for number, batch in enumerate(catalog["batches"], start=1):
            path = _component_path(HAZARD_BATCH_DIR, "hazard", str(batch["batch_id"]))
            frame = _validated_existing_batch(path, int(batch["row_count"]))
            if frame is None:
                frame = derive_hazard_batch(batch, source)
                _atomic_parquet(frame, path)
                created += 1
            else:
                reused += 1
            pieces.append(frame)
            if number == 1 or number % 25 == 0 or number == int(catalog["batch_count"]):
                progress(f"Hazard tile {number}/{catalog['batch_count']}: {batch['batch_id']}")
    result = pd.concat(pieces, ignore_index=True).sort_values("cell_id", kind="mergesort").reset_index(drop=True)
    if len(result) != 89_112 or not result.cell_id.is_unique:
        raise ValueError("Assembled official hazard component lost or duplicated cells")
    return result, {"created": created, "reused": reused}


def assemble_screening_table(core: pd.DataFrame, hazard: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    thresholds = recurrence_thresholds(core.fire_years_history_10y_2km)
    bands = assign_recurrence_bands(core.fire_years_history_10y_2km, thresholds)
    result = core.drop(columns="land_area_m2").copy()
    result.insert(1, "evidence_as_of_year", np.int16(EVIDENCE_AS_OF_YEAR))
    result.insert(2, "history_start_year", np.int16(HISTORY_START_YEAR))
    result.insert(3, "history_end_year", np.int16(HISTORY_END_YEAR))
    result.insert(5, "historical_exposure_band", bands.historical_exposure_band)
    result.insert(6, "historical_exposure_note", bands.historical_exposure_note)
    result = result.merge(hazard, on="cell_id", how="left", validate="one_to_one")
    result["icnf_source_version"] = ICNF_STRUCTURAL_HAZARD_2020_2030.source_version
    result["evidence_status"] = np.where(
        result.official_icnf_hazard_class.eq("unmatched"),
        "official_hazard_unmatched",
        "complete_descriptive_evidence",
    )
    if result.isna().any().any():
        raise ValueError("Unexpected missing values in assembled historical screening attributes")
    return result.sort_values("cell_id", kind="mergesort").reset_index(drop=True), thresholds


def _summary_tables(table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    total = len(table)
    bands = (
        table.groupby("historical_exposure_band", observed=True).size()
        .reindex(BAND_ORDER, fill_value=0).rename("cell_count").reset_index()
    )
    bands["share_of_cells"] = bands.cell_count / total
    hazard = (
        table.groupby("official_icnf_hazard_class", observed=True).size()
        .reindex(HAZARD_CLASS_ORDER, fill_value=0).rename("cell_count").reset_index()
    )
    hazard["share_of_cells"] = hazard.cell_count / total
    cross = (
        table.groupby(["historical_exposure_band", "official_icnf_hazard_class"], observed=True)
        .size().rename("cell_count").reset_index()
    )
    cross["share_of_all_cells"] = cross.cell_count / total
    band_totals = cross.groupby("historical_exposure_band").cell_count.transform("sum")
    cross["share_within_historical_band"] = cross.cell_count / band_totals
    return bands, hazard, cross


def _publish_output(table: pd.DataFrame) -> None:
    geometry = pyogrio.read_dataframe(GRID_PATH, columns=["cell_id"])
    if len(geometry) != 89_112 or not geometry.cell_id.is_unique or str(geometry.crs) != SPATIAL.analysis_crs:
        raise ValueError("Canonical geometry lookup contract failed")
    output = geometry[["cell_id", "geometry"]].merge(table, on="cell_id", validate="one_to_one")
    output = gpd.GeoDataFrame(output, geometry="geometry", crs=SPATIAL.analysis_crs)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_PATH.with_name(OUTPUT_PATH.stem + ".tmp.gpkg")
    if temporary.exists():
        raise FileExistsError(f"Stale temporary GeoPackage requires inspection: {temporary}")
    pyogrio.write_dataframe(output, temporary, layer=OUTPUT_LAYER, driver="GPKG")
    os.replace(temporary, OUTPUT_PATH)


def validate_output(expected: pd.DataFrame) -> dict[str, object]:
    info = pyogrio.read_info(OUTPUT_PATH, layer=OUTPUT_LAYER)
    output = pyogrio.read_dataframe(OUTPUT_PATH, layer=OUTPUT_LAYER)
    fields = list(info["fields"])
    forbidden = sorted(FORBIDDEN_OUTPUT_FIELDS.intersection(fields))
    predictive_tokens = ("predict", "probab", "buy", "recommend", "outcome", "target")
    suspicious = sorted(field for field in fields if any(token in field.lower() for token in predictive_tokens))
    if forbidden or suspicious:
        raise ValueError(f"Buyer-facing layer contains forbidden/predictive fields: {forbidden + suspicious}")
    if (
        info["features"] != 89_112
        or str(info["crs"]) != SPATIAL.analysis_crs
        or info["geometry_type"] not in ("Polygon", "MultiPolygon")
        or output.cell_id.isna().any()
        or not output.cell_id.is_unique
        or output.geometry.is_empty.any()
        or (~output.geometry.is_valid).any()
    ):
        raise ValueError("Historical screening GeoPackage spatial contract failed")
    observed = output.drop(columns="geometry").sort_values("cell_id", kind="mergesort").reset_index(drop=True)
    pd.testing.assert_frame_equal(
        expected.reset_index(drop=True),
        observed[expected.columns].reset_index(drop=True),
        check_exact=True,
        check_dtype=False,
    )
    return {
        "path": OUTPUT_PATH.relative_to(ROOT).as_posix(),
        "layer": OUTPUT_LAYER,
        "crs": str(info["crs"]),
        "feature_count": int(info["features"]),
        "geometry_type": info["geometry_type"],
        "fields": fields,
        "missing_cell_id": 0,
        "empty_geometries": 0,
        "invalid_geometries": 0,
        "forbidden_fields": forbidden,
        "predictive_field_names": suspicious,
        "sha256": _sha256(OUTPUT_PATH),
    }


def verify_analytical_rerun(expected: pd.DataFrame) -> dict[str, object]:
    """Recompute every bounded source batch without writing and compare exact attributes."""
    core_parts = []
    hazard_parts = []
    catalog = _catalog()
    with rasterio.open(HAZARD_PATH) as source:
        for batch in catalog["batches"]:
            core_parts.append(derive_core_batch(batch))
            hazard_parts.append(derive_hazard_batch(batch, source))
    rerun_core = pd.concat(core_parts, ignore_index=True).sort_values("cell_id", kind="mergesort").reset_index(drop=True)
    rerun_hazard = pd.concat(hazard_parts, ignore_index=True).sort_values("cell_id", kind="mergesort").reset_index(drop=True)
    rerun, thresholds = assemble_screening_table(rerun_core, rerun_hazard)
    pd.testing.assert_frame_equal(expected, rerun, check_exact=True, check_dtype=True)
    return {
        "all_275_batches_recomputed_without_writes": True,
        "analytical_values_exact": True,
        "row_order_exact": True,
        "thresholds_exact": thresholds,
        "byte_identical_gpkg_not_required": True,
    }


def _write_reports(
    table: pd.DataFrame,
    thresholds: dict[str, object],
    validation: dict[str, object],
    rerun: dict[str, object],
    hazard_facts: dict[str, object],
    component_status: dict[str, object],
) -> dict[str, object]:
    bands, hazard, cross = _summary_tables(table)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    bands.to_csv(BAND_TABLE_PATH, index=False)
    hazard.to_csv(HAZARD_TABLE_PATH, index=False)
    cross.to_csv(CROSSTAB_TABLE_PATH, index=False)

    comparable = table.loc[~table.official_icnf_hazard_class.eq("unmatched")].copy()
    comparable["official_broad_band"] = comparable.official_icnf_hazard_class.map({
        "null": "lower", "very_low": "lower", "low": "lower",
        "medium": "moderate", "high": "higher", "very_high": "higher",
    })
    comparable["same_broad_level"] = comparable.historical_exposure_band.eq(comparable.official_broad_band)
    notable = (
        cross.sort_values("cell_count", ascending=False, kind="mergesort").head(10)
        .to_dict(orient="records")
    )
    metrics = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "historical_descriptive_wildfire_exposure_screening_not_prediction",
        "evidence_snapshot": {
            "evidence_as_of_year": EVIDENCE_AS_OF_YEAR,
            "history_start_year": HISTORY_START_YEAR,
            "history_end_year": HISTORY_END_YEAR,
            "history_years": list(HISTORY_YEARS),
            "available_validated_icnf_years": list(range(2005, 2026)),
        },
        "thresholds": thresholds,
        "output_validation": validation,
        "deterministic_rerun": rerun,
        "hazard_source": {
            "record": ICNF_STRUCTURAL_HAZARD_2020_2030.__dict__,
            "raster_validation": hazard_facts,
            "spatial_method": (
                "Predominant valid 25 m hazard class by pixel-centre area within each mainland-masked "
                "1 km cell; exact modal ties select the higher official class."
            ),
        },
        "component_status": component_status,
        "band_summary": bands.to_dict(orient="records"),
        "hazard_summary": hazard.to_dict(orient="records"),
        "cross_tabulation": cross.to_dict(orient="records"),
        "official_hazard_unmatched_cells": int((table.official_icnf_hazard_class == "unmatched").sum()),
        "modal_tie_cells": int(table.icnf_modal_tie.sum()),
        "same_broad_level_count": int(comparable.same_broad_level.sum()),
        "same_broad_level_share_of_matched": float(comparable.same_broad_level.mean()),
        "notable_largest_combinations": notable,
        "no_predictive_claim": True,
    }
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    band_rows = "\n".join(
        f"| {row.historical_exposure_band} | {int(row.cell_count):,} | {row.share_of_cells:.2%} |"
        for row in bands.itertuples(index=False)
    )
    hazard_rows = "\n".join(
        f"| {row.official_icnf_hazard_class} | {int(row.cell_count):,} | {row.share_of_cells:.2%} |"
        for row in hazard.itertuples(index=False)
    )
    cross_pivot = pd.crosstab(
        table.historical_exposure_band,
        table.official_icnf_hazard_class,
    ).reindex(index=BAND_ORDER, columns=HAZARD_CLASS_ORDER, fill_value=0)
    cross_header = "| Historical band | " + " | ".join(HAZARD_CLASS_ORDER) + " |"
    cross_rule = "|---|" + "---:|" * len(HAZARD_CLASS_ORDER)
    cross_rows = "\n".join(
        "| " + band + " | " + " | ".join(f"{int(value):,}" for value in cross_pivot.loc[band]) + " |"
        for band in BAND_ORDER
    )
    REPORT_PATH.write_text(
        f"""# Historical exposure screening and official ICNF comparison

**This output is historical and descriptive, not a prediction, probability, safety guarantee, property recommendation, or validation of the official ICNF map.**

## Evidence snapshot and recurrence bands

The assessment snapshot uses the latest validated observed burned-area year, {EVIDENCE_AS_OF_YEAR}. The primary measure counts the distinct years from {HISTORY_START_YEAR} through {HISTORY_END_YEAR} in which each mainland-masked 2 km context intersected an annual dissolved ICNF burned-area geometry. The repository has validated ICNF annual inputs from 2005 through 2025; only the latest complete ten-year window is used here.

National empirical recurrence tertiles are {thresholds['q33']:.0f} and {thresholds['q67']:.0f} years, producing transparent recurrence-only bands:

- lower: 0-{thresholds['lower_max']} years;
- moderate: {int(thresholds['lower_max']) + 1}-{thresholds['moderate_max']} years;
- higher: {int(thresholds['moderate_max']) + 1}-10 years.

| Historical exposure band | Cells | Share |
|---|---:|---:|
{band_rows}

“Lower historical exposure” does not mean safe. Zero or one recorded fire year does not mean zero wildfire risk. These bands support broad location comparison and shortlisting only.

## Official ICNF hazard comparison

Source: **{ICNF_STRUCTURAL_HAZARD_2020_2030.dataset_name}**, {ICNF_STRUCTURAL_HAZARD_2020_2030.source_version}. The official 25 m EPSG:3763 raster was obtained from the registered ICNF WCS coverage and kept immutable at `{ICNF_STRUCTURAL_HAZARD_2020_2030.raw_path}`.

Each 1 km cell receives the predominant valid official 25 m class by pixel-centre area inside its mainland-land geometry. Exact modal ties select the higher official class and are counted. Cells with no valid official pixel remain `unmatched`; they are never assigned a low class.

| Official ICNF class | Cells | Share |
|---|---:|---:|
{hazard_rows}

### Cross-tabulation (cell counts)

{cross_header}
{cross_rule}
{cross_rows}

For a descriptive orientation only, official null/very-low/low classes were grouped as lower, medium as moderate, and high/very-high as higher. The broad levels coincide for {metrics['same_broad_level_count']:,} matched cells ({metrics['same_broad_level_share_of_matched']:.2%}). This is not an accuracy statistic: the recurrence band measures observed fire history around a cell, while the official map represents structural hazard under its own statutory methodology. Agreement and disagreement are both expected and neither source replaces the other.

## Output and validation

- GeoPackage: `{validation['path']}`
- Layer: `{validation['layer']}`
- CRS: {validation['crs']}
- Features: {validation['feature_count']:,}
- Unmatched official hazard cells: {metrics['official_hazard_unmatched_cells']:,}
- Exact official-class modal ties: {metrics['modal_tie_cells']:,}
- Invalid/empty geometries: 0 / 0
- Forbidden predictive/outcome fields: none
- Deterministic analytical rerun: all 275 bounded batches reproduced exact attributes and ordering

Machine-readable summaries are stored at `{METRICS_PATH.relative_to(ROOT).as_posix()}`, `{BAND_TABLE_PATH.relative_to(ROOT).as_posix()}`, `{HAZARD_TABLE_PATH.relative_to(ROOT).as_posix()}`, and `{CROSSTAB_TABLE_PATH.relative_to(ROOT).as_posix()}`.

## Limitations

- Historical recurrence records observed burned-area intersections, not future probability, ignition likelihood, property damage, evacuation access, or building-level vulnerability.
- A 2 km context is a project screening parameter; the analytical geometry remains the 1 km cell.
- CLC 2018 and static terrain fields provide generalized landscape context and do not describe individual properties.
- The official 25 m hazard raster is summarized to 1 km by predominant valid class, which necessarily removes within-cell detail.
- This layer must not be used as a buy/do-not-buy decision or property-level safety guarantee.
""",
        encoding="utf-8",
    )
    return metrics


def run_historical_exposure_screening(
    *,
    validate_existing: bool = False,
    progress: Callable[[str], None] = print,
) -> dict[str, object]:
    """Build or validate the final historical screening output without panel/model work."""
    hazard_facts = validate_hazard_source()
    core, core_status = build_core_batches(progress)
    hazard, hazard_status = build_hazard_batches(progress)
    table, thresholds = assemble_screening_table(core, hazard)
    if OUTPUT_PATH.exists():
        if not validate_existing:
            raise FileExistsError(
                f"Refusing to overwrite {OUTPUT_PATH}; use --validate-existing for a read-only rerun check"
            )
    else:
        _publish_output(table)
    validation = validate_output(table)
    rerun = verify_analytical_rerun(table)
    return _write_reports(
        table,
        thresholds,
        validation,
        rerun,
        hazard_facts,
        {"core_batches": core_status, "hazard_batches": hazard_status},
    )

