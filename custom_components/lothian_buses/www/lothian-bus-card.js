/*!
 * Lothian Buses & Edinburgh Trams — Minimalist Mushroom Card for Home Assistant
 * Domain: lothian_buses
 * Card type: custom:lothian-bus-card
 */

const DOMAIN = "lothian_buses";
const VERSION = "0.1.0";

const DEFAULT_CONFIG = {
  title: "",
  routes: [],
  max_departures: 6,
  compact: false,
  show_header: true,
  show_route_filter: true,
  show_vehicle_info: true,
  show_clock: true,
};

const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[c]
  );

function bearingToCompass(deg) {
  if (deg === null || deg === undefined || Number.isNaN(Number(deg))) return "";
  const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return dirs[Math.round(((Number(deg) % 360) + 360) % 360 / 45) % 8];
}

const BUS_SVG = `<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M18 11H6V6h12m-1.5 11a1.5 1.5 0 0 1-1.5-1.5 1.5 1.5 0 0 1 1.5-1.5 1.5 1.5 0 0 1 1.5 1.5 1.5 1.5 0 0 1-1.5 1.5m-9 0A1.5 1.5 0 0 1 6 15.5 1.5 1.5 0 0 1 7.5 14 1.5 1.5 0 0 1 9 15.5 1.5 1.5 0 0 1 7.5 17M4 16c0 .88.39 1.67 1 2.22V20a1 1 0 0 0 1 1h1a1 1 0 0 0 1-1v-1h8v1a1 1 0 0 0 1 1h1a1 1 0 0 0 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10Z"/></svg>`;
const TRAM_SVG = `<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M19 16.94V8.5c0-2.79-2.61-3.4-6.01-3.49l.76-1.51H17V2H7v1.5h4.75l-.76 1.52C7.86 5.11 5 5.73 5 8.5v8.44c0 1.45 1.19 2.66 2.59 2.97L6 21.5v.5h2.23l2-2H14l2 2h2v-.5L16.5 20h-.08c1.69 0 2.58-1.37 2.58-3.06m-7 1.56a1.5 1.5 0 0 1-1.5-1.5 1.5 1.5 0 0 1 1.5-1.5 1.5 1.5 0 0 1 1.5 1.5 1.5 1.5 0 0 1-1.5 1.5m5-4.5H7V9h10v5Z"/></svg>`;
const LIVE_WAVE_SVG = `<svg class="live-icon" viewBox="0 0 16 16" width="12" height="12" fill="currentColor"><circle cx="4" cy="12" r="2"/><path d="M4 7a5 5 0 0 1 5 5h2a7 7 0 0 0-7-7v2Zm0-4a9 9 0 0 1 9 9h2A11 11 0 0 0 4 1v2Z"/></svg>`;

const CARD_STYLES = `
  :host {
    display: block;
    --lb-radius: var(--ha-card-border-radius, 16px);
    --lb-bg: var(--ha-card-background, var(--card-background-color, #1c1c1e));
    --lb-text: var(--primary-text-color, #f5f5f7);
    --lb-subtext: var(--secondary-text-color, #98989f);
    --lb-divider: var(--divider-color, rgba(128, 128, 128, 0.14));
    --lb-surface: rgba(128, 128, 128, 0.08);
    --lb-surface-hover: rgba(128, 128, 128, 0.14);
    --lb-live: var(--success-color, #2ecc71);
    --lb-warn: var(--warning-color, #f39c12);
    --lb-accent: var(--primary-color, #03a9f4);
  }
  ha-card {
    background: var(--lb-bg);
    border-radius: var(--lb-radius);
    color: var(--lb-text);
    padding: 14px;
    box-sizing: border-box;
    overflow: hidden;
  }
  .header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }
  .avatar {
    position: relative;
    width: 42px;
    height: 42px;
    border-radius: 50%;
    background: rgba(133, 25, 60, 0.16);
    color: #e0456b;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .avatar.tram {
    background: rgba(148, 147, 148, 0.2);
    color: #b8b8b8;
  }
  .avatar-dot {
    position: absolute;
    bottom: 1px;
    right: 1px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--lb-live);
    border: 2px solid var(--lb-bg);
  }
  .header-main {
    flex: 1;
    min-width: 0;
  }
  .title-row {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .title {
    font-size: 16px;
    font-weight: 600;
    line-height: 1.25;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .meta-pill {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 999px;
    background: var(--lb-surface);
    color: var(--lb-subtext);
    letter-spacing: 0.02em;
  }
  .subtitle {
    font-size: 12px;
    color: var(--lb-subtext);
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .clock-chip {
    font-size: 12px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    padding: 4px 9px;
    border-radius: 999px;
    background: var(--lb-surface);
    color: var(--lb-subtext);
    flex-shrink: 0;
  }
  .filter-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    overflow-x: auto;
    padding-bottom: 4px;
    margin-bottom: 10px;
    scrollbar-width: none;
  }
  .filter-bar::-webkit-scrollbar {
    display: none;
  }
  .filter-chip {
    border: none;
    cursor: pointer;
    font-family: inherit;
    font-size: 12px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 999px;
    background: var(--lb-surface);
    color: var(--lb-subtext);
    transition: transform 0.12s ease, opacity 0.12s ease, box-shadow 0.12s ease;
    flex-shrink: 0;
  }
  .filter-chip:hover {
    transform: translateY(-1px);
  }
  .filter-chip.active {
    box-shadow: 0 0 0 2px var(--lb-text) inset;
    color: var(--lb-text);
  }
  .filter-chip.route-filter {
    opacity: 0.55;
  }
  .filter-chip.route-filter.active {
    opacity: 1;
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.85) inset;
  }
  .departures {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .dep-item {
    border-radius: 12px;
    background: var(--lb-surface);
    transition: background 0.15s ease;
    overflow: hidden;
  }
  .dep-row {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 9px 11px;
    cursor: pointer;
    user-select: none;
  }
  .dep-row.compact {
    padding: 6px 10px;
  }
  .dep-row:hover {
    background: var(--lb-surface-hover);
  }
  .route-pill {
    min-width: 44px;
    height: 30px;
    padding: 0 9px;
    border-radius: 9px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.01em;
    box-sizing: border-box;
    flex-shrink: 0;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.18);
  }
  .dep-row.compact .route-pill {
    min-width: 38px;
    height: 24px;
    font-size: 12px;
    border-radius: 7px;
  }
  .dep-info {
    flex: 1;
    min-width: 0;
  }
  .dest-line {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
  }
  .dest {
    font-size: 14px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .dep-row.compact .dest {
    font-size: 13px;
  }
  .warn-badge {
    font-size: 10px;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 6px;
    background: rgba(243, 156, 18, 0.18);
    color: var(--lb-warn);
    flex-shrink: 0;
    text-transform: uppercase;
  }
  .sub-line {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 2px;
    font-size: 11.5px;
    color: var(--lb-subtext);
    flex-wrap: wrap;
  }
  .veh-badge {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 6px;
    background: rgba(128, 128, 128, 0.12);
    color: var(--lb-text);
    font-size: 11px;
  }
  .eta-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    background: rgba(128, 128, 128, 0.12);
    color: var(--lb-text);
    flex-shrink: 0;
  }
  .eta-chip.live {
    background: rgba(46, 204, 113, 0.15);
    color: var(--lb-live);
  }
  .eta-chip.due {
    background: var(--lb-live);
    color: #fff;
    animation: pulse-due 1.8s infinite ease-in-out;
  }
  @keyframes pulse-due {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.78; }
  }
  .live-icon {
    opacity: 0.9;
  }
  .chevron {
    font-size: 11px;
    color: var(--lb-subtext);
    transition: transform 0.2s ease;
    margin-left: 2px;
  }
  .chevron.open {
    transform: rotate(180deg);
  }
  /* Interactive Trip Progress Drawer */
  .drawer {
    border-top: 1px solid var(--lb-divider);
    padding: 10px 12px 12px;
    background: rgba(0, 0, 0, 0.12);
    font-size: 12px;
  }
  .drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--lb-divider);
  }
  .drawer-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    color: var(--lb-subtext);
    font-size: 11.5px;
  }
  .drawer-meta strong {
    color: var(--lb-text);
  }
  .drawer-btn {
    border: none;
    background: var(--lb-surface-hover);
    color: var(--lb-text);
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 6px;
    cursor: pointer;
  }
  .timeline {
    display: flex;
    flex-direction: column;
    max-height: 230px;
    overflow-y: auto;
    padding-right: 4px;
  }
  .tl-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 6px;
    border-radius: 8px;
    position: relative;
  }
  .tl-row.passed {
    opacity: 0.48;
  }
  .tl-row.current-stop {
    background: rgba(3, 169, 244, 0.15);
    font-weight: 700;
  }
  .tl-row.bus-here {
    background: rgba(46, 204, 113, 0.15);
  }
  .tl-dot-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 14px;
    flex-shrink: 0;
  }
  .tl-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--lb-subtext);
  }
  .tl-row.passed .tl-dot {
    background: var(--lb-subtext);
    width: 6px;
    height: 6px;
  }
  .tl-row.current-stop .tl-dot {
    background: var(--lb-accent);
    width: 10px;
    height: 10px;
    box-shadow: 0 0 0 3px rgba(3, 169, 244, 0.28);
  }
  .tl-row.bus-here .tl-dot {
    background: var(--lb-live);
    width: 10px;
    height: 10px;
    box-shadow: 0 0 0 3px rgba(46, 204, 113, 0.3);
  }
  .tl-name {
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .tl-tag {
    font-size: 10px;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 999px;
    background: var(--lb-accent);
    color: #fff;
    flex-shrink: 0;
  }
  .tl-tag.bus {
    background: var(--lb-live);
  }
  .tl-time {
    font-variant-numeric: tabular-nums;
    font-size: 11.5px;
    color: var(--lb-subtext);
    flex-shrink: 0;
  }
  .empty {
    text-align: center;
    padding: 18px 12px;
    color: var(--lb-subtext);
    font-size: 13px;
    background: var(--lb-surface);
    border-radius: 12px;
  }
`;

class LothianBusCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("lothian-bus-card-editor");
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass?.states || {}).find(
      (id) => id.startsWith("sensor.") && hass.states[id]?.attributes?.stop_id
    );
    return {
      type: "custom:lothian-bus-card",
      entity: entity || "",
    };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = { ...DEFAULT_CONFIG };
    this._hass = null;
    this._activeRouteFilter = null; // null = use config filter or all
    this._expandedKey = null; // journey_id or vehicle_id currently expanded
    this._tripProgress = {}; // key -> { loading, error, stops, vehicle, showAllPassed }
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = { ...DEFAULT_CONFIG, ...config };
    this._activeRouteFilter = null;
    this._render();
  }

  set hass(hass) {
    const oldState = this._hass?.states?.[this._config?.entity];
    this._hass = hass;
    const newState = hass?.states?.[this._config?.entity];
    if (oldState !== newState) {
      this._render();
    }
  }

  getCardSize() {
    return this._config?.compact ? 3 : 4;
  }

  _depKey(dep) {
    return `${dep.journey_id || ""}_${dep.vehicle_id || ""}_${dep.route}_${dep.departure_time}`;
  }

  async _toggleTripProgress(dep) {
    const key = this._depKey(dep);
    if (this._expandedKey === key) {
      this._expandedKey = null;
      this._render();
      return;
    }
    this._expandedKey = key;
    if (!dep.vehicle_id && !dep.journey_id) {
      this._tripProgress[key] = {
        loading: false,
        error: "No live vehicle or trip ID assigned to this scheduled departure yet.",
        stops: [],
      };
      this._render();
      return;
    }
    await this._fetchTripProgress(dep, key);
  }

  async _fetchTripProgress(dep, key) {
    const stateObj = this._hass?.states?.[this._config?.entity];
    const stopId = stateObj?.attributes?.stop_id;
    this._tripProgress[key] = { loading: true, error: null, stops: [], vehicle: null };
    this._render();

    try {
      const res = await this._hass.callWS({
        type: `${DOMAIN}/trip_progress`,
        vehicle_id: dep.vehicle_id || null,
        journey_id: dep.journey_id || null,
        stop_id: stopId || null,
      });
      this._tripProgress[key] = {
        loading: false,
        error: null,
        stops: res.stops || [],
        vehicle: res.vehicle || null,
        showAllPassed: false,
      };
    } catch (err) {
      this._tripProgress[key] = {
        loading: false,
        error: err?.message || "Could not load live trip progress.",
        stops: [],
      };
    }
    this._render();
  }

  _renderDrawer(dep, currentStopId) {
    const key = this._depKey(dep);
    const prog = this._tripProgress[key];
    if (!prog) return "";

    if (prog.loading) {
      return `<div class="drawer"><div class="drawer-meta">Loading live stop-by-stop progress…</div></div>`;
    }
    if (prog.error) {
      return `<div class="drawer"><div class="drawer-meta">${esc(prog.error)}</div></div>`;
    }

    const stops = prog.stops || [];
    const veh = prog.vehicle;
    const compass = veh?.bearing !== undefined && veh?.bearing !== null ? bearingToCompass(veh.bearing) : "";

    // Find the first unpassed stop (where the vehicle currently is approaching)
    const firstUnpassedIdx = stops.findIndex((s) => !s.passed);
    const busAtIdx = firstUnpassedIdx > 0 ? firstUnpassedIdx - 1 : firstUnpassedIdx;

    // Keep passed stops concise unless user clicks "Show earlier stops"
    const hideBeforeIdx = !prog.showAllPassed && busAtIdx > 2 ? busAtIdx - 1 : 0;
    const hiddenCount = hideBeforeIdx;
    const visibleStops = stops.slice(hideBeforeIdx);

    const rowsHtml = visibleStops
      .map((s, idx) => {
        const realIdx = idx + hideBeforeIdx;
        const isCurrentStop = String(s.stop_id) === String(currentStopId);
        const isBusHere = realIdx === busAtIdx;
        const cls = [
          "tl-row",
          s.passed && !isBusHere ? "passed" : "",
          isCurrentStop ? "current-stop" : "",
          isBusHere ? "bus-here" : "",
        ]
          .filter(Boolean)
          .join(" ");

        const minsText =
          s.minutes <= 0
            ? s.passed
              ? s.time
              : "Due"
            : `${s.time} (${s.minutes}m)`;

        return `<div class="${cls}">
          <div class="tl-dot-col"><div class="tl-dot"></div></div>
          <div class="tl-name">${esc(s.stop_name)}</div>
          ${isBusHere ? `<span class="tl-tag bus">${dep.mode === "tram" ? "🚊 TRAM HERE" : "🚌 BUS HERE"}</span>` : ""}
          ${isCurrentStop ? `<span class="tl-tag">THIS STOP</span>` : ""}
          <div class="tl-time">${esc(minsText)}</div>
        </div>`;
      })
      .join("");

    return `<div class="drawer" data-key="${esc(key)}">
      <div class="drawer-header">
        <div class="drawer-meta">
          ${veh?.id ? `<span>Vehicle <strong>#${esc(veh.id)}</strong></span>` : ""}
          ${veh?.speed !== undefined && veh?.speed !== null ? `<span>• <strong>${esc(veh.speed)} mph</strong>${compass ? ` ${esc(compass)}` : ""}</span>` : ""}
          <span>• ${stops.length} stops on journey</span>
        </div>
        <button class="drawer-btn refresh-prog" data-key="${esc(key)}">↻ Refresh</button>
      </div>
      ${
        hiddenCount > 0
          ? `<button class="drawer-btn show-passed" data-key="${esc(key)}" style="margin-bottom:6px;width:100%">Show ${hiddenCount} earlier passed stops ↑</button>`
          : ""
      }
      <div class="timeline">${rowsHtml || `<div class="drawer-meta">No stop progress reported.</div>`}</div>
    </div>`;
  }

  _render() {
    if (!this.shadowRoot) return;
    const entityId = this._config?.entity;
    const stateObj = entityId ? this._hass?.states?.[entityId] : null;

    if (!entityId || !stateObj) {
      this.shadowRoot.innerHTML = `
        <style>${CARD_STYLES}</style>
        <ha-card>
          <div class="empty">
            ${
              !entityId
                ? "Select a Lothian Buses or Edinburgh Trams stop in the card editor."
                : `Waiting for stop sensor <strong>${esc(entityId)}</strong>…`
            }
          </div>
        </ha-card>
      `;
      return;
    }

    const attrs = stateObj.attributes || {};
    const allDeps = Array.isArray(attrs.departures) ? attrs.departures : [];
    const lines = Array.isArray(attrs.lines) ? attrs.lines : [];
    const modes = Array.isArray(attrs.modes) ? attrs.modes : ["bus"];
    const isTramOnly = modes.length === 1 && modes[0] === "tram";

    const configuredRoutes = Array.isArray(this._config.routes)
      ? this._config.routes.map((r) => String(r).trim()).filter(Boolean)
      : String(this._config.routes || "")
          .split(",")
          .map((r) => r.trim())
          .filter(Boolean);

    // Determine active route filter
    let filteredDeps = allDeps;
    if (this._activeRouteFilter) {
      filteredDeps = allDeps.filter((d) => d.route === this._activeRouteFilter);
    } else if (configuredRoutes.length > 0) {
      const allowed = new Set(configuredRoutes.map((r) => r.toLowerCase()));
      filteredDeps = allDeps.filter((d) => allowed.has(String(d.route).toLowerCase()));
    }

    const maxDeps = Number(this._config.max_departures) || 6;
    const shownDeps = filteredDeps.slice(0, maxDeps);

    const title = this._config.title || attrs.stop_name || stateObj.attributes.friendly_name || "Lothian Stop";
    const identifier = attrs.identifier ? `Stop ${attrs.identifier}` : "";
    const direction = attrs.direction ? `→ ${attrs.direction}` : "";
    const subParts = [attrs.street, attrs.locality, attrs.stop_id ? `#${attrs.stop_id}` : ""].filter(Boolean);
    const nowTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // Build interactive route filter pills if enabled and stop has >1 route
    const availableLines =
      configuredRoutes.length > 0
        ? lines.filter((l) => configuredRoutes.some((r) => r.toLowerCase() === String(l.name).toLowerCase()))
        : lines;

    const filterBarHtml =
      this._config.show_route_filter && availableLines.length > 1
        ? `<div class="filter-bar">
            <button class="filter-chip ${!this._activeRouteFilter ? "active" : ""}" data-route="">All</button>
            ${availableLines
              .map(
                (l) => `<button
                  class="filter-chip route-filter ${this._activeRouteFilter === l.name ? "active" : ""}"
                   data-route="${esc(l.name)}"
                  style="background:${esc(l.color)};color:${esc(l.text_color)}"
                >${esc(l.name)}</button>`
              )
              .join("")}
          </div>`
        : "";

    const rowsHtml = shownDeps.length
      ? shownDeps
          .map((dep, idx) => {
            const key = this._depKey(dep);
            const isOpen = this._expandedKey === key;
            const isDue = dep.minutes <= 0;
            const etaText = isDue
              ? "Due"
              : dep.real_time || dep.minutes <= 60
              ? `${dep.minutes} min`
              : dep.departure_time;
            const etaClass = isDue ? "eta-chip due" : dep.real_time ? "eta-chip live" : "eta-chip";
            const compass =
              dep.vehicle_bearing !== null && dep.vehicle_bearing !== undefined
                ? bearingToCompass(dep.vehicle_bearing)
                : "";

            const subLineHtml = !this._config.compact
              ? `<div class="sub-line">
                  ${dep.departure_time ? `<span>Sched ${esc(dep.departure_time)}</span>` : ""}
                  ${
                    this._config.show_vehicle_info && dep.vehicle_id
                      ? `<span class="veh-badge">${dep.mode === "tram" ? "🚊" : "🚌"} #${esc(dep.vehicle_id)}${
                          dep.vehicle_speed ? ` · ${esc(dep.vehicle_speed)} mph ${esc(compass)}` : ""
                        }</span>`
                      : ""
                  }
                  <span>${dep.real_time ? "Live GPS" : "Timetable"}</span>
                </div>`
              : "";

            return `<div class="dep-item">
              <div class="dep-row ${this._config.compact ? "compact" : ""}" data-idx="${idx}">
                <span class="route-pill" style="background:${esc(dep.route_color)};color:${esc(dep.route_text_color)}">
                  ${esc(dep.route)}
                </span>
                <div class="dep-info">
                  <div class="dest-line">
                    <span class="dest">${esc(dep.destination)}</span>
                    ${dep.diverted ? `<span class="warn-badge">Diverted</span>` : ""}
                    ${dep.part_route ? `<span class="warn-badge">Part route</span>` : ""}
                  </div>
                  ${subLineHtml}
                </div>
                <div class="${etaClass}">
                  ${dep.real_time && !isDue ? LIVE_WAVE_SVG : ""}
                  <span>${esc(etaText)}</span>
                </div>
                <span class="chevron ${isOpen ? "open" : ""}">▾</span>
              </div>
              ${isOpen ? this._renderDrawer(dep, attrs.stop_id) : ""}
            </div>`;
          })
          .join("")
      : `<div class="empty">No upcoming departures${
          this._activeRouteFilter ? ` for route ${esc(this._activeRouteFilter)}` : ""
        }.</div>`;

    this.shadowRoot.innerHTML = `
      <style>${CARD_STYLES}</style>
      <ha-card>
        ${
          this._config.show_header
            ? `<div class="header">
                <div class="avatar ${isTramOnly ? "tram" : ""}">
                  ${isTramOnly ? TRAM_SVG : BUS_SVG}
                  <div class="avatar-dot"></div>
                </div>
                <div class="header-main">
                  <div class="title-row">
                    <span class="title">${esc(title)}</span>
                    ${identifier ? `<span class="meta-pill">${esc(identifier)}</span>` : ""}
                    ${direction ? `<span class="meta-pill">${esc(direction)}</span>` : ""}
                  </div>
                  ${subParts.length ? `<div class="subtitle">${esc(subParts.join(" · "))}</div>` : ""}
                </div>
                ${this._config.show_clock ? `<div class="clock-chip">${esc(nowTime)}</div>` : ""}
              </div>`
            : ""
        }
        ${filterBarHtml}
        <div class="departures">${rowsHtml}</div>
      </ha-card>
    `;

    // Bind filter chips
    this.shadowRoot.querySelectorAll(".filter-chip").forEach((btn) => {
      btn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const route = btn.dataset.route || null;
        this._activeRouteFilter = this._activeRouteFilter === route ? null : route;
        this._render();
      });
    });

    // Bind departure row click -> expand live trip progress
    this.shadowRoot.querySelectorAll(".dep-row").forEach((row) => {
      row.addEventListener("click", () => {
        const idx = Number(row.dataset.idx);
        const dep = shownDeps[idx];
        if (dep) this._toggleTripProgress(dep);
      });
    });

    // Bind drawer refresh & show passed buttons
    this.shadowRoot.querySelectorAll(".refresh-prog").forEach((btn) => {
      btn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const key = btn.dataset.key;
        const dep = shownDeps.find((d) => this._depKey(d) === key);
        if (dep) this._fetchTripProgress(dep, key);
      });
    });

    this.shadowRoot.querySelectorAll(".show-passed").forEach((btn) => {
      btn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const key = btn.dataset.key;
        if (this._tripProgress[key]) {
          this._tripProgress[key].showAllPassed = true;
          this._render();
        }
      });
    });
  }
}

/* ============================================================================
 * Visual Card Editor (Live Stop Search + Route Filter Chips + HA Form)
 * ========================================================================== */

const EDITOR_STYLES = `
  .search-box {
    border: 1px solid var(--divider-color, #444);
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 16px;
    background: var(--card-background-color, transparent);
  }
  .section-title {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 6px;
  }
  input[type="search"] {
    width: 100%;
    box-sizing: border-box;
    padding: 9px 12px;
    border: 1px solid var(--divider-color, #555);
    border-radius: 8px;
    background: var(--ha-card-background, var(--card-background-color, #fff));
    color: var(--primary-text-color);
    font: inherit;
    font-size: 14px;
  }
  .hint {
    font-size: 12px;
    color: var(--secondary-text-color);
    margin-top: 5px;
  }
  .status {
    font-size: 12px;
    color: var(--secondary-text-color);
    margin-top: 6px;
  }
  .status.err {
    color: var(--error-color, #db4437);
  }
  .results {
    max-height: 280px;
    overflow-y: auto;
    margin-top: 6px;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .item {
    display: block;
    width: 100%;
    text-align: left;
    padding: 9px 11px;
    border: 1px solid var(--divider-color, #444);
    border-radius: 10px;
    background: transparent;
    color: var(--primary-text-color);
    font: inherit;
    cursor: pointer;
  }
  .item:hover {
    background: var(--secondary-background-color, rgba(127, 127, 127, 0.12));
  }
  .item.selected {
    border-color: var(--primary-color, #03a9f4);
  }
  .top-line {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .name {
    font-weight: 600;
    font-size: 13.5px;
  }
  .meta {
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 999px;
    background: rgba(127, 127, 127, 0.16);
    color: var(--secondary-text-color);
  }
  .added {
    font-size: 11px;
    color: var(--success-color, #2ecc71);
    margin-left: auto;
    font-weight: 600;
  }
  .sub {
    font-size: 12px;
    color: var(--secondary-text-color);
    margin-top: 2px;
  }
  .badges {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 6px;
  }
  .badge {
    font-size: 11px;
    font-weight: 700;
    padding: 1px 7px;
    border-radius: 6px;
    line-height: 1.4;
  }
  .route-picker {
    border: 1px solid var(--divider-color, #444);
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 16px;
  }
  .route-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;
  }
  .route-chip {
    border: none;
    cursor: pointer;
    font-size: 12px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 8px;
    opacity: 0.45;
    transition: opacity 0.12s ease, transform 0.12s ease;
  }
  .route-chip.selected {
    opacity: 1;
    box-shadow: 0 0 0 2px var(--primary-text-color) inset;
  }
`;

const FORM_LABELS = {
  entity: "Stop sensor entity",
  title: "Card title (optional, defaults to stop name)",
  max_departures: "Maximum departures shown",
  compact: "Compact single-line rows",
  show_header: "Show card header",
  show_route_filter: "Show interactive route filter pills in header",
  show_vehicle_info: "Show bus/tram fleet number & live speed",
  show_clock: "Show clock in header",
};

class LothianBusCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._stops = [];
    this._timer = null;
    this._seq = 0;
  }

  setConfig(config) {
    this._config = { ...DEFAULT_CONFIG, ...config };
    this._ensureDom();
    this._refreshForm();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) {
      this._form.hass = hass;
      this._refreshForm();
    }
  }

  _ensureDom() {
    if (this._input) return;
    this.shadowRoot.innerHTML = `
      <style>${EDITOR_STYLES}</style>
      <div class="search-box">
        <div class="section-title">Find a Lothian Bus or Edinburgh Tram stop</div>
        <input type="search" autocomplete="off" placeholder="Search e.g. Princes Street, Haymarket, Clerwood, 26, or 36238285" />
        <div class="hint">Click any stop below: if it isn't added yet, it will be added to the integration automatically.</div>
        <div class="status"></div>
        <div class="results"></div>
      </div>
      <div class="route-picker" style="display:none">
        <div class="section-title">Filter routes on this card (empty = show all routes)</div>
        <div class="route-chips"></div>
      </div>
      <ha-form></ha-form>
    `;
    this._input = this.shadowRoot.querySelector("input");
    this._status = this.shadowRoot.querySelector(".status");
    this._results = this.shadowRoot.querySelector(".results");
    this._routePicker = this.shadowRoot.querySelector(".route-picker");
    this._routeChips = this.shadowRoot.querySelector(".route-chips");
    this._form = this.shadowRoot.querySelector("ha-form");
    this._form.computeLabel = (s) => FORM_LABELS[s.name] || s.name;
    this._form.hass = this._hass;

    this._form.addEventListener("value-changed", (ev) => {
      ev.stopPropagation();
      this._updateConfig({ ...this._config, ...ev.detail.value });
    });

    this._input.addEventListener("input", () => {
      clearTimeout(this._timer);
      this._timer = setTimeout(() => this._search(), 250);
    });
  }

  _setStatus(text, isErr = false) {
    if (!this._status) return;
    this._status.textContent = text || "";
    this._status.classList.toggle("err", !!isErr);
  }

  async _search() {
    const q = this._input.value.trim();
    const seq = ++this._seq;
    if (q.length < 2) {
      this._results.innerHTML = "";
      this._setStatus(q.length ? "Type at least 2 characters…" : "");
      return;
    }
    this._setStatus("Searching Edinburgh & Lothians stops…");
    try {
      const res = await this._hass.callWS({ type: `${DOMAIN}/search`, query: q });
      if (seq !== this._seq) return;
      const stops = res.stops || [];
      this._renderResults(stops);
      this._setStatus(
        stops.length
          ? `${stops.length} matching stop${stops.length === 1 ? "" : "s"}`
          : "No stops matched. Try a street name or 8-digit stop code."
      );
    } catch (err) {
      if (seq !== this._seq) return;
      this._results.innerHTML = "";
      this._setStatus(err?.message || "Search failed.", true);
    }
  }

  _renderResults(stops) {
    this._stops = stops;
    this._results.innerHTML = stops
      .map((s, i) => {
        const badges = (s.lines || [])
          .slice(0, 18)
          .map(
            (l) =>
              `<span class="badge" style="background:${esc(l.color)};color:${esc(l.text_color)}">${esc(
                l.name
              )}</span>`
          )
          .join("");
        const subParts = [s.street, s.locality, `#${s.id}`].filter(Boolean);
        const isSelected = s.entity_id && s.entity_id === this._config?.entity;
        const icon = (s.modes || []).includes("tram") ? "🚊" : "🚌";

        return `<button class="item ${isSelected ? "selected" : ""}" data-i="${i}">
          <div class="top-line">
            <span>${icon}</span>
            <span class="name">${esc(s.name)}</span>
            ${s.indicator ? `<span class="meta">${esc(s.indicator)}</span>` : ""}
            ${s.direction ? `<span class="meta">→ ${esc(s.direction)}</span>` : ""}
            ${s.added ? `<span class="added">✓ Added</span>` : ""}
          </div>
          <div class="sub">${esc(subParts.join(" · "))}</div>
          ${badges ? `<div class="badges">${badges}</div>` : ""}
        </button>`;
      })
      .join("");

    this._results.querySelectorAll(".item").forEach((btn) => {
      btn.addEventListener("click", () => this._pickStop(this._stops[Number(btn.dataset.i)]));
    });
  }

  async _pickStop(stop) {
    try {
      let entityId = stop.entity_id;
      if (!stop.added || !entityId) {
        this._setStatus(`Adding ${stop.name}…`);
        const res = await this._hass.callWS({ type: `${DOMAIN}/add_stop`, stop_id: stop.id });
        entityId = res.entity_id;
        stop.added = true;
        stop.entity_id = entityId;
      }
      this._updateConfig({ ...this._config, entity: entityId, routes: [] });
      this._setStatus(`Selected: ${stop.name}`);
      this._renderResults(this._stops);
    } catch (err) {
      this._setStatus(err?.message || "Could not add stop.", true);
    }
  }

  _refreshForm() {
    if (!this._form) return;
    const stateObj = this._config?.entity ? this._hass?.states?.[this._config.entity] : null;
    const lines = stateObj?.attributes?.lines || [];

    if (lines.length > 1) {
      this._routePicker.style.display = "block";
      const selectedRoutes = new Set(
        (Array.isArray(this._config.routes) ? this._config.routes : []).map((r) => String(r))
      );
      this._routeChips.innerHTML = lines
        .map(
          (l) => `<button
            type="button"
            class="route-chip ${selectedRoutes.has(l.name) ? "selected" : ""}"
            data-route="${esc(l.name)}"
            style="background:${esc(l.color)};color:${esc(l.text_color)}"
          >${esc(l.name)}</button>`
        )
        .join("");

      this._routeChips.querySelectorAll(".route-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
          const r = chip.dataset.route;
          const next = new Set(Array.isArray(this._config.routes) ? this._config.routes : []);
          if (next.has(r)) next.delete(r);
          else next.add(r);
          this._updateConfig({ ...this._config, routes: [...next] });
        });
      });
    } else {
      this._routePicker.style.display = "none";
    }

    this._form.schema = [
      {
        name: "entity",
        selector: { entity: { domain: "sensor", integration: DOMAIN, device_class: "duration" } },
      },
      { name: "title", selector: { text: {} } },
      { name: "max_departures", selector: { number: { min: 1, max: 20, mode: "slider" } } },
      { name: "compact", selector: { boolean: {} } },
      { name: "show_header", selector: { boolean: {} } },
      { name: "show_route_filter", selector: { boolean: {} } },
      { name: "show_vehicle_info", selector: { boolean: {} } },
      { name: "show_clock", selector: { boolean: {} } },
    ];
    this._form.data = { ...DEFAULT_CONFIG, ...this._config };
  }

  _updateConfig(nextConfig) {
    const clean = { type: "custom:lothian-bus-card" };
    for (const [k, v] of Object.entries(nextConfig)) {
      if (k === "type" || v === undefined || v === "") continue;
      if (Array.isArray(v) && v.length === 0) continue;
      if (k in DEFAULT_CONFIG && DEFAULT_CONFIG[k] === v) continue;
      clean[k] = v;
    }
    this._config = { ...DEFAULT_CONFIG, ...clean };
    this._refreshForm();
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: clean },
        bubbles: true,
        composed: true,
      })
    );
  }
}

if (!customElements.get("lothian-bus-card")) {
  customElements.define("lothian-bus-card", LothianBusCard);
}
if (!customElements.get("lothian-bus-card-editor")) {
  customElements.define("lothian-bus-card-editor", LothianBusCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "lothian-bus-card")) {
  window.customCards.push({
    type: "lothian-bus-card",
    name: "Lothian Buses & Edinburgh Trams Card",
    description:
      "Minimalist Mushroom-style live departure board with official Lothian route pills, live stop search, and interactive stop-by-stop trip progress.",
    preview: true,
    documentationURL: "https://github.com/vinodmishra/ha-lothianbuses",
    getEntitySuggestion: (hass, entityId) => {
      const attrs = hass?.states?.[entityId]?.attributes;
      if (!attrs?.stop_id || !Array.isArray(attrs?.departures)) return null;
      return { config: { type: "custom:lothian-bus-card", entity: entityId } };
    },
  });
}

console.info(
  `%c LOTHIAN BUSES & TRAMS %c v${VERSION} `,
  "color:#fff;background:#85193C;font-weight:700;padding:2px 6px;border-radius:4px 0 0 4px",
  "color:#85193C;background:#f5f5f7;font-weight:700;padding:2px 6px;border-radius:0 4px 4px 0"
);
