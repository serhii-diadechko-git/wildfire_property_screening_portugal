/* Local presentation client. It reads a derived 2026 map asset and queries the
 * same-origin read-only API for click context; no model work occurs in the browser. */
(() => {
  "use strict";
  const colors = { lower: "#ead9a0", intermediate: "#eca900", higher: "#a6222a" };
  const map = L.map("map", { preferCanvas: true, zoomControl: true, minZoom: 5, maxZoom: 13 });
  const cellLayers = new Map();
  const highlightTiers = new Map();
  const selectionTitle = document.getElementById("selection-title");
  const selectionContent = document.getElementById("selection-content");
  const clearSelection = document.getElementById("clear-selection");
  let exposureOpacity = 0.82;
  let selectionRequestId = 0;

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

  function defaultSelection() {
    selectionTitle.textContent = "Cell details";
    clearSelection.hidden = true;
    selectionContent.innerHTML = '<p>Click a 1 km cell to inspect its 2026 comparative estimate.</p><p class="card-note">The map will also highlight nearby 3 km and 5 km context cells. These are surrounding-area summaries, not a second grid or a property assessment.</p>';
  }

  function selectionHtml(properties, context) {
    const contexts = context.context_buffers;
    const summary = contexts.map((item) => row(
      `${item.radius_km} km radius`,
      `${item.intersecting_cell_count} cells; average estimate ${percent(item.mean_predicted_burned_share_next_year)}; ${percent(item.higher_estimated_exposure_area_share, 1)} in higher band`
    )).join("");
    return `<table class="selection-table">${
      row("Cell ID", text(properties.cell_id)) +
      row("2026 band", text(properties.estimated_comparative_exposure_band)) +
      row("Estimated burned share", percent(properties.predicted_burned_share_next_year)) +
      row("Predictor inputs", text(properties.prediction_input_year)) +
      summary
    }</table><p class="card-note"><strong>Nearby-area context:</strong> each radius is a circle around the clicked point. It summarises overlapping 1 km cells; it is not a second grid, a property assessment, or a separate prediction.</p><div class="highlight-guide"><span><i class="highlight-dot highlight-selected"></i>Selected cell</span><span><i class="highlight-dot highlight-three"></i>Within 3 km</span><span><i class="highlight-dot highlight-five"></i>3&ndash;5 km</span></div>`;
  }

  function style(feature) {
    const tier = highlightTiers.get(feature.properties.cell_id);
    if (tier === "selected") return { color: "#fff7b0", weight: 2.4, opacity: 1, fillColor: "#f7d64a", fillOpacity: 0.72 };
    if (tier === "three") return { color: "#3fc0dc", weight: 1.2, opacity: 1, fillColor: "#3fc0dc", fillOpacity: 0.50 };
    if (tier === "five") return { color: "#3177a5", weight: 1.0, opacity: 1, fillColor: "#3177a5", fillOpacity: 0.36 };
    return { color: "#4a4a4a", weight: 0.15, opacity: 0.65, fillColor: colors[feature.properties.exposure_band_code], fillOpacity: exposureOpacity };
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
    defaultSelection();
  });
  defaultSelection();

  fetch("/v1/map/2026/cells.geojson")
    .then((response) => response.ok ? response.json() : response.json().then((body) => Promise.reject(new Error(body.detail || "Map asset is unavailable."))))
    .then((data) => {
      const cells = L.geoJSON(data, {
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
