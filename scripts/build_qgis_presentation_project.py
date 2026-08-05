"""Create and validate the portable QGIS presentation project.

Run this script with the QGIS Python runtime, not the project's virtual
environment.  It reads existing GeoPackages only and never rewrites their data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Python 3.8+ requires dependent DLL locations to be registered explicitly on
# Windows. Keep the handles alive for the process lifetime so the standalone
# PyQGIS runner can import Qt without relying on the caller's current directory.
_QGIS_DLL_HANDLES = []
if os.name == "nt" and os.environ.get("OSGEO4W_ROOT"):
    qgis_root = Path(os.environ["OSGEO4W_ROOT"])
    for relative_path in ("bin", "apps/qt5/bin", "apps/qgis-ltr/bin"):
        dll_path = qgis_root / relative_path
        if dll_path.is_dir():
            _QGIS_DLL_HANDLES.append(os.add_dll_directory(dll_path))

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsApplication,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsFillSymbol,
    QgsLayoutExporter,
    QgsLayoutItemMap,
    QgsLayoutItemPage,
    QgsLayoutItemPicture,
    QgsLayoutItemScaleBar,
    QgsLayoutMeasurement,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsLineSymbol,
    QgsProject,
    QgsPrintLayout,
    QgsRectangle,
    QgsRendererCategory,
    QgsSingleSymbolRenderer,
    QgsUnitTypes,
    QgsVectorLayer,
)


PROJECT_PATH = ROOT / "qgis" / "wildfire_exposure_screening_portugal.qgz"
ASSET_DIR = ROOT / "qgis" / "assets"
FIGURES_DIR = ROOT / "reports" / "figures"
VALIDATION_PATH = ROOT / "reports" / "validation" / "qgis_presentation_project_validation.md"
VALIDATION_JSON_PATH = ROOT / "reports" / "validation" / "qgis_presentation_project_validation.json"

SCREENING_PATH = ROOT / "data" / "processed" / "spatial_outputs" / "historical_residential_wildfire_exposure_screening.gpkg"
SCREENING_LAYER = "historical_exposure_screening"
BOUNDARY_PATH = ROOT / "data" / "processed" / "reference" / "mainland_boundary_caop2025.gpkg"
BOUNDARY_LAYER = "mainland_boundary_caop2025"
ERA5_QA_PATH = ROOT / "data" / "processed" / "spatial_qa" / "era5_land_coastal_fallback_qa.gpkg"
ERA5_QA_LAYER = "era5_coastal_fallback_qa"
SNAPSHOT_PATH = ROOT / "data" / "processed" / "spatial_qa" / "national_panel_snapshot_2024.gpkg"
SNAPSHOT_LAYER = "national_panel_snapshot_2024"

MAP_EXPORTS = {
    "historical": FIGURES_DIR / "historical_wildfire_exposure_screening_mainland_portugal.png",
    "comparison": FIGURES_DIR / "historical_exposure_and_official_icnf_structural_hazard_comparison.png",
}
PDF_EXPORTS = {
    "historical": FIGURES_DIR / "historical_wildfire_exposure_screening_mainland_portugal.pdf",
    "comparison": FIGURES_DIR / "historical_exposure_and_official_icnf_structural_hazard_comparison.pdf",
}

HISTORICAL_STYLE = {
    "lower": ("Lower historical exposure (0–1 years)", "#E9D8A6"),
    "moderate": ("Moderate historical exposure (2–3 years)", "#E69F00"),
    "higher": ("Higher historical exposure (4–10 years)", "#9B2226"),
}
HAZARD_STYLE = {
    "very_low": ("Official very low structural hazard", "#509E2F"),
    "low": ("Official low structural hazard", "#FFE900"),
    "medium": ("Official medium structural hazard", "#E87722"),
    "high": ("Official high structural hazard", "#CB333B"),
    "very_high": ("Official very high structural hazard", "#6F263D"),
    "unmatched": ("Official class unmatched", "#BDBDBD"),
}


def _uri(path: Path, layer: str) -> str:
    return f"{path.as_posix()}|layername={layer}"


def _load(path: Path, layer: str, name: str) -> QgsVectorLayer:
    vector = QgsVectorLayer(_uri(path, layer), name, "ogr")
    if not vector.isValid():
        raise ValueError(f"QGIS could not open {path} layer {layer}")
    if vector.crs().authid() != "EPSG:3763":
        raise ValueError(f"Unexpected CRS for {name}: {vector.crs().authid()}")
    if vector.featureCount() <= 0:
        raise ValueError(f"QGIS layer is unexpectedly empty: {name}")
    return vector


def _fill(color: str, outline: str = "#6A6A6A", width: str = "0.05") -> QgsFillSymbol:
    return QgsFillSymbol.createSimple({"color": color, "outline_color": outline, "outline_width": width})


def _apply_categories(layer: QgsVectorLayer, field: str, specification: dict[str, tuple[str, str]]) -> None:
    categories = [
        QgsRendererCategory(value, _fill(color), label)
        for value, (label, color) in specification.items()
    ]
    layer.setRenderer(QgsCategorizedSymbolRenderer(field, categories))


def _apply_aliases_and_popup(layer: QgsVectorLayer) -> None:
    aliases = {
        "cell_id": "Cell ID",
        "evidence_as_of_year": "Evidence snapshot year",
        "history_start_year": "Historical evidence start year",
        "history_end_year": "Historical evidence end year",
        "fire_years_history_10y_2km": "Recorded fire years, 2016–2025 (2 km context)",
        "historical_exposure_band": "Historical exposure band",
        "historical_exposure_note": "Historical exposure note",
        "official_icnf_hazard_class": "Official ICNF structural hazard (predominant 25 m class)",
        "forest_shrub_share_2km": "Forest/shrub share (2 km context)",
        "mean_slope_2km": "Mean slope (degrees; 2 km context)",
        "built_up_share": "Built-up share (1 km cell)",
        "icnf_source_version": "Official ICNF source version",
        "evidence_status": "Evidence status",
    }
    for field, label in aliases.items():
        index = layer.fields().indexFromName(field)
        if index >= 0:
            layer.setFieldAlias(index, label)
    layer.setMapTipTemplate(
        "<h3>Historical wildfire-exposure screening</h3>"
        "<b>Cell ID:</b> [% \"cell_id\" %]<br>"
        "<b>Evidence:</b> [% \"history_start_year\" %]–[% \"history_end_year\" %]; "
        "recurrence measured in a 2 km context<br>"
        "<b>Recorded fire years:</b> [% \"fire_years_history_10y_2km\" %]<br>"
        "<b>Historical exposure:</b> [% \"historical_exposure_band\" %]<br>"
        "<b>Official ICNF class:</b> [% \"official_icnf_hazard_class\" %]<br>"
        "<b>Forest/shrub share:</b> [% round(\"forest_shrub_share_2km\" * 100, 1) %]%<br>"
        "<b>Mean slope:</b> [% round(\"mean_slope_2km\", 1) %]°<br>"
        "<b>Built-up share:</b> [% round(\"built_up_share\" * 100, 1) %]%<br>"
        "<i>Historical comparative exposure only; not a forecast, safety guarantee, or purchase recommendation.</i>"
    )


def _add_to_group(project: QgsProject, group_name: str, layer: QgsVectorLayer, *, visible: bool = True) -> None:
    root = project.layerTreeRoot()
    group = root.findGroup(group_name)
    if group is None:
        group = root.addGroup(group_name)
    project.addMapLayer(layer, False)
    node = group.addLayer(layer)
    node.setItemVisibilityChecked(visible)


def _add_picture(layout, path: Path, x: float, y: float, width: float, height: float) -> QgsLayoutItemPicture:
    picture = QgsLayoutItemPicture(layout)
    picture.setPicturePath(path.relative_to(ROOT).as_posix())
    layout.addLayoutItem(picture)
    picture.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
    picture.attemptResize(QgsLayoutSize(width, height, QgsUnitTypes.LayoutMillimeters))
    return picture


def _add_map(layout, extent: QgsRectangle, layers: list[QgsVectorLayer], x: float, y: float, width: float, height: float) -> QgsLayoutItemMap:
    item = QgsLayoutItemMap(layout)
    layout.addLayoutItem(item)
    item.setFrameEnabled(True)
    item.setFrameStrokeColor(QColor("#555555"))
    item.setFrameStrokeWidth(QgsLayoutMeasurement(0.25, QgsUnitTypes.LayoutMillimeters))
    # A layout map calculates its extent from its physical size. Give it a
    # non-zero temporary size before setting the metric extent, then impose the
    # requested print-layout rectangle afterwards.
    item.attemptResize(QgsLayoutSize(10, 10, QgsUnitTypes.LayoutMillimeters))
    item.setExtent(extent)
    item.setLayers(layers)
    item.setKeepLayerSet(True)
    item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
    item.attemptResize(QgsLayoutSize(width, height, QgsUnitTypes.LayoutMillimeters))
    item.zoomToExtent(extent)
    item.refresh()
    return item


def _page(layout) -> None:
    layout.initializeDefaults()
    layout.pageCollection().page(0).setPageSize(
        QgsLayoutSize(297, 210, QgsUnitTypes.LayoutMillimeters)
    )


def _export_layout(layout, key: str) -> None:
    layout.refresh()
    layout.update()
    exporter = QgsLayoutExporter(layout)
    image_settings = QgsLayoutExporter.ImageExportSettings()
    image_settings.dpi = 180
    image_target = MAP_EXPORTS[key]
    pdf_target = PDF_EXPORTS[key]
    image_temporary = image_target.with_name(image_target.stem + ".tmp.png")
    pdf_temporary = pdf_target.with_name(pdf_target.stem + ".tmp.pdf")
    image_status = exporter.exportToImage(str(image_temporary), image_settings)
    pdf_status = exporter.exportToPdf(str(pdf_temporary), QgsLayoutExporter.PdfExportSettings())
    if image_status != QgsLayoutExporter.Success or pdf_status != QgsLayoutExporter.Success:
        raise RuntimeError(f"Could not export QGIS layout {key}: image={image_status}, pdf={pdf_status}")
    os.replace(image_temporary, image_target)
    os.replace(pdf_temporary, pdf_target)


def _build_layouts(project: QgsProject, historical: QgsVectorLayer, hazard: QgsVectorLayer, boundary: QgsVectorLayer) -> None:
    extent = boundary.extent()
    extent.scale(1.04)
    manager = project.layoutManager()

    historical_layout = QgsPrintLayout(project)
    historical_layout.setName("Historical Wildfire Exposure Screening — Mainland Portugal")
    _page(historical_layout)
    manager.addLayout(historical_layout)
    _add_picture(historical_layout, ASSET_DIR / "historical_layout_title.png", 10, 7, 277, 18)
    historical_map = _add_map(historical_layout, extent, [historical, boundary], 10, 29, 196, 144)
    _add_picture(historical_layout, ASSET_DIR / "historical_layout_legend.png", 212, 35, 72, 48)
    _add_picture(historical_layout, ASSET_DIR / "scale_north.png", 212, 110, 72, 25)
    _add_picture(historical_layout, ASSET_DIR / "layout_footer.png", 10, 177, 277, 22)
    _export_layout(historical_layout, "historical")

    comparison_layout = QgsPrintLayout(project)
    comparison_layout.setName("Historical Exposure and Official ICNF Structural Hazard — Comparison")
    _page(comparison_layout)
    manager.addLayout(comparison_layout)
    _add_picture(comparison_layout, ASSET_DIR / "comparison_layout_title.png", 8, 7, 281, 18)
    left = _add_map(comparison_layout, extent, [historical, boundary], 8, 29, 132, 123)
    right = _add_map(comparison_layout, extent, [hazard, boundary], 150, 29, 132, 123)
    _add_picture(comparison_layout, ASSET_DIR / "scale_north.png", 10, 125, 72, 25)
    _add_picture(comparison_layout, ASSET_DIR / "comparison_historical_legend.png", 8, 154, 132, 26)
    _add_picture(comparison_layout, ASSET_DIR / "comparison_hazard_legend.png", 150, 154, 132, 26)
    _add_picture(comparison_layout, ASSET_DIR / "layout_footer.png", 10, 183, 277, 22)
    _export_layout(comparison_layout, "comparison")


def _validate_project() -> dict[str, object]:
    opened = QgsProject()
    if not opened.read(str(PROJECT_PATH)):
        raise ValueError("QGIS could not reopen the written project")
    expected = {
        "Historical exposure bands — 1 km cells",
        "ICNF structural hazard class — predominant class per 1 km cell",
        "Mainland Portugal boundary",
        "ERA5 coastal fallback QA",
        "National 2024 snapshot — retrospective EDA only",
    }
    names = {layer.name() for layer in opened.mapLayers().values()}
    missing = expected - names
    invalid = [layer.name() for layer in opened.mapLayers().values() if not layer.isValid()]
    layouts = [layout.name() for layout in opened.layoutManager().printLayouts()]
    expected_layouts = {
        "Historical Wildfire Exposure Screening — Mainland Portugal",
        "Historical Exposure and Official ICNF Structural Hazard — Comparison",
    }
    if missing or invalid or set(layouts) != expected_layouts:
        raise ValueError(f"QGIS project validation failed: missing={missing}, invalid={invalid}, layouts={layouts}")
    alias_expectations = {
        "cell_id": "Cell ID",
        "fire_years_history_10y_2km": "Recorded fire years, 2016–2025 (2 km context)",
        "historical_exposure_band": "Historical exposure band",
        "official_icnf_hazard_class": "Official ICNF structural hazard (predominant 25 m class)",
        "forest_shrub_share_2km": "Forest/shrub share (2 km context)",
        "mean_slope_2km": "Mean slope (degrees; 2 km context)",
        "built_up_share": "Built-up share (1 km cell)",
    }
    screening_layers = [opened.mapLayersByName(name)[0] for name in (
        "Historical exposure bands — 1 km cells", "ICNF structural hazard class — predominant class per 1 km cell"
    )]
    aliases_ok = all(
        layer.attributeDisplayName(layer.fields().indexFromName(field)) == expected
        for layer in screening_layers for field, expected in alias_expectations.items()
    )
    if not aliases_ok:
        raise ValueError("QGIS aliases did not persist")
    if any(layer.featureCount() != 89_112 for layer in screening_layers):
        raise ValueError("QGIS screening views do not resolve all 89,112 features")
    exports = {key: {"png": path.relative_to(ROOT).as_posix(), "png_bytes": path.stat().st_size,
                     "pdf": PDF_EXPORTS[key].relative_to(ROOT).as_posix(), "pdf_bytes": PDF_EXPORTS[key].stat().st_size}
               for key, path in MAP_EXPORTS.items()}
    if any(record["png_bytes"] < 5_000 or record["pdf_bytes"] < 5_000 for record in exports.values()):
        raise ValueError("QGIS layout export is unexpectedly small")
    return {
        "project": PROJECT_PATH.relative_to(ROOT).as_posix(),
        "crs": "EPSG:3763",
        "layer_names": sorted(names),
        "layouts": layouts,
        "aliases_validated": aliases_ok,
        "screening_view_feature_count": 89_112,
        "exports": exports,
    }


def _write_validation(record: dict[str, object]) -> None:
    VALIDATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_JSON_PATH.write_text(json.dumps(record, indent=2), encoding="utf-8")
    export_rows = "\n".join(
        f"| {name} | `{details['png']}` | `{details['pdf']}` |"
        for name, details in record["exports"].items()
    )
    VALIDATION_PATH.write_text(
        f"""# QGIS presentation project validation

The portable QGIS project was created from existing, validated GeoPackage inputs only. It does not alter or duplicate the screening data.

- Project: `{record['project']}`
- Project CRS: {record['crs']}
- Project layers: {len(record['layer_names'])}
- Layout aliases validated: {record['aliases_validated']}
- Screening-view features validated: {record['screening_view_feature_count']:,} for each styled view

## Layout exports

| Layout | PNG | PDF |
|---|---|---|
{export_rows}

## Interpretation boundary

The map represents **1 km mainland grid cells with fire recurrence measured in a 2 km context**. It is historical comparative exposure only, not a next-year forecast, property-level safety guarantee, or purchase recommendation. The official ICNF structural-hazard view is a separate official product summarized to the same 1 km comparison resolution; it is not this project's prediction.
""",
        encoding="utf-8",
    )


def build_project() -> dict[str, object]:
    assets = [
        ASSET_DIR / "historical_layout_title.png", ASSET_DIR / "comparison_layout_title.png",
        ASSET_DIR / "historical_layout_legend.png", ASSET_DIR / "comparison_historical_legend.png",
        ASSET_DIR / "comparison_hazard_legend.png", ASSET_DIR / "scale_north.png", ASSET_DIR / "layout_footer.png",
    ]
    for path in (SCREENING_PATH, BOUNDARY_PATH, ERA5_QA_PATH, SNAPSHOT_PATH, *assets):
        if not path.exists():
            raise FileNotFoundError(path)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    PROJECT_PATH.parent.mkdir(parents=True, exist_ok=True)
    project = QgsProject.instance()
    project.clear()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:3763"))
    project.setPresetHomePath(str(ROOT))
    project.writeEntry("Paths", "/Absolute", False)
    project.writeEntry("Paths", "Absolute", False)

    historical = _load(SCREENING_PATH, SCREENING_LAYER, "Historical exposure bands — 1 km cells")
    hazard = _load(SCREENING_PATH, SCREENING_LAYER, "ICNF structural hazard class — predominant class per 1 km cell")
    boundary = _load(BOUNDARY_PATH, BOUNDARY_LAYER, "Mainland Portugal boundary")
    era5 = _load(ERA5_QA_PATH, ERA5_QA_LAYER, "ERA5 coastal fallback QA")
    snapshot = _load(SNAPSHOT_PATH, SNAPSHOT_LAYER, "National 2024 snapshot — retrospective EDA only")
    _apply_categories(historical, "historical_exposure_band", HISTORICAL_STYLE)
    _apply_categories(hazard, "official_icnf_hazard_class", HAZARD_STYLE)
    _apply_aliases_and_popup(historical)
    _apply_aliases_and_popup(hazard)
    boundary.setRenderer(QgsSingleSymbolRenderer(_fill("0,0,0,0", "48,48,48,255", "0.45")))
    era5.setRenderer(QgsSingleSymbolRenderer(_fill("#4C78A8", "#1F3F66", "0.12")))
    snapshot.setRenderer(QgsSingleSymbolRenderer(_fill("0,0,0,0", "102,102,102,255", "0.05")))
    _add_to_group(project, "01 Historical exposure screening", historical)
    _add_to_group(project, "02 Official ICNF comparison", hazard)
    _add_to_group(project, "03 Context", boundary)
    _add_to_group(project, "04 QA reference — off by default", era5, visible=False)
    _add_to_group(project, "04 QA reference — off by default", snapshot, visible=False)
    project.setFileName(str(PROJECT_PATH))
    _build_layouts(project, historical, hazard, boundary)
    if not project.write(str(PROJECT_PATH)):
        raise RuntimeError(f"Could not write QGIS project: {PROJECT_PATH}")
    record = _validate_project()
    _write_validation(record)
    return record


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate-existing",
        action="store_true",
        help="Open and validate the existing portable project without rebuilding or exporting it.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = _parse_args()
    qgis_prefix = os.environ.get("QGIS_PREFIX_PATH")
    QgsApplication.setPrefixPath(qgis_prefix or "", True)
    # Layout export needs the Qt GUI resources even though QT_QPA_PLATFORM is offscreen.
    application = QgsApplication([], True)
    application.initQgis()
    try:
        result = _validate_project() if arguments.validate_existing else build_project()
        print(json.dumps(result, indent=2))
    finally:
        application.exitQgis()
