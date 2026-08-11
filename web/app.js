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
  const clearSelection = document.getElementById("clear-selection");
  const showInputDetails = document.getElementById("show-input-details");
  const inputDetailsDialog = document.getElementById("input-details-dialog");
  const inputDetailsContent = document.getElementById("input-details-content");
  const inputDetailsClose = document.getElementById("input-details-close");
  const legendDescription = document.getElementById("legend-description");
  const legendItems = document.getElementById("legend-items");
  let exposureOpacity = 0.82;
  let selectionRequestId = 0;
  let classificationMode = "three";
  let cells;
  let selectedFeature;
  let selectedContext;
  let selectedInputs;

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

  const percent = (value, digits = 2) => `${(Number(value) * 100).toFixed(digits)}%`;
  const text = (value) => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", "\"": "&quot;" })[char]);
  const row = (name, value) => `<tr><td>${name}</td><td>${value}</td></tr>`;

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
      ["Built-up share", percent(inputs.built_up_share), "Built environment in the 1 km cell", "The proportion of this cell's land covered by buildings, roads, and other developed surfaces in the CLC land-cover data."],
      ["Forest/shrub share", percent(inputs.forest_shrub_share_2km), "Mainland land within the 2 km context", "The proportion of mainland land around the cell classified as forest or shrubland, measured in the outward 2 km context."],
      ["Mean slope", `${Number(inputs.mean_slope_2km).toFixed(1)}\u00b0`, "Terrain context within the 2 km buffer", "The average steepness of the surrounding terrain. Higher degrees mean steeper land."],
      ["Previously burned years", `${inputs.fire_years_previous_10y_2km} of 10`, `Distinct years in ${inputs.historical_fire_start_year}\u2013${inputs.historical_fire_end_year}, within the 2 km context`, "The number of different years in the previous ten years when burned-area geometry was recorded within the surrounding 2 km context."],
      ["Mean summer temperature", `${Number(inputs.warm_season_mean_2m_temperature_c).toFixed(1)}\u00b0C`, `June\u2013September ${inputs.climate_reference_year}`, "The average June-to-September air temperature, measured by ERA5-Land at the standard height of 2 metres above the ground."],
      ["Summer precipitation", `${Number(inputs.warm_season_total_precipitation_mm).toFixed(1)} mm`, `June\u2013September ${inputs.climate_reference_year}`, "The total estimated rainfall for June through September. Millimetres describe the depth of water over a flat surface."],
      ["Mean surface soil water", Number(inputs.warm_season_mean_soil_water_layer1).toFixed(3), `June\u2013September ${inputs.climate_reference_year}`, "The average water content in ERA5-Land's top soil layer, approximately the upper 7 cm. Larger values mean wetter near-surface soil."],
      ["Warmest monthly mean", `${Number(inputs.warm_season_max_monthly_2m_temperature_c).toFixed(1)}\u00b0C`, `Warmest monthly mean in June\u2013September ${inputs.climate_reference_year}`, "The highest of the four monthly average 2-metre air temperatures for June, July, August, and September."],
      ["Lowest monthly mean soil water", Number(inputs.warm_season_min_monthly_soil_water_layer1).toFixed(3), `Lowest monthly mean in June\u2013September ${inputs.climate_reference_year}`, "The lowest of the four monthly average top-layer soil-water values, representing the driest monthly soil condition in the warm season."],
    ];
    return `<p class="input-details-intro">These are the nine recorded inputs used together to produce this cell's 2026 estimate. They describe context; they are not separate proven causes.</p><p class="input-details-source"><strong>Source periods:</strong> ${sourceSummary}</p><div class="input-details-grid">${featureRows.map(([name, value, meaning, help]) => `<section><div class="input-feature-heading"><strong>${name}</strong><button class="feature-info" type="button" aria-label="What ${name} means" data-help="${text(help)}">i</button></div><span class="input-value">${value}</span><span>${meaning}</span></section>`).join("")}</div><p class="card-note">Select or focus an <strong>i</strong> icon for a plain-language definition. The result combines all nine inputs through the final model and remains a broad-area comparative estimate, not a property-level assessment.</p>`;
  }

  function defaultSelection() {
    selectionTitle.textContent = "Cell details";
    clearSelection.hidden = true;
    showInputDetails.hidden = true;
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
    const requestId = ++selectionRequestId;
    selectionTitle.textContent = "Selected cell";
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
      map.fitBounds(cells.getBounds(), { padding: [14, 14] });
    })
    .catch((error) => {
      selectionContent.innerHTML = `<p><strong>Map unavailable:</strong> ${text(error.message)} Run <code>python scripts/build_web_map_assets.py</code> after the documented reproduction workflow.</p>`;
      map.setView([39.6, -8.0], 6);
    });
})();
