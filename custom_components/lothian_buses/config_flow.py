"""Config flow for Lothian Buses & Edinburgh Trams."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryData,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .api import LothianApi, LothianApiError
from .const import (
    CONF_DIRECTION,
    CONF_IDENTIFIER,
    CONF_LOCALITY,
    CONF_MAX_DEPARTURES,
    CONF_MODES,
    CONF_QUERY,
    CONF_ROUTES,
    CONF_SCAN_INTERVAL,
    CONF_STOP_ID,
    CONF_STOP_NAME,
    CONF_STOPS,
    CONF_STREET,
    DEFAULT_MAX_DEPARTURES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    MODE_ICONS,
    SUBENTRY_STOP,
)
from .stops import load_stops, search_stops, stop_from_board

MAX_RESULTS = 40
ENTRY_TITLE = "Lothian Buses & Edinburgh Trams"


def stop_title(stop: dict[str, Any]) -> str:
    """Format a human-readable title for a stop subentry."""
    title = stop["name"]
    indicator = stop.get("indicator") or ""
    direction = stop.get("direction") or ""
    suffix_parts = []
    if indicator and indicator.lower() not in title.lower():
        suffix_parts.append(indicator)
    if direction:
        suffix_parts.append(direction)
    if suffix_parts:
        title = f"{title} ({' · '.join(suffix_parts)})"
    return title


def stop_label(stop: dict[str, Any]) -> str:
    """Format a stop option line for ConfigFlow selector lists."""
    icons = "".join(MODE_ICONS.get(m, "🚌") for m in stop.get("modes") or ["bus"])
    label = f"{icons} {stop_title(stop)}"
    loc_parts = [p for p in (stop.get("street"), stop.get("locality")) if p]
    if loc_parts:
        label += f" — {', '.join(loc_parts)}"
    label += f" [{stop['id']}]"
    routes = stop.get("routes") or []
    if routes:
        shown = ", ".join(routes[:10]) + (" …" if len(routes) > 10 else "")
        label += f"  •  Routes: {shown}"
    return label


def stop_subentry(stop: dict[str, Any]) -> ConfigSubentryData:
    """Create a ConfigSubentryData object from a stop dictionary."""
    return ConfigSubentryData(
        data={
            CONF_STOP_ID: str(stop["id"]),
            CONF_STOP_NAME: stop["name"],
            CONF_STREET: stop.get("street", ""),
            CONF_LOCALITY: stop.get("locality", ""),
            CONF_IDENTIFIER: stop.get("indicator", ""),
            CONF_DIRECTION: stop.get("direction", ""),
            CONF_MODES: list(stop.get("modes") or ["bus"]),
            CONF_ROUTES: list(stop.get("routes") or []),
        },
        subentry_type=SUBENTRY_STOP,
        title=stop_title(stop),
        unique_id=str(stop["id"]),
    )


async def async_search_stops(
    hass: HomeAssistant,
    query: str,
    modes: list[str] | None = None,
    live_colors: dict[str, tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Search bundled stops and fall back to live API if a numeric stop ID is queried."""
    await hass.async_add_executor_job(load_stops)
    clean = query.strip()
    results = search_stops(
        clean, modes=modes, limit=MAX_RESULTS, live_colors=live_colors
    )

    if (
        clean.isdigit()
        and len(clean) >= 6
        and not any(s["id"] == clean for s in results)
    ):
        api = LothianApi(async_get_clientsession(hass))
        try:
            board = await api.get_departure_board(clean)
            if board.get("stop") or board.get("services"):
                results.insert(0, stop_from_board(clean, board, live_colors))
        except LothianApiError:
            pass

    return results[:MAX_RESULTS]


def search_schema() -> vol.Schema:
    return vol.Schema({vol.Required(CONF_QUERY): TextSelector()})


def stops_schema(results: dict[str, dict[str, Any]], multiple: bool) -> vol.Schema:
    options = [
        SelectOptionDict(value=sid, label=stop_label(s)) for sid, s in results.items()
    ]
    key = CONF_STOPS if multiple else CONF_STOP_ID
    return vol.Schema(
        {
            vol.Required(key): SelectSelector(
                SelectSelectorConfig(
                    options=options, multiple=multiple, mode=SelectSelectorMode.LIST
                )
            )
        }
    )


class LothianBusesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Lothian Buses & Edinburgh Trams."""

    VERSION = 1

    def __init__(self) -> None:
        self._results: dict[str, dict[str, Any]] = {}
        self._selected: dict[str, dict[str, Any]] = {}

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_STOP: StopSubentryFlow}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return LothianOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Initial setup menu: add stops now or from the dashboard card editor."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return self.async_show_menu(step_id="user", menu_options=["finish", "search"])

    async def async_step_search(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            query = (user_input.get(CONF_QUERY) or "").strip()
            if len(query) < 2:
                errors[CONF_QUERY] = "query_too_short"
            else:
                stops = await async_search_stops(self.hass, query)
                if not stops:
                    errors[CONF_QUERY] = "no_stops"
                else:
                    self._results = {s["id"]: s for s in stops}
                    return await self.async_step_stops()
        return self.async_show_form(
            step_id="search",
            data_schema=search_schema(),
            errors=errors,
            description_placeholders={"selected": self._selected_text()},
        )

    async def async_step_stops(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            chosen = user_input.get(CONF_STOPS) or []
            if chosen:
                for sid in chosen:
                    if sid in self._results:
                        self._selected[sid] = self._results[sid]
                return await self.async_step_more()
            errors["base"] = "select_one"
        return self.async_show_form(
            step_id="stops",
            data_schema=stops_schema(self._results, multiple=True),
            errors=errors,
        )

    async def async_step_more(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="more",
            menu_options=["search", "finish"],
            description_placeholders={"selected": self._selected_text()},
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_create_entry(
            title=ENTRY_TITLE,
            data={},
            subentries=[stop_subentry(s) for s in self._selected.values()],
        )

    def _selected_text(self) -> str:
        if not self._selected:
            return "–"
        return "\n".join(f"• {stop_label(s)}" for s in self._selected.values())


class StopSubentryFlow(ConfigSubentryFlow):
    """Handle '+ Add stop' subentry flow from the integration page."""

    def __init__(self) -> None:
        self._results: dict[str, dict[str, Any]] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            query = (user_input.get(CONF_QUERY) or "").strip()
            if len(query) < 2:
                errors[CONF_QUERY] = "query_too_short"
            else:
                entry = self._get_entry()
                live_colors = (
                    entry.runtime_data.fleet.route_colors
                    if hasattr(entry, "runtime_data") and entry.runtime_data
                    else None
                )
                stops = await async_search_stops(
                    self.hass, query, live_colors=live_colors
                )
                if not stops:
                    errors[CONF_QUERY] = "no_stops"
                else:
                    existing = {s.unique_id for s in entry.subentries.values()}
                    self._results = {
                        s["id"]: s for s in stops if s["id"] not in existing
                    }
                    if self._results:
                        return await self.async_step_select()
                    errors[CONF_QUERY] = "already_configured"
        return self.async_show_form(
            step_id="user", data_schema=search_schema(), errors=errors
        )

    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            stop = self._results[user_input[CONF_STOP_ID]]
            sub = stop_subentry(stop)
            return self.async_create_entry(
                title=sub["title"],
                data=sub["data"],
                unique_id=sub["unique_id"],
            )
        return self.async_show_form(
            step_id="select",
            data_schema=stops_schema(self._results, multiple=False),
        )


class LothianOptionsFlow(OptionsFlow):
    """Configure polling interval and maximum departures kept."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                    CONF_MAX_DEPARTURES: int(user_input[CONF_MAX_DEPARTURES]),
                },
            )
        opts = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=5,
                            unit_of_measurement="s",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_MAX_DEPARTURES,
                        default=opts.get(CONF_MAX_DEPARTURES, DEFAULT_MAX_DEPARTURES),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=5,
                            max=50,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
        )
