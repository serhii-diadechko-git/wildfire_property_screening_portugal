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
    five: {
      description: "Five equal national-rank groups for more detail. Colours do not show the percentage expected to burn.",
      items: [["#fff1c7", "0–20th national rank"], ["#f8cf6a", ">20–40th national rank"], ["#eca900", ">40–60th national rank"], ["#dd6b32", ">60–80th national rank"], ["#a6222a", ">80–100th national rank"]],
      band: (percentile) => percentile <= 0.20 ? ["#fff1c7", "0–20th national-rank group"] : percentile <= 0.40 ? ["#f8cf6a", ">20–40th national-rank group"] : percentile <= 0.60 ? ["#eca900", ">40–60th national-rank group"] : percentile <= 0.80 ? ["#dd6b32", ">60–80th national-rank group"] : ["#a6222a", ">80–100th national-rank group"],
    },
  };
  const map = L.map("map", { preferCanvas: true, zoomControl: true, minZoom: 5, maxZoom: 13 });
  const cellLayers = new Map();
  const highlightTiers = new Map();
  const selectionTitle = document.getElementById("selection-title");
  const selectionContent = document.getElementById("selection-content");
  const clearSelection = document.getElementById("clear-selection");
  const legendDescription = document.getElementById("legend-description");
  const legendItems = document.getElementById("legend-items");
  let exposureOpacity = 0.82;
  let selectionRequestId = 0;
  let classificationMode = "three";
  let cells;
  let selectedFeature;
  let selectedContext;

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

  function defaultSelection() {
    selectionTitle.textContent = "Cell details";
    clearSelection.hidden = true;
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
    }</table><div class="rank-scale" aria-label="National relative rank ${rank.toFixed(1)}th percentile"><span class="rank-marker" style="left:${rank.toFixed(3)}%"></span></div><div class="rank-scale-labels"><span>Lower national rank</span><strong>${rank.toFixed(1)}th percentile</strong><span>Higher national rank</span></div><p class="interpretation-note"><strong>Two different percentages:</strong> burned share estimates how much of this cell may burn. National rank compares that estimate with all 89,112 mainland cells.</p><div class="context-heading"><h3>Nearby context averages</h3><p>The selected cell's own estimate is shown above. These rows summarise all cells intersecting each circle.</p></div><div class="context-list">${summary}</div><p class="card-note">Context radii are surrounding-area summaries, not a second grid, property assessment, or separate prediction.</p><div class="highlight-guide"><span><i class="highlight-dot highlight-selected"></i>Selected cell</span><span><i class="highlight-dot highlight-three"></i>Within 3 km</span><span><i class="highlight-dot highlight-five"></i>3&ndash;5 km</span></div>`;
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
    selectionContent.innerHTML = '<p>Loading selected-cell and nearby-area context…</p>';
    replaceHighlights(feature.properties.cell_id);
    const query = new URLSearchParams({ longitude: event.latlng.lng.toFixed(6), latitude: event.latlng.lat.toFixed(6), buffers_km: "1,3,5" });
    fetch(`/v1/exposure?${query}`)
      .then((response) => response.ok ? response.json() : response.json().then((body) => Promise.reject(new Error(body.detail || "Selected-cell context is unavailable."))))
      .then((context) => {
        if (requestId !== selectionRequestId) return;
        selectedFeature = feature;
        selectedContext = context;
        selectionContent.innerHTML = selectionHtml(feature.properties, context);
        applyHighlights(feature.properties.cell_id, context.context_buffers);
      })
      .catch((error) => {
        if (requestId !== selectionRequestId) return;
        selectionContent.innerHTML = `<p><strong>Selected cell:</strong> ${text(feature.properties.cell_id)}</p><p class="card-note">${text(error.message)}</p>`;
      });
  }

  clearSelection.addEventListener("click", () => {
    selectionRequestId += 1;
    clearHighlights();
    selectedFeature = undefined;
    selectedContext = undefined;
    defaultSelection();
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
      const control = L.control({ position: "topleft" });
      control.onAdd = () => {
        const element = L.DomUtil.create("div", "opacity-control leaflet-bar");
        element.innerHTML = '<label for="exposure-opacity">2026 layer opacity <output id="opacity-value">82%</output></label><input id="exposure-opacity" type="range" min="0" max="100" value="82" aria-label="2026 exposure layer opacity">';
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
