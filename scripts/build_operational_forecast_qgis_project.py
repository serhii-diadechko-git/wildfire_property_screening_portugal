"""Create a portable QGIS view of the validated annual 2026 estimate.

Run through ``scripts\\run_qgis_presentation_project.bat`` so the installed
QGIS Python runtime is used.  This creates a separate project and never
rewrites the historical presentation project or any GeoPackage data.
"""

from __future__ import annotations

import os
import shutil
import sys
import zipfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsApplication,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsFillSymbol,
    QgsProject,
    QgsRuleBasedRenderer,
    QgsVectorLayer,
)


SOURCE_PROJECT = ROOT / "qgis" / "wildfire_exposure_screening_portugal.qgz"
PROJECT_PATH = ROOT / "qgis" / "wildfire_exposure_screening_portugal_2026.qgz"
FORECAST_PATH = ROOT / "data" / "processed" / "spatial_outputs" / "estimated_comparative_wildfire_exposure_2026.gpkg"
FORECAST_LAYER = "estimated_comparative_exposure_2026"
LAYER_NAME = "2026 estimated comparative wildfire exposure — 1 km cells"


def _fill(color: str) -> QgsFillSymbol:
    return QgsFillSymbol.createSimple({"color": color, "outline_color": "#5C4B43", "outline_width": "0.04"})


def _validate(project: QgsProject) -> None:
    layers = project.mapLayersByName(LAYER_NAME)
    if len(layers) != 1 or not layers[0].isValid():
        raise ValueError("The operational forecast layer did not persist in the QGIS project")
    layer = layers[0]
    if layer.crs().authid() != "EPSG:3763" or layer.featureCount() != 89_112:
        raise ValueError("Operational forecast layer CRS or feature count is invalid")
    required = {
        "cell_id", "prediction_input_year", "forecast_year", "predicted_burned_share_next_year",
        "predicted_exposure_percentile", "model_sha256", "score_status",
    }
    if not required.issubset(set(layer.fields().names())):
        raise ValueError("Operational forecast layer fields are incomplete")
    group = project.layerTreeRoot().findGroup("00 Annual comparative estimate — 2026")
    if group is None:
        raise ValueError("Operational estimate layer group is missing")


def _make_project_paths_relative() -> None:
    """Remove inherited absolute paths from copied layout layer sets.

    QGIS writes active layer sources relatively but preserves older layout
    sources verbatim when a project is copied.  Replace only the known project
    root prefix inside the compressed project definition, leaving all data
    untouched.  QGIS resolves ``../data`` from the ``qgis`` directory.
    """
    prefix_forward = ROOT.as_posix() + "/"
    prefix_backslash = str(ROOT) + "\\"
    temporary = PROJECT_PATH.with_suffix(".qgz.tmp")
    with zipfile.ZipFile(PROJECT_PATH, "r") as source, zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as target:
        for entry in source.infolist():
            payload = source.read(entry.filename)
            if entry.filename.endswith(".qgs"):
                text = payload.decode("utf-8")
                text = text.replace(prefix_forward, "../").replace(prefix_backslash, "..\\")
                text = text.replace(f'<homePath path="{ROOT}"/>', '<homePath path="."/>')
                payload = text.encode("utf-8")
            target.writestr(entry, payload)
    os.replace(temporary, PROJECT_PATH)


def build() -> None:
    if not SOURCE_PROJECT.is_file() or not FORECAST_PATH.is_file():
        raise FileNotFoundError("The validated historical QGIS project and 2026 forecast GeoPackage must exist")
    if PROJECT_PATH.exists():
        raise FileExistsError(f"Refusing to overwrite existing portable forecast project: {PROJECT_PATH}")
    shutil.copy2(SOURCE_PROJECT, PROJECT_PATH)
    project = QgsProject.instance()
    project.setPresetHomePath(str(ROOT))
    project.writeEntry("Paths", "/Absolute", False)
    project.writeEntry("Paths", "Absolute", False)
    if not project.read(str(PROJECT_PATH)):
        raise ValueError("Could not open copied historical QGIS project")
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:3763"))
    uri = f"{FORECAST_PATH.as_posix()}|layername={FORECAST_LAYER}"
    layer = QgsVectorLayer(uri, LAYER_NAME, "ogr")
    if not layer.isValid():
        raise ValueError("QGIS could not open the validated 2026 forecast GeoPackage")
    # Display-only percentile rules: they are saved in the project and never
    # add a field to or otherwise mutate the validated GeoPackage.
    root_rule = QgsRuleBasedRenderer.Rule(None)
    for expression, label, color in (
        ('"predicted_exposure_percentile" <= 0.50', "Lower estimated comparative exposure percentile (0–50%)", "#E9D8A6"),
        ('"predicted_exposure_percentile" > 0.50 AND "predicted_exposure_percentile" <= 0.80', "Intermediate estimated comparative exposure percentile (50–80%)", "#E69F00"),
        ('"predicted_exposure_percentile" > 0.80', "Higher estimated comparative exposure percentile (80–100%)", "#9B2226"),
    ):
        rule = root_rule.children()[0].clone() if root_rule.children() else QgsRuleBasedRenderer.Rule(_fill(color))
        rule.setSymbol(_fill(color))
        rule.setFilterExpression(expression)
        rule.setLabel(label)
        root_rule.appendChild(rule)
    layer.setRenderer(QgsRuleBasedRenderer(root_rule))
    aliases = {
        "cell_id": "Cell ID",
        "prediction_input_year": "Predictor-input year",
        "forecast_year": "Estimated outcome year",
        "predicted_burned_share_next_year": "Estimated comparative burned share",
        "predicted_exposure_percentile": "Estimated comparative exposure percentile",
        "model_sha256": "Model SHA-256",
        "score_status": "Score status",
    }
    for field, alias in aliases.items():
        layer.setFieldAlias(layer.fields().indexFromName(field), alias)
    layer.setMapTipTemplate(
        "<h3>2026 estimated comparative wildfire exposure</h3>"
        "<b>Cell:</b> [% \"cell_id\" %]<br>"
        "<b>Input year:</b> [% \"prediction_input_year\" %]; <b>estimated outcome year:</b> [% \"forecast_year\" %]<br>"
        "<b>Estimated comparative burned share:</b> [% round(\"predicted_burned_share_next_year\" * 100, 2) %]%<br>"
        "<b>Percentile:</b> [% round(\"predicted_exposure_percentile\" * 100, 1) %]%<br>"
        "<i>Comparative 1 km screening estimate only; not a probability, property-level forecast, safety guarantee, or purchase recommendation.</i>"
    )
    project.addMapLayer(layer, False)
    root = project.layerTreeRoot()
    group = root.insertGroup(0, "00 Annual comparative estimate — 2026")
    group.addLayer(layer)
    if not project.write(str(PROJECT_PATH)):
        raise RuntimeError("Could not write portable 2026 QGIS project")
    _make_project_paths_relative()
    reopened = QgsProject()
    if not reopened.read(str(PROJECT_PATH)):
        raise ValueError("QGIS could not reopen the portable 2026 project")
    _validate(reopened)
    print(f"Validated {PROJECT_PATH.relative_to(ROOT)} with {LAYER_NAME}")


if __name__ == "__main__":
    QgsApplication.setPrefixPath(os.environ.get("QGIS_PREFIX_PATH", ""), True)
    application = QgsApplication([], False)
    application.initQgis()
    try:
        build()
    finally:
        application.exitQgis()
