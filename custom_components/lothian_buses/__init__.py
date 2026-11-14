"""Lothian Buses & Edinburgh Trams integration for Home Assistant.

Provides live stop departures, vehicle tracking, schedule sensors for Assist,
and an auto-registered Mushroom-style dashboard card.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from . import websocket
from .api import LothianApi
from .const import DOMAIN, SUBENTRY_STOP
from .coordinator import (
    FleetCache,
    LothianConfigEntry,
    RuntimeData,
    StopCoordinator,
    parse_departure_board,
)
from .frontend import async_setup_frontend
from .sensor import build_spoken_schedule
from .stops import load_stops, search_stops

PLATFORMS: list[Platform] = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_GET_SCHEDULE = "get_schedule"
SERVICE_GET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Optional("stop_id"): cv.string,
        vol.Optional("route"): cv.string,
        vol.Optional("max_departures", default=5): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=20)
        ),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the bundled Lovelace card, register WebSocket APIs, and preload stops."""
    await async_setup_frontend(hass)
    websocket.async_register(hass)
    await hass.async_add_executor_job(load_stops)

    async def _async_handle_get_schedule(call: ServiceCall) -> ServiceResponse:
        stop_query = (call.data.get("stop_id") or "").strip()
        route_filter = (call.data.get("route") or "").strip().lower()
        max_deps: int = call.data.get("max_departures", 5)

        entry: LothianConfigEntry | None = None
        for cand in hass.config_entries.async_entries(DOMAIN):
            if cand.state is ConfigEntryState.LOADED:
                entry = cand
                break

        stops_out: list[dict[str, Any]] = []
        spoken_parts: list[str] = []

        if entry and not stop_query:
            for coord in entry.runtime_data.coordinators.values():
                board = coord.data or {}
                deps = list(board.get("departures") or [])
                if route_filter:
                    deps = [
                        d
                        for d in deps
                        if str(d.get("route") or "").lower() == route_filter
                    ]
                deps = deps[:max_deps]
                title = coord.subentry.title or coord.stop_name
                spoken = build_spoken_schedule(title, deps, max_items=max_deps)
                spoken_parts.append(spoken)
                stops_out.append(
                    {
                        "stop_id": coord.stop_id,
                        "stop_name": title,
                        "direction": board.get("direction"),
                        "spoken_schedule": spoken,
                        "departures": deps,
                    }
                )
        else:
            session = async_get_clientsession(hass)
            api = entry.runtime_data.api if entry else LothianApi(session)
            fleet = entry.runtime_data.fleet if entry else FleetCache(api=api)
            await fleet.async_refresh_if_stale()

            stop_id = stop_query
            if not stop_id.isdigit():
                matches = await hass.async_add_executor_job(
                    search_stops, stop_query, None, 1, None
                )
                if matches:
                    stop_id = matches[0]["id"]

            if stop_id:
                raw = await api.get_departure_board(stop_id)
                parsed = parse_departure_board(stop_id, raw, fleet)
                deps = list(parsed.get("departures") or [])
                if route_filter:
                    deps = [
                        d
                        for d in deps
                        if str(d.get("route") or "").lower() == route_filter
                    ]
                deps = deps[:max_deps]
                title = parsed.get("stop_name") or stop_id
                spoken = build_spoken_schedule(title, deps, max_items=max_deps)
                spoken_parts.append(spoken)
                stops_out.append(
                    {
                        "stop_id": stop_id,
                        "stop_name": title,
                        "direction": parsed.get("direction"),
                        "spoken_schedule": spoken,
                        "departures": deps,
                    }
                )

        return {
            "spoken_summary": " ".join(spoken_parts)
            if spoken_parts
            else "No stops matched.",
            "stops": stops_out,
        }

    if not hass.services.has_service(DOMAIN, SERVICE_GET_SCHEDULE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_SCHEDULE,
            _async_handle_get_schedule,
            schema=SERVICE_GET_SCHEDULE_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: LothianConfigEntry) -> bool:
    """Set up Lothian Buses & Edinburgh Trams and one coordinator per stop subentry."""
    session = async_get_clientsession(hass)
    api = LothianApi(session)
    fleet = FleetCache(api=api)
    runtime = RuntimeData(api=api, fleet=fleet)

    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_STOP:
            continue
        coordinator = StopCoordinator(hass, entry, subentry, api, fleet)
        await coordinator.async_config_entry_first_refresh()
        runtime.coordinators[subentry.subentry_id] = coordinator

    entry.runtime_data = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: LothianConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: LothianConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
