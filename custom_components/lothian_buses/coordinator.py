"""DataUpdateCoordinator and shared live fleet cache for Lothian Buses & Edinburgh Trams."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LothianApi, LothianApiError
from .const import (
    CONF_DIRECTION,
    CONF_IDENTIFIER,
    CONF_LOCALITY,
    CONF_MODES,
    CONF_ROUTES,
    CONF_SCAN_INTERVAL,
    CONF_STOP_ID,
    CONF_STOP_NAME,
    CONF_STREET,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FLEET_CACHE_TTL,
    get_route_colors,
)
from .stops import get_stop_by_id

_LOGGER = logging.getLogger(__name__)


@dataclass
class FleetCache:
    """Shared live vehicle fleet cache (/vehicles/all) refreshed at most every FLEET_CACHE_TTL seconds."""

    api: LothianApi
    by_vehicle_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_trip_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    route_colors: dict[str, tuple[str, str]] = field(default_factory=dict)
    last_fetched: float = -1e9

    async def async_refresh_if_stale(self) -> None:
        """Refresh /vehicles/all if older than FLEET_CACHE_TTL seconds."""
        now = time.monotonic()
        if now - self.last_fetched < FLEET_CACHE_TTL:
            return
        try:
            payload = await self.api.get_all_vehicles()
            vehicles = payload.get("vehicles") or []
            by_vid: dict[str, dict[str, Any]] = {}
            by_tid: dict[str, dict[str, Any]] = {}
            for v in vehicles:
                if not isinstance(v, dict):
                    continue
                vid = str(v.get("id") or v.get("vehicleID") or "").strip()
                tid = str(v.get("tripID") or "").strip()
                rname = str(v.get("routeName") or "").strip()
                if vid:
                    by_vid[vid] = v
                if tid:
                    by_tid[tid] = v
                if rname and v.get("routeColor"):
                    bg = str(v["routeColor"]).strip()
                    fg = str(v.get("routeTextColor") or "#FFFFFF").strip()
                    if not bg.startswith("#"):
                        bg = f"#{bg}"
                    if not fg.startswith("#"):
                        fg = f"#{fg}"
                    self.route_colors[rname] = (bg, fg)
            self.by_vehicle_id = by_vid
            self.by_trip_id = by_tid
            self.last_fetched = now
        except LothianApiError as err:
            _LOGGER.debug("Live fleet cache refresh failed (non-fatal): %s", err)

    def match_vehicle(
        self, vehicle_id: str | None, journey_id: str | None
    ) -> dict[str, Any] | None:
        """Find a live vehicle by fleet ID or trip/journey ID."""
        if vehicle_id:
            vid = str(vehicle_id).strip()
            if vid in self.by_vehicle_id:
                return self.by_vehicle_id[vid]
        if journey_id:
            tid = str(journey_id).strip()
            if tid in self.by_trip_id:
                return self.by_trip_id[tid]
        return None


@dataclass
class RuntimeData:
    """Shared API client, fleet cache, and per-stop coordinators."""

    api: LothianApi
    fleet: FleetCache
    coordinators: dict[str, StopCoordinator] = field(default_factory=dict)


type LothianConfigEntry = ConfigEntry[RuntimeData]


def parse_departure_board(
    stop_id: str,
    raw: dict[str, Any],
    fleet: FleetCache,
    fallback_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse /departureBoards/website JSON and enrich with live fleet & route colour metadata."""
    fallback = fallback_meta or {}
    stop_obj = raw.get("stop") or {}
    bundled = get_stop_by_id(stop_id) or {}

    stop_name = (
        stop_obj.get("name")
        or fallback.get(CONF_STOP_NAME)
        or bundled.get("name")
        or stop_id
    )
    identifier = (
        stop_obj.get("identifier")
        or fallback.get(CONF_IDENTIFIER)
        or bundled.get("indicator")
        or ""
    )
    direction = (
        stop_obj.get("direction")
        or fallback.get(CONF_DIRECTION)
        or bundled.get("direction")
        or ""
    )
    street = fallback.get(CONF_STREET) or bundled.get("street") or ""
    locality = fallback.get(CONF_LOCALITY) or bundled.get("locality") or ""

    services = raw.get("services") or []
    departures: list[dict[str, Any]] = []
    seen_routes: list[str] = []
    modes_set: set[str] = set(fallback.get(CONF_MODES) or bundled.get("modes") or [])

    now_ts = time.time()

    for svc in services:
        if not isinstance(svc, dict):
            continue
        svc_name = str(svc.get("service_name") or "").strip()
        if svc_name and svc_name not in seen_routes:
            seen_routes.append(svc_name)

        for dep in svc.get("departures") or []:
            if not isinstance(dep, dict):
                continue
            route = str(dep.get("service_name") or svc_name or "").strip()
            if route and route not in seen_routes:
                seen_routes.append(route)

            is_tram = route.lower() == "tram" or dep.get("transit_mode") == 0
            mode = "tram" if is_tram else "bus"
            modes_set.add(mode)

            raw_vid = dep.get("vehicle_id")
            vid = str(raw_vid).strip() if raw_vid else None
            raw_jid = dep.get("journey_id")
            jid = str(raw_jid).strip() if raw_jid else None

            live_veh = fleet.match_vehicle(vid, jid)
            if live_veh:
                if not vid and live_veh.get("id"):
                    vid = str(live_veh["id"]).strip()
                if live_veh.get("transitMode") == "tram":
                    mode = "tram"
                    modes_set.add("tram")

            bg_color, fg_color = get_route_colors(route, mode, fleet.route_colors)

            dep_unix = dep.get("departure_time_unix")
            if isinstance(dep_unix, (int, float)):
                expected_ts = float(dep_unix)
            else:
                mins_raw = dep.get("minutes", 0)
                expected_ts = now_ts + (float(mins_raw) * 60.0)

            minutes = dep.get("minutes")
            if not isinstance(minutes, int):
                minutes = max(0, int((expected_ts - now_ts) // 60))

            coord = (live_veh or {}).get("coordinate") or {}
            departures.append(
                {
                    "route": route,
                    "mode": mode,
                    "destination": str(dep.get("destination") or "").strip(),
                    "departure_time": str(dep.get("departure_time") or "").strip(),
                    "departure_time_iso": dep.get("departure_time_iso"),
                    "expected": expected_ts,
                    "minutes": max(0, minutes),
                    "real_time": bool(dep.get("real_time", False)),
                    "diverted": bool(dep.get("diverted", False)),
                    "part_route": bool(dep.get("partRoute", False)),
                    "occupancy_rate": dep.get("occupancy_rate"),
                    "journey_id": jid,
                    "vehicle_id": vid,
                    "route_color": bg_color,
                    "route_text_color": fg_color,
                    "vehicle_speed": (live_veh or {}).get("speed"),
                    "vehicle_bearing": (live_veh or {}).get("bearing"),
                    "vehicle_lat": coord.get("latitude"),
                    "vehicle_lon": coord.get("longitude"),
                    "vehicle_last_updated": (live_veh or {}).get("lastUpdated"),
                }
            )

    departures.sort(key=lambda d: (d["expected"], d["minutes"], d["route"]))

    # Merge configured/bundled routes so all routes serving the stop are listed even late at night
    for rname in fallback.get(CONF_ROUTES) or bundled.get("routes") or []:
        if rname and rname not in seen_routes:
            seen_routes.append(rname)

    lines = []
    for rname in seen_routes:
        m = "tram" if rname.lower() == "tram" else "bus"
        bg, fg = get_route_colors(rname, m, fleet.route_colors)
        lines.append(
            {"id": rname, "name": rname, "color": bg, "text_color": fg, "mode": m}
        )

    if not modes_set:
        modes_set = {"bus"}

    return {
        "stop_id": str(stop_id),
        "stop_name": stop_name,
        "identifier": identifier,
        "direction": direction,
        "street": street,
        "locality": locality,
        "modes": sorted(modes_set),
        "lines": lines,
        "departures": departures,
    }


class StopCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls live Lothian Buses & Edinburgh Trams departures for a single stop subentry."""

    config_entry: LothianConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: LothianConfigEntry,
        subentry: ConfigSubentry,
        api: LothianApi,
        fleet: FleetCache,
    ) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        stop_id = str(subentry.data[CONF_STOP_ID]).strip()
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{stop_id}",
            update_interval=timedelta(seconds=interval),
        )
        self.api = api
        self.fleet = fleet
        self.subentry = subentry
        self.stop_id = stop_id
        self.stop_name: str = subentry.data.get(CONF_STOP_NAME) or stop_id

    async def _async_update_data(self) -> dict[str, Any]:
        await self.fleet.async_refresh_if_stale()
        try:
            raw = await self.api.get_departure_board(self.stop_id)
        except LothianApiError as err:
            raise UpdateFailed(
                f"Error fetching departures for stop {self.stop_id}: {err}"
            ) from err

        return parse_departure_board(
            self.stop_id,
            raw,
            self.fleet,
            dict(self.subentry.data),
        )
