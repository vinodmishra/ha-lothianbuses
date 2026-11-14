"""WebSocket API for the Lothian Buses card and visual editor."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .api import LothianApiError
from .config_flow import async_search_stops, stop_subentry
from .const import DOMAIN
from .stops import get_stop_by_id, stop_from_board

CACHE_KEY = f"{DOMAIN}_search_cache"
NOT_LOADED = (
    "Lothian Buses & Edinburgh Trams is not set up yet: add it under "
    "Settings → Devices & services → Add integration."
)


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register WebSocket commands for stop search, one-click stop add, and live trip progress."""
    websocket_api.async_register_command(hass, ws_search)
    websocket_api.async_register_command(hass, ws_add_stop)
    websocket_api.async_register_command(hass, ws_trip_progress)


def _get_loaded_entry(hass: HomeAssistant):
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry
    return None


def _entity_id_for_stop(hass: HomeAssistant, stop_id: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{stop_id}_next_arrival"
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/search",
        vol.Required("query"): str,
        vol.Optional("modes"): vol.All(cv.ensure_list, [str]),
    }
)
@websocket_api.async_response
async def ws_search(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Search stops while typing in the card editor."""
    entry = _get_loaded_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_loaded", NOT_LOADED)
        return

    query = msg["query"].strip()
    if len(query) < 2:
        connection.send_result(msg["id"], {"stops": []})
        return

    modes = msg.get("modes") or None
    live_colors = entry.runtime_data.fleet.route_colors
    stops = await async_search_stops(hass, query, modes=modes, live_colors=live_colors)

    cache: dict[str, dict[str, Any]] = hass.data.setdefault(CACHE_KEY, {})
    configured = {s.unique_id for s in entry.subentries.values()}
    for stop in stops:
        cache[stop["id"]] = dict(stop)
        stop["added"] = stop["id"] in configured
        stop["entity_id"] = (
            _entity_id_for_stop(hass, stop["id"]) if stop["added"] else None
        )

    connection.send_result(msg["id"], {"stops": stops})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/add_stop",
        vol.Required("stop_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_add_stop(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Add a stop subentry from the card editor and return its sensor entity_id."""
    entry = _get_loaded_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_loaded", NOT_LOADED)
        return

    stop_id = str(msg["stop_id"]).strip()
    configured = {s.unique_id for s in entry.subentries.values()}

    if stop_id not in configured:
        stop = hass.data.get(CACHE_KEY, {}).get(stop_id)
        if not stop:
            stop = await hass.async_add_executor_job(get_stop_by_id, stop_id)
        if not stop:
            try:
                board = await entry.runtime_data.api.get_departure_board(stop_id)
                stop = stop_from_board(
                    stop_id, board, entry.runtime_data.fleet.route_colors
                )
            except LothianApiError as err:
                connection.send_error(msg["id"], "api_error", str(err))
                return

        sub = stop_subentry(stop)
        hass.config_entries.async_add_subentry(
            entry,
            ConfigSubentry(
                data=sub["data"],
                subentry_type=sub["subentry_type"],
                title=sub["title"],
                unique_id=sub["unique_id"],
            ),
        )

    for _ in range(80):
        if entity_id := _entity_id_for_stop(hass, stop_id):
            connection.send_result(msg["id"], {"entity_id": entity_id})
            return
        await asyncio.sleep(0.25)

    connection.send_error(
        msg["id"],
        "timeout",
        "The stop was added, but its sensor is still initialising. Refresh the page in a moment.",
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/trip_progress",
        vol.Optional("vehicle_id"): vol.Any(str, None),
        vol.Optional("journey_id"): vol.Any(str, None),
        vol.Optional("stop_id"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_trip_progress(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Fetch live stop-by-stop trip progress (/trips/progress/app) for a departure."""
    entry = _get_loaded_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_loaded", NOT_LOADED)
        return

    vehicle_id = (msg.get("vehicle_id") or "").strip() or None
    journey_id = (msg.get("journey_id") or "").strip() or None
    if not vehicle_id and not journey_id:
        connection.send_error(
            msg["id"],
            "missing_params",
            "Either vehicle_id or journey_id is required to fetch trip progress.",
        )
        return

    api = entry.runtime_data.api
    fleet = entry.runtime_data.fleet
    await fleet.async_refresh_if_stale()

    live_veh = fleet.match_vehicle(vehicle_id, journey_id)
    if not vehicle_id and live_veh and live_veh.get("id"):
        vehicle_id = str(live_veh["id"]).strip()
    if not journey_id and live_veh and live_veh.get("tripID"):
        journey_id = str(live_veh["tripID"]).strip()

    try:
        raw = await api.get_trip_progress(vehicle_id, journey_id)
    except LothianApiError as err:
        connection.send_error(msg["id"], "api_error", str(err))
        return

    stops = []
    for item in raw.get("stops") or []:
        if not isinstance(item, dict):
            continue
        stops.append(
            {
                "stop_id": str(item.get("stop_id") or "").strip(),
                "stop_name": str(item.get("stop_name") or "").strip(),
                "time": str(item.get("time") or "").strip(),
                "time_iso": item.get("time_iso"),
                "time_unix": item.get("time_unix"),
                "minutes": item.get("minutes", 0),
                "passed": bool(item.get("passed", False)),
                "real_time": bool(item.get("real_time", False)),
            }
        )

    coord = (live_veh or {}).get("coordinate") or {}
    vehicle_info = (
        {
            "id": str(live_veh.get("id") or vehicle_id or ""),
            "trip_id": str(live_veh.get("tripID") or journey_id or ""),
            "mode": live_veh.get("transitMode", "bus"),
            "route": live_veh.get("routeName"),
            "destination": live_veh.get("destination"),
            "speed": live_veh.get("speed"),
            "bearing": live_veh.get("bearing"),
            "latitude": coord.get("latitude"),
            "longitude": coord.get("longitude"),
            "last_updated": live_veh.get("lastUpdated"),
            "next_stop_code": live_veh.get("nextStopCode"),
        }
        if live_veh
        else (
            {"id": vehicle_id, "trip_id": journey_id}
            if (vehicle_id or journey_id)
            else None
        )
    )

    connection.send_result(
        msg["id"],
        {
            "stops": stops,
            "vehicle": vehicle_info,
        },
    )
