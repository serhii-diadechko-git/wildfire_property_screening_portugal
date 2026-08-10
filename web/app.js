/* Local presentation client. It reads a derived 2026 map asset and queries the
 * same-origin read-only API for click context; no model work occurs in the browser. */
(() => {
  "use strict";
  const colors = { lower: "#ead9a0", intermediate: "#eca900", higher: "#a6222a" };
  const map = L.map("map", { preferCanvas: true, zoomControl: true, minZoom: 5, maxZoom: 13 });
  let exposureOpacity = 0.82;
  const standard = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© <a href=\"https://www.openstreetmap.org/copyright\" target=\"_blank\" rel=\"noopener\">OpenStreetMap contributors</a>",
  });
  const humanitarian = L.tileLayer("https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© <a href=\"https://www.openstreetmap.org/copyright\" target=\"_blank\" rel=\"noopener\">OpenStreetMap contributors</a>, tiles style by <a href=\"https://www.hotosm.org/\" target=\"_blank\" rel=\"noopener\">Humanitarian OpenStreetMap Team</a>",
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

  function popupHtml(properties, context) {
    const summary = context ? context.context_buffers.map((item) =>
      row(`${item.radius_km} km radius`, `${item.intersecting_cell_count} nearby cells; average estimate ${percent(item.mean_predicted_burned_share_next_year)}; ${percent(item.higher_estimated_exposure_area_share, 1)} of this nearby area is in the higher band`)
    ).join("") : row("Nearby-area context", "Loading summaries for circles around this point…");
    return `<div class="popup-title">2026 comparative exposure</div><table class="popup-table">${
      row("Cell ID", text(properties.cell_id)) +
      row("Band", text(properties.estimated_comparative_exposure_band)) +
      row("Estimated burned share", percent(properties.predicted_burned_share_next_year)) +
      row("Predictor inputs", text(properties.prediction_input_year)) +
      summary
    }</table><p class="popup-note"><strong>Nearby-area context:</strong> each radius is a circle around the clicked point, summarising overlapping 1 km cells. It is not a second grid, a property assessment, or a separate prediction.</p>`;
  }

  function style(feature) {
    const code = feature.properties.exposure_band_code;
    return { color: "#4a4a4a", weight: 0.15, opacity: 0.65, fillColor: colors[code], fillOpacity: exposureOpacity };
  }

  function popupOffsetFor(latlng) {
    const point = map.latLngToContainerPoint(latlng);
    // Keep the detail panel to the right when it fits; open to the left near the right edge.
    return point.x > map.getSize().x - 360 ? [-340, 0] : [26, 0];
  }

  fetch("/v1/map/2026/cells.geojson")
    .then((response) => response.ok ? response.json() : response.json().then((body) => Promise.reject(new Error(body.detail || "Map asset is unavailable."))))
    .then((data) => {
      const cells = L.geoJSON(data, {
        renderer: L.canvas({ padding: 0.25 }),
        style,
        onEachFeature(feature, layer) {
          layer.on({
            mouseover: () => layer.setStyle({ weight: 0.8, color: "#15243a" }),
            mouseout: () => layer.setStyle(style(feature)),
            click: (event) => {
              const popup = L.popup({
                autoPan: true,
                autoPanPadding: [24, 24],
                closeButton: true,
                maxWidth: 360,
                minWidth: 300,
                offset: popupOffsetFor(event.latlng),
              }).setLatLng(event.latlng).setContent(popupHtml(feature.properties)).openOn(map);
              const query = new URLSearchParams({ longitude: event.latlng.lng.toFixed(6), latitude: event.latlng.lat.toFixed(6), buffers_km: "1,3,5" });
              fetch(`/v1/exposure?${query}`)
                .then((response) => response.ok ? response.json() : null)
                .then((context) => popup.setContent(popupHtml(feature.properties, context)))
                .catch(() => popup.setContent(popupHtml(feature.properties)));
            },
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
      document.querySelector(".explanation").insertAdjacentHTML("afterbegin", `<p><strong>Map unavailable:</strong> ${text(error.message)} Run <code>python scripts/build_web_map_assets.py</code> after the documented reproduction workflow.</p>`);
      map.setView([39.6, -8.0], 6);
    });
})();
