/* Local presentation client. It reads a derived 2026 map asset and queries the
 * same-origin read-only API for click context; no model work occurs in the browser. */
(() => {
  "use strict";
  const colors = { lower: "#ead9a0", intermediate: "#eca900", higher: "#a6222a" };
  const map = L.map("map", { preferCanvas: true, zoomControl: true, minZoom: 5, maxZoom: 13 });
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© <a href=\"https://www.openstreetmap.org/copyright\" target=\"_blank\" rel=\"noopener\">OpenStreetMap contributors</a>",
  }).addTo(map);

  const percent = (value, digits = 2) => `${(Number(value) * 100).toFixed(digits)}%`;
  const text = (value) => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", "\"": "&quot;" })[char]);
  const row = (name, value) => `<tr><td>${name}</td><td>${value}</td></tr>`;

  function popupHtml(properties, context) {
    const summary = context ? context.context_buffers.map((item) =>
      row(`${item.radius_km} km context`, `${percent(item.mean_predicted_burned_share_next_year)} mean estimate; ${percent(item.higher_estimated_exposure_area_share, 1)} higher-band area`)
    ).join("") : row("Context", "Loading local summaries…");
    return `<div class="popup-title">2026 comparative exposure</div><table class="popup-table">${
      row("Cell ID", text(properties.cell_id)) +
      row("Band", text(properties.estimated_comparative_exposure_band)) +
      row("Estimated burned share", percent(properties.predicted_burned_share_next_year)) +
      row("Predictor inputs", text(properties.prediction_input_year)) +
      summary
    }</table><p class="popup-note">A 1 km comparative screening cell, not a property-level forecast or safety rating.</p>`;
  }

  function style(feature) {
    const code = feature.properties.exposure_band_code;
    return { color: "#4a4a4a", weight: 0.15, opacity: 0.65, fillColor: colors[code], fillOpacity: 0.82 };
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
              layer.bindPopup(popupHtml(feature.properties)).openPopup(event.latlng);
              const query = new URLSearchParams({ longitude: event.latlng.lng.toFixed(6), latitude: event.latlng.lat.toFixed(6), buffers_km: "1,3,5" });
              fetch(`/v1/exposure?${query}`)
                .then((response) => response.ok ? response.json() : null)
                .then((context) => layer.setPopupContent(popupHtml(feature.properties, context)))
                .catch(() => layer.setPopupContent(popupHtml(feature.properties)));
            },
          });
        },
      }).addTo(map);
      map.fitBounds(cells.getBounds(), { padding: [14, 14] });
    })
    .catch((error) => {
      document.querySelector(".explanation").insertAdjacentHTML("afterbegin", `<p><strong>Map unavailable:</strong> ${text(error.message)} Run <code>python scripts/build_web_map_assets.py</code> after the documented reproduction workflow.</p>`);
      map.setView([39.6, -8.0], 6);
    });
})();
