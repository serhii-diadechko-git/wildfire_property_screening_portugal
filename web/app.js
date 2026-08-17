/* Local presentation client. It reads a derived 2026 map asset and queries the
 * same-origin read-only API for click context; no model work occurs in the browser. */
(() => {
  "use strict";
  const classifications = {
    three: {
      description: "Overview groups based on each cell's national rank. Colours do not show the percentage expected to burn.",
      items: [["#ead9a0", "Lower national rank (0–50th percentile)"], ["#eca900", "Intermediate national rank (>50–80th percentile)"], ["#a6222a", "Higher national rank (>80–100th percentile)"]],
      band: (percentile) => percentile <= 0.50 ? ["#ead9a0", "Lower national rank (0–50th percentile)"] : percentile <= 0.80 ? ["#eca900", "Intermediate national rank (>50–80th percentile)"] : ["#a6222a", "Higher national rank (>80–100th percentile)"],
    },
    fifteen: {
      description: "Detailed national-rank intervals, mostly 15 percentile points wide. Colours still do not show the percentage expected to burn.",
      items: [["#fff1c7", "0–15th national rank"], ["#f8dd94", ">15–30th national rank"], ["#f2c45d", ">30–45th national rank"], ["#eca900", ">45–60th national rank"], ["#dd7635", ">60–75th national rank"], ["#c7442e", ">75–90th national rank"], ["#8f1725", ">90–100th national rank"]],
      band: (percentile) => percentile <= 0.15 ? ["#fff1c7", "0–15th national-rank interval"] : percentile <= 0.30 ? ["#f8dd94", ">15–30th national-rank interval"] : percentile <= 0.45 ? ["#f2c45d", ">30–45th national-rank interval"] : percentile <= 0.60 ? ["#eca900", ">45–60th national-rank interval"] : percentile <= 0.75 ? ["#dd7635", ">60–75th national-rank interval"] : percentile <= 0.90 ? ["#c7442e", ">75–90th national-rank interval"] : ["#8f1725", ">90–100th national-rank interval"],
    },
  };
  const map = L.map("map", { preferCanvas: true, zoomControl: true, minZoom: 5, maxZoom: 13 });
  const cellLayers = new Map();
  const highlightTiers = new Map();
  const selectionTitle = document.getElementById("selection-title");
  const selectionContent = document.getElementById("selection-content");
  const selectionToolbar = document.getElementById("selection-toolbar");
  const clearSelection = document.getElementById("clear-selection");
  const showInputDetails = document.getElementById("show-input-details");
  const inputDetailsDialog = document.getElementById("input-details-dialog");
  const inputDetailsContent = document.getElementById("input-details-content");
  const inputDetailsClose = document.getElementById("input-details-close");
  const featureHelpPopover = document.getElementById("feature-help-popover");
  const legendHelpButton = document.getElementById("legend-help-button");
  const legendHelpPopover = document.getElementById("legend-help-popover");
  const legendDescription = document.getElementById("legend-description");
  const legendItems = document.getElementById("legend-items");
  let exposureOpacity = 0.82;
  let selectionRequestId = 0;
  let classificationMode = "three";
  let cells;
  let selectedFeature;
  let selectedContext;
  let selectedInputs;
  let activeFeatureHelp;
  let legendHelpPinned = false;
  let measurementMode;
  let measurementPoints = [];
  let activeMeasurement;

  const standard = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\" target=\"_blank\" rel=\"noopener\">OpenStreetMap contributors</a>",
  });
  const humanitarian = L.tileLayer("https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\" target=\"_blank\" rel=\"noopener\">OpenStreetMap contributors</a>, tiles style by <a href=\"https://www.hotosm.org/\" target=\"_blank\" rel=\"noopener\">Humanitarian OpenStreetMap Team</a>",
  });
  const terrain = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 19,
    attribution: "Tiles &copy; Esri &mdash; Sources: Esri, DeLorme, HERE, USGS, Intermap, increment P Corp., GEBCO, FAO, NPS, NRCAN, GeoBase, IGN, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), swisstopo, MapmyIndia, and the GIS User Community",
  });
  const satellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 19,
    attribution: "Tiles &copy; Esri &mdash; Sources: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
  });
  const noBasemap = L.layerGroup();
  standard.addTo(map);
  L.control.layers({
    "OpenStreetMap Standard": standard,
    "OpenStreetMap Humanitarian": humanitarian,
    "Terrain (Esri World Topographic)": terrain,
    "Satellite imagery (Esri World Imagery)": satellite,
    "No online basemap": noBasemap,
  }, {}, { position: "topright", collapsed: false }).addTo(map);
  L.control.scale({ position: "bottomright", metric: true, imperial: false, maxWidth: 140 }).addTo(map);

  map.createPane("measurementPane");
  map.getPane("measurementPane").style.pointerEvents = "none";
  map.getPane("measurementPane").style.zIndex = "650";
  const measurementRenderer = L.svg({ pane: "measurementPane" });
  const measurementLayers = L.featureGroup().addTo(map);
  const measurementControl = L.control({ position: "topright" });
  measurementControl.onAdd = () => {
    const element = L.DomUtil.create("div", "measurement-control map-card");
    element.innerHTML = `<div class="measurement-toolbar" role="toolbar" aria-label="Map measurement tools">
      <button type="button" data-measure="distance" title="Measure distance: click points, then double-click to finish" aria-label="Measure distance" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 17 17 4l3 3L7 20H4v-3Zm8-8 3 3m-6 0 3 3m-6 0 3 3"/></svg></button>
      <button type="button" data-measure="area" title="Measure area: click polygon corners, then double-click to finish" aria-label="Measure area" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 5 14 2-2 12-12-2V5Zm0 0 12 14M19 7 5 17"/></svg></button>
      <button type="button" data-measure="clear" title="Clear all distance and area measurements" aria-label="Clear all measurements" disabled><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h14M9 7V4h6v3m-8 0 1 13h8l1-13M10 10v7m4-7v7"/></svg></button>
    </div><div class="measurement-status" aria-live="polite">Choose distance or area.</div>`;
    L.DomEvent.disableClickPropagation(element);
    L.DomEvent.disableScrollPropagation(element);
    return element;
  };
  let measurementStatus;
  let distanceMeasureButton;
  let areaMeasureButton;
  let clearMeasureButton;

  function installMeasurementControl() {
    measurementControl.addTo(map);
    measurementStatus = document.querySelector(".measurement-status");
    distanceMeasureButton = document.querySelector('[data-measure="distance"]');
    areaMeasureButton = document.querySelector('[data-measure="area"]');
    clearMeasureButton = document.querySelector('[data-measure="clear"]');
    distanceMeasureButton.addEventListener("click", () => setMeasurementMode("distance"));
    areaMeasureButton.addEventListener("click", () => setMeasurementMode("area"));
    clearMeasureButton.addEventListener("click", clearMeasurements);
    updateMeasurementButtons();
  }

  const percent = (value, digits = 2) => `${(Number(value) * 100).toFixed(digits)}%`;
  const text = (value) => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", "\"": "&quot;" })[char]);
  const row = (name, value) => `<tr><td>${name}</td><td>${value}</td></tr>`;

  const distanceMetres = (points) => points.slice(1).reduce((total, point, index) => total + map.distance(points[index], point), 0);
  const formatDistance = (metres) => metres < 1_000 ? `${metres.toFixed(0)} m` : `${(metres / 1_000).toFixed(3)} km`;
  const formatArea = (squareMetres) => squareMetres < 10_000
    ? `${squareMetres.toFixed(0)} m\u00b2`
    : squareMetres < 1_000_000
      ? `${(squareMetres / 10_000).toFixed(2)} ha`
      : `${(squareMetres / 1_000_000).toFixed(3)} km\u00b2 (${(squareMetres / 10_000).toFixed(1)} ha)`;

  // Spherical polygon area, matching Leaflet's geographic map coordinates.
  function geodesicArea(points) {
    if (points.length < 3) return 0;
    const radius = 6_378_137;
    const radians = Math.PI / 180;
    let sum = 0;
    for (let index = 0; index < points.length; index += 1) {
      const first = points[index];
      const second = points[(index + 1) % points.length];
      sum += (second.lng - first.lng) * radians * (2 + Math.sin(first.lat * radians) + Math.sin(second.lat * radians));
    }
    return Math.abs(sum * radius * radius / 2);
  }

  function measurementValue(points = measurementPoints) {
    return measurementMode === "distance" ? formatDistance(distanceMetres(points)) : formatArea(geodesicArea(points));
  }

  function updateMeasurementButtons() {
    distanceMeasureButton.setAttribute("aria-pressed", String(measurementMode === "distance"));
    areaMeasureButton.setAttribute("aria-pressed", String(measurementMode === "area"));
    clearMeasureButton.disabled = measurementLayers.getLayers().length === 0;
    map.getContainer().classList.toggle("measurement-active", Boolean(measurementMode));
  }

  function cancelActiveMeasurement() {
    if (activeMeasurement) measurementLayers.removeLayer(activeMeasurement);
    activeMeasurement = undefined;
    measurementPoints = [];
  }

  function leaveMeasurementMode(message) {
    measurementMode = undefined;
    measurementPoints = [];
    activeMeasurement = undefined;
    map.doubleClickZoom.enable();
    map.dragging.enable();
    map.getContainer().classList.remove("measurement-active");
    measurementStatus.textContent = message;
    updateMeasurementButtons();
  }

  function setMeasurementMode(mode) {
    if (measurementMode === mode) {
      cancelActiveMeasurement();
      leaveMeasurementMode("Choose distance or area.");
    } else {
      cancelActiveMeasurement();
      measurementMode = mode;
      map.doubleClickZoom.disable();
      measurementStatus.textContent = mode === "distance"
        ? "Distance: click points; double-click to finish."
        : "Area: click corners; double-click to finish.";
    }
    if (measurementMode) updateMeasurementButtons();
  }

  function finishMeasurement() {
    const minimumPoints = measurementMode === "distance" ? 2 : 3;
    if (!activeMeasurement || measurementPoints.length < minimumPoints) return;
    const value = measurementValue();
    activeMeasurement.setLatLngs(measurementPoints);
    activeMeasurement.bindTooltip(value, { permanent: true, direction: "center", className: "measurement-label", interactive: false }).openTooltip();
    leaveMeasurementMode(`Measured: ${value}`);
  }

  function clearMeasurements() {
    measurementLayers.clearLayers();
    leaveMeasurementMode("All measurements cleared. Click any map cell to inspect it.");
  }

  map.on("click", (event) => {
    if (!measurementMode) return;
    measurementPoints.push(event.latlng);
    if (!activeMeasurement) {
      activeMeasurement = measurementMode === "distance"
        ? L.polyline(measurementPoints, { color: "#22d3ee", interactive: false, renderer: measurementRenderer, weight: 3 })
        : L.polygon(measurementPoints, { color: "#22d3ee", fillColor: "#0e7490", fillOpacity: 0.25, interactive: false, renderer: measurementRenderer, weight: 2 });
      activeMeasurement.addTo(measurementLayers);
    } else {
      activeMeasurement.setLatLngs(measurementPoints);
    }
    const minimumPoints = measurementMode === "distance" ? 2 : 3;
    measurementStatus.innerHTML = measurementPoints.length >= minimumPoints
      ? `<strong>Current ${measurementMode}:</strong> ${measurementValue()} &mdash; double-click to finish.`
      : `${measurementMode === "distance" ? "Distance" : "Area"}: add ${minimumPoints - measurementPoints.length} more point${minimumPoints - measurementPoints.length === 1 ? "" : "s"}.`;
    updateMeasurementButtons();
  });
  map.on("mousemove", (event) => {
    if (!measurementMode || measurementPoints.length === 0 || !activeMeasurement) return;
    activeMeasurement.setLatLngs([...measurementPoints, event.latlng]);
    measurementStatus.innerHTML = `<strong>Current ${measurementMode}:</strong> ${measurementValue([...measurementPoints, event.latlng])}`;
  });
  map.on("dblclick", (event) => {
    if (!measurementMode) return;
    L.DomEvent.stop(event.originalEvent);
    if (measurementPoints.length > 1 && map.distance(measurementPoints.at(-1), measurementPoints.at(-2)) < 1) measurementPoints.pop();
    finishMeasurement();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !measurementMode) return;
    cancelActiveMeasurement();
    leaveMeasurementMode("Measurement cancelled. Click any map cell to inspect it.");
  });

  // Keep surrounding-radius summaries visually secondary to the selected
  // cell's own estimate. Each row reports an area-weighted context average,
  // not another estimate for the selected 1 km cell.
  const contextRow = (item) => `<div class="context-row">
    <div class="context-radius"><strong>${item.radius_km} km</strong><span>radius</span></div>
    <div class="context-measure"><strong>${percent(item.mean_predicted_burned_share_next_year)}</strong><span>average estimated burned share</span></div>
    <div class="context-detail"><span>${item.intersecting_cell_count} intersecting cells</span><span>${percent(item.higher_estimated_exposure_area_share, 1)} of context area in the highest national-rank group</span></div>
  </div>`;

  // This modal intentionally shows the recorded values supplied jointly to
  // the model. It does not claim that one displayed value caused the estimate.
  function inputDetailsHtml(inputs) {
    const sourceSummary = `ICNF history ${inputs.historical_fire_start_year}\u2013${inputs.historical_fire_end_year}; CLC ${inputs.land_cover_reference_year} (${text(inputs.land_cover_release_id)}); ${text(inputs.terrain_release_id)}; ERA5-Land JJAS ${inputs.climate_reference_year}.`;
    const featureRows = [
      ["Built/artificial land share (CLC)", percent(inputs.built_up_share), Number(inputs.built_up_share) === 0 ? "No CLC artificial-surface class mapped in this 1 km cell" : "Broad CLC artificial-surface share in the 1 km cell", "How much of this 1 km cell is mapped as developed or artificial land.", `Source: CLC ${inputs.land_cover_reference_year} broad classes such as urban fabric, transport, industry and construction. It does not identify individual buildings or properties.`],
      ["Forest/shrub share (CLC)", percent(inputs.forest_shrub_share_2km), "Broad CLC forest/shrub context within 2 km", "How much of the surrounding land within 2 km is mapped as forest or shrubland.", `Source: CLC ${inputs.land_cover_reference_year}. This describes broad vegetation cover, not tree density, fuel load, current vegetation condition or a specific property.`],
      ["Mean slope (DEM, 2 km)", `${Number(inputs.mean_slope_2km).toFixed(1)}\u00b0`, "DEM-derived average across the 2 km context", "The average steepness of the terrain within 2 km. A larger angle means steeper land.", "Source: Copernicus DEM GLO-30 elevation data. This is an area average, not a surveyed slope for a specific property."],
      ["Previously burned years (ICNF)", `${inputs.fire_years_previous_10y_2km} of 10`, `Years with any mapped burn in ${inputs.historical_fire_start_year}\u2013${inputs.historical_fire_end_year}, within 2 km`, "How many of the previous 10 years had a mapped wildfire somewhere within 2 km.", "Source: official ICNF annual burned-area maps. This counts years, not individual fires or total area burned, and it does not prove that this selected cell burned."],
      ["Mean summer temperature (ERA5-Land)", `${Number(inputs.warm_season_mean_2m_temperature_c).toFixed(1)}\u00b0C`, `Coarse regional June\u2013September ${inputs.climate_reference_year} context`, "The average June-to-September air temperature. “2 m” means 2 metres above the ground.", "Source: ERA5-Land. This is coarse regional climate context assigned to the cell, not downscaled 1 km or property-level weather."],
      ["Summer precipitation (ERA5-Land)", `${Number(inputs.warm_season_total_precipitation_mm).toFixed(1)} mm`, `Coarse regional June\u2013September ${inputs.climate_reference_year} total`, "The estimated total rainfall from June through September.", "Source: ERA5-Land monthly data, converted to a day-weighted seasonal total. Millimetres describe water depth over a flat surface; this is not a local rain-gauge reading."],
      ["Mean shallow soil water (ERA5-Land)", `${Number(inputs.warm_season_mean_soil_water_layer1).toFixed(3)} m\u00b3/m\u00b3`, `Coarse regional June\u2013September ${inputs.climate_reference_year} mean`, "The average amount of water in the shallow soil, approximately the top 7 cm. A larger value means wetter soil.", "Source: ERA5-Land soil layer 1. The unit is cubic metres of water per cubic metre of soil. This is coarse modelled context, not a measurement at a property."],
      ["Warmest monthly mean (ERA5-Land)", `${Number(inputs.warm_season_max_monthly_2m_temperature_c).toFixed(1)}\u00b0C`, `Highest monthly mean in June\u2013September ${inputs.climate_reference_year}`, "The highest monthly average temperature among June, July, August and September.", "Source: ERA5-Land 2-metre air temperature. This is a monthly average—not the hottest day, a daily maximum or a property-level reading."],
      ["Lowest monthly mean soil water (ERA5-Land)", `${Number(inputs.warm_season_min_monthly_soil_water_layer1).toFixed(3)} m\u00b3/m\u00b3`, `Lowest monthly mean in June\u2013September ${inputs.climate_reference_year}`, "The driest monthly average shallow-soil condition between June and September.", "Source: ERA5-Land soil layer 1. This is the lowest of four monthly averages—not the driest day or a property-level soil measurement."],
    ];
    return `<p class="input-details-intro">These are the nine recorded inputs used together to produce this cell's 2026 estimate. They describe context; they are not separate proven causes.</p><p class="input-details-source"><strong>Source periods:</strong> ${sourceSummary}</p><div class="input-details-grid">${featureRows.map(([name, value, caption, meaning, context]) => `<section><div class="input-feature-heading"><strong>${name}</strong><button class="feature-info" type="button" aria-label="What ${name} means" data-help-meaning="${text(meaning)}" data-help-context="${text(context)}">i</button></div><span class="input-value">${value}</span><span>${caption}</span></section>`).join("")}</div><p class="card-note">Select or focus an <strong>i</strong> icon for a plain-language definition. The result combines all nine inputs through the final model and remains a broad-area comparative estimate, not a property-level assessment.</p>`;
  }

  // Keep help independent of the feature-card layout. It floats beside the
  // selected icon, remains inside the dialog, and never resizes the card.
  function showFeatureHelp(button) {
    featureHelpPopover.innerHTML = `<strong class="feature-help-main">${text(button.dataset.helpMeaning)}</strong><span class="feature-help-label">Source and context</span><span class="feature-help-context">${text(button.dataset.helpContext)}</span>`;
    inputDetailsDialog.appendChild(featureHelpPopover);
    featureHelpPopover.hidden = false;
    const buttonRect = button.getBoundingClientRect();
    const dialogRect = inputDetailsDialog.getBoundingClientRect();
    const popoverRect = featureHelpPopover.getBoundingClientRect();
    const gap = 8;
    const minimumLeft = dialogRect.left + gap;
    const maximumLeft = dialogRect.right - popoverRect.width - gap;
    const preferredLeft = buttonRect.left - popoverRect.width - gap;
    const left = Math.min(Math.max(minimumLeft, preferredLeft), maximumLeft);
    const preferredTop = buttonRect.top - popoverRect.height - gap;
    const fallbackTop = buttonRect.bottom + gap;
    const top = preferredTop >= dialogRect.top + gap
      ? preferredTop
      : Math.min(fallbackTop, dialogRect.bottom - popoverRect.height - gap);
    featureHelpPopover.style.left = `${left}px`;
    featureHelpPopover.style.top = `${top}px`;
    activeFeatureHelp = button;
  }

  function hideFeatureHelp(button) {
    if (button && activeFeatureHelp !== button) return;
    featureHelpPopover.hidden = true;
    activeFeatureHelp = undefined;
  }

  function showLegendHelp() {
    legendHelpPopover.hidden = false;
    legendHelpButton.setAttribute("aria-expanded", "true");
    const buttonRect = legendHelpButton.getBoundingClientRect();
    const popoverRect = legendHelpPopover.getBoundingClientRect();
    const gap = 8;
    const left = Math.max(gap, buttonRect.left - popoverRect.width - gap);
    const top = Math.min(
      Math.max(gap, buttonRect.top),
      window.innerHeight - popoverRect.height - gap,
    );
    legendHelpPopover.style.left = `${left}px`;
    legendHelpPopover.style.top = `${Math.max(gap, top)}px`;
  }

  function hideLegendHelp() {
    legendHelpPopover.hidden = true;
    legendHelpButton.setAttribute("aria-expanded", "false");
  }

  function defaultSelection() {
    selectionTitle.textContent = "Selected cell";
    selectionToolbar.hidden = true;
    clearSelection.hidden = true;
    showInputDetails.hidden = true;
    hideFeatureHelp();
    selectionContent.innerHTML = '<p>Click a 1 km cell to inspect its 2026 comparative estimate.</p><p class="card-note">The map will also highlight nearby 3 km and 5 km context cells. These are surrounding-area summaries, not a second grid or a property assessment.</p>';
  }

  function selectionHtml(properties, context) {
    const contexts = context.context_buffers;
    const rank = Number(properties.predicted_exposure_percentile) * 100;
    const summary = contexts.map(contextRow).join("");
    return `<div class="selected-cell-primary">
      <span class="selected-cell-kicker">Selected 1 km cell</span>
      <strong class="selected-cell-value">${percent(properties.predicted_burned_share_next_year)}</strong>
      <span class="selected-cell-unit">estimated 2026 burned share</span>
    </div><table class="selection-table">${
      row("Cell ID", text(properties.cell_id)) +
      row("National relative rank", `${rank.toFixed(1)}th percentile`) +
      row("Map colour group", text(currentBand(properties)[1])) +
      row("Predictor inputs", text(properties.prediction_input_year))
    }</table><div class="rank-scale" aria-label="National relative rank ${rank.toFixed(1)}th percentile"><span class="rank-marker" style="left:${rank.toFixed(3)}%"></span></div><div class="rank-scale-labels"><span>Lower national rank</span><strong>${rank.toFixed(1)}th percentile</strong><span>Higher national rank</span></div><p class="interpretation-note"><strong>Two different percentages:</strong> burned share estimates how much of this cell may burn. National rank compares that estimate with all 89,112 mainland cells.</p><div class="context-heading"><h3>Nearby context averages</h3><p>The selected cell's own estimate is shown above. These rows summarise all cells intersecting each circle.</p></div><div class="context-list">${summary}</div><p class="card-note">These radius areas are surrounding-area summaries, not a second grid, property assessment, or separate prediction.</p><div class="highlight-guide"><span><i class="highlight-dot highlight-selected"></i>Selected cell</span><span><i class="highlight-dot highlight-three"></i>Within 3 km</span><span><i class="highlight-dot highlight-five"></i>3&ndash;5 km</span></div>`;
  }

  function currentBand(properties) {
    return classifications[classificationMode].band(Number(properties.predicted_exposure_percentile));
  }

  function renderLegend() {
    const classification = classifications[classificationMode];
    legendDescription.textContent = classification.description;
    legendItems.innerHTML = classification.items.map(([color, label]) => `<li><span class="swatch" style="background:${color}"></span>${label}</li>`).join("");
  }

  function changeClassification(mode) {
    classificationMode = mode;
    renderLegend();
    if (cells) cells.eachLayer((layer) => layer.setStyle(style(layer.feature)));
    if (selectedFeature && selectedContext) selectionContent.innerHTML = selectionHtml(selectedFeature.properties, selectedContext);
  }

  function style(feature) {
    const tier = highlightTiers.get(feature.properties.cell_id);
    if (tier === "selected") return { color: "#fff7b0", weight: 2.4, opacity: 1, fillColor: "#f7d64a", fillOpacity: 0.72 };
    if (tier === "three") return { color: "#3fc0dc", weight: 1.2, opacity: 1, fillColor: "#3fc0dc", fillOpacity: 0.50 };
    if (tier === "five") return { color: "#3177a5", weight: 1.0, opacity: 1, fillColor: "#3177a5", fillOpacity: 0.36 };
    return { color: "#4a4a4a", weight: 0.15, opacity: 0.65, fillColor: currentBand(feature.properties)[0], fillOpacity: exposureOpacity };
  }

  function redrawCells(cellIds) {
    for (const cellId of cellIds) {
      const layer = cellLayers.get(cellId);
      if (layer) layer.setStyle(style(layer.feature));
    }
  }

  function clearHighlights() {
    const previousCellIds = [...highlightTiers.keys()];
    highlightTiers.clear();
    redrawCells(previousCellIds);
  }

  function replaceHighlights(selectedCellId, buffers = []) {
    const changedCellIds = new Set(highlightTiers.keys());
    highlightTiers.clear();
    const byRadius = new Map(buffers.map((item) => [item.radius_km, new Set(item.intersecting_cell_ids)]));
    for (const cellId of byRadius.get(5) || []) highlightTiers.set(cellId, "five");
    for (const cellId of byRadius.get(3) || []) highlightTiers.set(cellId, "three");
    highlightTiers.set(selectedCellId, "selected");
    for (const cellId of highlightTiers.keys()) changedCellIds.add(cellId);
    redrawCells(changedCellIds);
  }

  function applyHighlights(selectedCellId, buffers) {
    replaceHighlights(selectedCellId, buffers);
  }

  function selectCell(feature, event) {
    if (measurementMode) return;
    const requestId = ++selectionRequestId;
    selectionTitle.textContent = "Selected cell";
    selectionToolbar.hidden = false;
    clearSelection.hidden = false;
    showInputDetails.hidden = true;
    selectionContent.innerHTML = '<p>Loading selected-cell and nearby-area context…</p>';
    replaceHighlights(feature.properties.cell_id);
    const query = new URLSearchParams({ longitude: event.latlng.lng.toFixed(6), latitude: event.latlng.lat.toFixed(6), buffers_km: "1,3,5" });
    fetch(`/v1/exposure?${query}`)
      .then((response) => response.ok ? response.json() : response.json().then((body) => Promise.reject(new Error(body.detail || "Selected-cell context is unavailable."))))
      .then((context) => {
        if (requestId !== selectionRequestId) return;
        selectedFeature = feature;
        selectedContext = context;
        selectedInputs = context.model_inputs;
        showInputDetails.hidden = !selectedInputs;
        selectionContent.innerHTML = selectionHtml(feature.properties, context);
        applyHighlights(feature.properties.cell_id, context.context_buffers);
      })
      .catch((error) => {
        if (requestId !== selectionRequestId) return;
        selectedInputs = undefined;
        showInputDetails.hidden = true;
        selectionContent.innerHTML = `<p><strong>Selected cell:</strong> ${text(feature.properties.cell_id)}</p><p class="card-note">${text(error.message)}</p>`;
      });
  }

  clearSelection.addEventListener("click", () => {
    selectionRequestId += 1;
    clearHighlights();
    selectedFeature = undefined;
    selectedContext = undefined;
    selectedInputs = undefined;
    if (inputDetailsDialog.open) inputDetailsDialog.close();
    hideFeatureHelp();
    defaultSelection();
  });
  showInputDetails.addEventListener("click", () => {
    if (!selectedInputs) return;
    inputDetailsContent.innerHTML = inputDetailsHtml(selectedInputs);
    inputDetailsDialog.showModal();
  });
  inputDetailsClose.addEventListener("click", () => inputDetailsDialog.close());
  inputDetailsDialog.addEventListener("click", (event) => {
    if (event.target === inputDetailsDialog) inputDetailsDialog.close();
  });
  inputDetailsDialog.addEventListener("close", () => hideFeatureHelp());
  inputDetailsContent.addEventListener("pointerover", (event) => {
    const button = event.target.closest(".feature-info");
    if (button) showFeatureHelp(button);
  });
  inputDetailsContent.addEventListener("pointerout", (event) => {
    const button = event.target.closest(".feature-info");
    if (button && !button.contains(event.relatedTarget)) hideFeatureHelp(button);
  });
  inputDetailsContent.addEventListener("focusin", (event) => {
    const button = event.target.closest(".feature-info");
    if (button) showFeatureHelp(button);
  });
  inputDetailsContent.addEventListener("focusout", (event) => {
    const button = event.target.closest(".feature-info");
    if (button && !button.contains(event.relatedTarget)) hideFeatureHelp(button);
  });
  inputDetailsContent.addEventListener("click", (event) => {
    const button = event.target.closest(".feature-info");
    if (!button) return;
    event.preventDefault();
    showFeatureHelp(button);
  });
  legendHelpButton.addEventListener("mouseenter", showLegendHelp);
  legendHelpButton.addEventListener("mouseleave", () => {
    if (!legendHelpPinned) hideLegendHelp();
  });
  legendHelpButton.addEventListener("focus", showLegendHelp);
  legendHelpButton.addEventListener("blur", () => {
    if (!legendHelpPinned) hideLegendHelp();
  });
  legendHelpButton.addEventListener("click", (event) => {
    event.preventDefault();
    legendHelpPinned = !legendHelpPinned;
    if (legendHelpPinned) showLegendHelp();
    else hideLegendHelp();
  });
  document.addEventListener("pointerdown", (event) => {
    if (!legendHelpPinned || event.target === legendHelpButton) return;
    legendHelpPinned = false;
    hideLegendHelp();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || legendHelpPopover.hidden) return;
    legendHelpPinned = false;
    hideLegendHelp();
    legendHelpButton.focus();
  });
  window.addEventListener("resize", () => {
    if (!legendHelpPopover.hidden) showLegendHelp();
  });
  document.querySelectorAll('input[name="display-classification"]').forEach((input) => {
    input.addEventListener("change", () => changeClassification(input.value));
  });
  defaultSelection();
  renderLegend();

  fetch("/v1/map/2026/cells.geojson")
    .then((response) => response.ok ? response.json() : response.json().then((body) => Promise.reject(new Error(body.detail || "Map asset is unavailable."))))
    .then((data) => {
      cells = L.geoJSON(data, {
        renderer: L.canvas({ padding: 0.25 }),
        style,
        onEachFeature(feature, layer) {
          cellLayers.set(feature.properties.cell_id, layer);
          layer.on({
            mouseover: () => layer.setStyle({ weight: 0.8, color: "#15243a" }),
            mouseout: () => layer.setStyle(style(feature)),
            click: (event) => selectCell(feature, event),
          });
        },
      }).addTo(map);
      // Keep display controls together: the opacity control follows the
      // basemap selector in Leaflet's top-right control stack.
      const control = L.control({ position: "topright" });
      control.onAdd = () => {
        const element = L.DomUtil.create("div", "opacity-control map-card");
        element.innerHTML = '<div class="opacity-heading">2026 layer opacity</div><label for="exposure-opacity"><span>Exposure layer</span><output id="opacity-value">82%</output></label><input id="exposure-opacity" type="range" min="0" max="100" value="82" aria-label="2026 exposure layer opacity">';
        L.DomEvent.disableClickPropagation(element);
        L.DomEvent.disableScrollPropagation(element);
        return element;
      };
      control.addTo(map);
      const slider = document.getElementById("exposure-opacity");
      const output = document.getElementById("opacity-value");
      slider.addEventListener("input", () => {
        exposureOpacity = Number(slider.value) / 100;
        output.value = `${slider.value}%`;
        output.textContent = `${slider.value}%`;
        cells.eachLayer((layer) => layer.setStyle(style(layer.feature)));
      });
      installMeasurementControl();
      map.fitBounds(cells.getBounds(), { padding: [14, 14] });
    })
    .catch((error) => {
      selectionContent.innerHTML = `<p><strong>Map unavailable:</strong> ${text(error.message)} Run <code>python scripts/build_web_map_assets.py</code> after the documented reproduction workflow.</p>`;
      map.setView([39.6, -8.0], 6);
    });
})();
