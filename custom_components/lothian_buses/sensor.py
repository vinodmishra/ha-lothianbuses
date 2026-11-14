"""Schedule and arrival sensors per Lothian Buses / Edinburgh Trams stop."""

from __future__ import annotations

import contextlib
import re
import time
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_DIRECTION,
    CONF_IDENTIFIER,
    CONF_LOCALITY,
    CONF_MAX_DEPARTURES,
    CONF_MODES,
    CONF_ROUTES,
    CONF_STREET,
    DEFAULT_MAX_DEPARTURES,
    DOMAIN,
    MODE_NAMES,
)
from .coordinator import LothianConfigEntry, StopCoordinator


def _eta_phrase(minutes: int) -> str:
    """Format a compact ETA string such as 'Due' or '5 min'."""
    if minutes <= 0:
        return "Due"
    return f"{minutes} min"


def _spoken_eta(minutes: int) -> str:
    """Format a conversational ETA phrase for TTS/Assist."""
    if minutes <= 0:
        return "due now"
    if minutes == 1:
        return "in 1 minute"
    return f"in {minutes} minutes"


def _truncate_state(text: str, max_len: int = 255) -> str:
    """Ensure sensor state never exceeds Home Assistant's 255-character limit."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip(" ;|,") + "…"


def build_spoken_schedule(
    stop_title: str, departures: list[dict[str, Any]], max_items: int = 4
) -> str:
    """Build a natural-language spoken schedule sentence for Assist and TTS."""
    if not departures:
        return f"There are no upcoming departures scheduled from {stop_title}."

    parts: list[str] = []
    for dep in departures[:max_items]:
        route = dep.get("route") or "Bus"
        prefix = "Tram" if str(route).lower() == "tram" else f"Route {route}"
        dest = dep.get("destination") or "unknown destination"
        mins = int(dep.get("minutes", 0))
        clock = dep.get("departure_time") or ""
        time_part = f" at {clock}" if clock else ""
        parts.append(f"{prefix} to {dest} {_spoken_eta(mins)}{time_part}")

    if len(parts) == 1:
        joined = parts[0]
    else:
        joined = ", ".join(parts[:-1]) + f", and {parts[-1]}"
    return f"From {stop_title}, the next departures are: {joined}."


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LothianConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create arrival and schedule sensors for each configured stop subentry."""
    for subentry_id, coordinator in entry.runtime_data.coordinators.items():
        entities: list[SensorEntity] = [
            LothianNextArrivalSensor(coordinator),
            LothianNextDepartureTimeSensor(coordinator),
            LothianNextServiceSensor(coordinator),
            LothianUpcomingScheduleSensor(coordinator),
        ]

        known_routes: set[str] = set()
        for rname in coordinator.subentry.data.get(CONF_ROUTES) or []:
            clean = str(rname).strip()
            if clean:
                known_routes.add(clean)
        for line in (coordinator.data or {}).get("lines") or []:
            clean = str(line.get("name") or line.get("id") or "").strip()
            if clean:
                known_routes.add(clean)

        for route in sorted(known_routes, key=_route_sort_key):
            entities.append(LothianRouteScheduleSensor(coordinator, route))

        async_add_entities(entities, config_subentry_id=subentry_id)

        # Dynamically register route schedule sensors if a stop sees a new route later
        @callback
        def _check_new_routes(
            coord: StopCoordinator = coordinator,
            sub_id: str = subentry_id,
            seen: set[str] = known_routes,
        ) -> None:
            new_entities: list[SensorEntity] = []
            for line in (coord.data or {}).get("lines") or []:
                rname = str(line.get("name") or line.get("id") or "").strip()
                if rname and rname not in seen:
                    seen.add(rname)
                    new_entities.append(LothianRouteScheduleSensor(coord, rname))
            if new_entities:
                async_add_entities(new_entities, config_subentry_id=sub_id)

        entry.async_on_unload(coordinator.async_add_listener(_check_new_routes))


def _route_sort_key(route: str) -> tuple[int, int, str]:
    """Sort numeric routes first (1, 2, 14, 26), then prefixed routes (N16, X37, Tram)."""
    m = re.match(r"^([A-Za-z]*)(\d+)([A-Za-z]*)$", route.strip())
    if m:
        prefix, num, suffix = m.groups()
        return (0 if not prefix else 1, int(num), f"{prefix}{suffix}")
    return (2, 9999, route)


class LothianBaseStopSensor(CoordinatorEntity[StopCoordinator], SensorEntity):
    """Base class for Lothian Buses & Edinburgh Trams stop sensors."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: StopCoordinator) -> None:
        super().__init__(coordinator)
        sub_data = coordinator.subentry.data
        modes = sub_data.get(CONF_MODES) or ["bus"]
        self._is_tram_only = modes == ["tram"]

        identifier = sub_data.get(CONF_IDENTIFIER) or ""
        direction = sub_data.get(CONF_DIRECTION) or ""
        street = sub_data.get(CONF_STREET) or ""
        locality = sub_data.get(CONF_LOCALITY) or ""

        model_parts = [
            ", ".join(MODE_NAMES.get(m, m) for m in modes),
            f"Stop {identifier}" if identifier else "",
            f"({direction})" if direction else "",
            street or locality,
        ]
        self._stop_title = coordinator.subentry.title or coordinator.stop_name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.stop_id)},
            name=self._stop_title,
            manufacturer="Lothian Buses & Edinburgh Trams",
            model=" · ".join(p for p in model_parts if p) or None,
            serial_number=coordinator.stop_id,
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Automatically expose schedule sensors to Home Assistant Assist (conversation)."""
        await super().async_added_to_hass()
        with contextlib.suppress(Exception):
            from homeassistant.components.homeassistant import exposed_entities

            settings = exposed_entities.async_get_entity_settings(
                self.hass, self.entity_id
            )
            if (
                "conversation" not in settings
                or "should_expose" not in settings["conversation"]
            ):
                exposed_entities.async_expose_entity(
                    self.hass, "conversation", self.entity_id, True
                )

    @property
    def _departures(self) -> list[dict[str, Any]]:
        now = time.time()
        raw_deps = (self.coordinator.data or {}).get("departures") or []
        return [d for d in raw_deps if d.get("expected", 0) > now - 45]


class LothianNextArrivalSensor(LothianBaseStopSensor):
    """Minutes until the next Lothian Bus or Edinburgh Tram at this stop (primary card entity)."""

    _attr_translation_key = "next_arrival"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _unrecorded_attributes = frozenset({"departures", "lines", "spoken_schedule"})

    def __init__(self, coordinator: StopCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.stop_id}_next_arrival"
        self._attr_icon = "mdi:tram" if self._is_tram_only else "mdi:bus-clock"

    @property
    def native_value(self) -> int | None:
        deps = self._departures
        if not deps:
            return None
        first = deps[0]
        if isinstance(first.get("minutes"), int):
            return max(0, first["minutes"])
        return max(0, int((first["expected"] - time.time()) // 60))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        limit = self.coordinator.config_entry.options.get(
            CONF_MAX_DEPARTURES, DEFAULT_MAX_DEPARTURES
        )
        board = self.coordinator.data or {}
        sub_data = self.coordinator.subentry.data
        deps = self._departures[:limit]
        first = deps[0] if deps else {}

        return {
            "stop_id": self.coordinator.stop_id,
            "stop_name": board.get("stop_name") or self.coordinator.stop_name,
            "identifier": board.get("identifier") or sub_data.get(CONF_IDENTIFIER, ""),
            "direction": board.get("direction") or sub_data.get(CONF_DIRECTION, ""),
            "street": board.get("street") or sub_data.get(CONF_STREET, ""),
            "locality": board.get("locality") or sub_data.get(CONF_LOCALITY, ""),
            "modes": board.get("modes") or sub_data.get(CONF_MODES, ["bus"]),
            "lines": board.get("lines") or [],
            "next_route": first.get("route"),
            "next_destination": first.get("destination"),
            "next_departure_time": first.get("departure_time"),
            "next_vehicle_id": first.get("vehicle_id"),
            "next_real_time": first.get("real_time"),
            "spoken_schedule": build_spoken_schedule(self._stop_title, deps),
            "departures": deps,
        }


class LothianNextDepartureTimeSensor(LothianBaseStopSensor):
    """Exact timestamp of the next departure at this stop."""

    _attr_translation_key = "next_departure_time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: StopCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.stop_id}_next_departure_time"
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> datetime | None:
        deps = self._departures
        if not deps:
            return None
        expected = deps[0].get("expected")
        if not isinstance(expected, (int, float)):
            return None
        return datetime.fromtimestamp(expected, tz=UTC)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        deps = self._departures
        first = deps[0] if deps else {}
        return {
            "route": first.get("route"),
            "destination": first.get("destination"),
            "departure_time": first.get("departure_time"),
            "minutes": first.get("minutes"),
            "real_time": first.get("real_time"),
            "vehicle_id": first.get("vehicle_id"),
        }


class LothianNextServiceSensor(LothianBaseStopSensor):
    """Human-readable summary of the very next bus or tram departure."""

    _attr_translation_key = "next_service"

    def __init__(self, coordinator: StopCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.stop_id}_next_service"
        self._attr_icon = "mdi:tram" if self._is_tram_only else "mdi:bus-side"

    @property
    def native_value(self) -> str:
        deps = self._departures
        if not deps:
            return "No upcoming departures"
        first = deps[0]
        route = first.get("route") or "Bus"
        prefix = "Tram" if str(route).lower() == "tram" else f"Route {route}"
        dest = first.get("destination") or "Unknown"
        mins = int(first.get("minutes", 0))
        clock = first.get("departure_time") or ""
        eta = "Due" if mins <= 0 else f"in {mins} min"
        time_part = f" ({clock})" if clock else ""
        return _truncate_state(f"{prefix} to {dest} {eta}{time_part}")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        deps = self._departures
        first = deps[0] if deps else {}
        return {
            "route": first.get("route"),
            "destination": first.get("destination"),
            "departure_time": first.get("departure_time"),
            "minutes": first.get("minutes"),
            "real_time": first.get("real_time"),
            "vehicle_id": first.get("vehicle_id"),
            "diverted": first.get("diverted"),
            "part_route": first.get("part_route"),
        }


class LothianUpcomingScheduleSensor(LothianBaseStopSensor):
    """Natural-language schedule summary of the next several departures for Assist & Voice."""

    _attr_translation_key = "upcoming_schedule"
    _unrecorded_attributes = frozenset({"schedule_table", "spoken_schedule"})

    def __init__(self, coordinator: StopCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.stop_id}_upcoming_schedule"
        self._attr_icon = "mdi:timetable"

    @property
    def native_value(self) -> str:
        deps = self._departures
        if not deps:
            return "No upcoming departures"
        items: list[str] = []
        for dep in deps[:4]:
            route = dep.get("route") or ""
            dest = dep.get("destination") or ""
            mins = int(dep.get("minutes", 0))
            clock = dep.get("departure_time") or ""
            eta = _eta_phrase(mins)
            time_suffix = f" ({clock})" if clock else ""
            items.append(f"{route} to {dest}: {eta}{time_suffix}")
        return _truncate_state("; ".join(items))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        deps = self._departures
        active_routes = list(
            dict.fromkeys(str(d.get("route")) for d in deps if d.get("route"))
        )
        table = [
            f"{d.get('departure_time', '')} ({_eta_phrase(int(d.get('minutes', 0)))}) — "
            f"Route {d.get('route', '')} to {d.get('destination', '')}"
            + (f" [Live #{d['vehicle_id']}]" if d.get("vehicle_id") else "")
            for d in deps[:8]
        ]
        return {
            "upcoming_count": len(deps),
            "active_routes": active_routes,
            "spoken_schedule": build_spoken_schedule(
                self._stop_title, deps, max_items=4
            ),
            "schedule_table": table,
        }


class LothianRouteScheduleSensor(LothianBaseStopSensor):
    """Per-route schedule sensor at a stop (e.g. 'Route 14 schedule')."""

    _unrecorded_attributes = frozenset({"spoken_schedule"})

    def __init__(self, coordinator: StopCoordinator, route: str) -> None:
        super().__init__(coordinator)
        self._route = str(route).strip()
        slug = re.sub(r"[^a-z0-9]+", "_", self._route.lower()).strip("_")
        self._attr_unique_id = f"{coordinator.stop_id}_route_{slug}_schedule"
        is_tram = self._route.lower() == "tram"
        self._attr_name = (
            "Tram schedule" if is_tram else f"Route {self._route} schedule"
        )
        self._attr_icon = "mdi:tram" if is_tram else "mdi:bus-Multiple"
        if not is_tram:
            self._attr_icon = "mdi:bus"

    @property
    def _route_departures(self) -> list[dict[str, Any]]:
        target = self._route.lower()
        return [
            d
            for d in self._departures
            if str(d.get("route") or "").strip().lower() == target
        ]

    @property
    def native_value(self) -> str:
        rdeps = self._route_departures
        if not rdeps:
            return "No upcoming departures"

        # Group or format up to 3 upcoming departures for this route
        dests = list(
            dict.fromkeys(
                d.get("destination") or "" for d in rdeps[:3] if d.get("destination")
            )
        )
        if len(dests) == 1:
            times_str = ", ".join(
                f"{_eta_phrase(int(d.get('minutes', 0)))}"
                + (f" ({d['departure_time']})" if d.get("departure_time") else "")
                for d in rdeps[:3]
            )
            return _truncate_state(f"To {dests[0]}: {times_str}")

        parts = [
            f"{d.get('destination', '')}: {_eta_phrase(int(d.get('minutes', 0)))}"
            + (f" ({d['departure_time']})" if d.get("departure_time") else "")
            for d in rdeps[:3]
        ]
        return _truncate_state("; ".join(parts))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        rdeps = self._route_departures
        first = rdeps[0] if rdeps else {}
        prefix = "Tram" if self._route.lower() == "tram" else f"Route {self._route}"

        if not rdeps:
            spoken = (
                f"There are no upcoming {prefix} departures from {self._stop_title}."
            )
        else:
            first_eta = _spoken_eta(int(first.get("minutes", 0)))
            first_clock = (
                f" at {first['departure_time']}" if first.get("departure_time") else ""
            )
            spoken = (
                f"{prefix} from {self._stop_title} towards {first.get('destination', 'unknown')} "
                f"is {first_eta}{first_clock}"
            )
            if len(rdeps) > 1:
                follow = [
                    f"{_spoken_eta(int(d.get('minutes', 0)))}"
                    + (f" ({d['departure_time']})" if d.get("departure_time") else "")
                    for d in rdeps[1:3]
                ]
                spoken += f", followed by {', and '.join(follow)}."
            else:
                spoken += "."

        return {
            "route": self._route,
            "next_destination": first.get("destination"),
            "next_minutes": first.get("minutes"),
            "next_departure_time": first.get("departure_time"),
            "next_real_time": first.get("real_time"),
            "next_vehicle_id": first.get("vehicle_id"),
            "upcoming_minutes": [d.get("minutes") for d in rdeps[:4]],
            "upcoming_times": [d.get("departure_time") for d in rdeps[:4]],
            "spoken_schedule": spoken,
        }
