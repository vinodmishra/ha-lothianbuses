"""Async API client for Lothian Buses & Edinburgh Trams (lothianapi.com)."""

from __future__ import annotations

from typing import Any

import aiohttp

from .const import API_BASE

DEFAULT_HEADERS = {
    "User-Agent": "HomeAssistant-LothianBuses/0.1",
    "Accept": "application/json",
}
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=12)


class LothianApiError(Exception):
    """Base error for Lothian API requests."""


class LothianConnectionError(LothianApiError):
    """Network or timeout error talking to lothianapi.com."""


class LothianApi:
    """Client for the public Lothian Buses & Edinburgh Trams endpoints."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{API_BASE}{path}"
        try:
            async with self._session.get(
                url,
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status >= 400:
                    raise LothianApiError(f"HTTP {resp.status} from {path}")
                data = await resp.json(content_type=None)
                if isinstance(data, dict):
                    return data
                # lothianapi.com (PHP backend) serializes empty associative arrays as []
                if isinstance(data, list):
                    if not data:
                        return {}
                    if isinstance(data[0], dict):
                        return data[0]
                raise LothianApiError(f"Unexpected response format from {path}")
        except (TimeoutError, aiohttp.ClientError) as err:
            raise LothianConnectionError(f"Error connecting to {url}: {err}") from err

    async def get_departure_board(self, stop_id: str) -> dict[str, Any]:
        """Fetch live departures for a stop ID (NaPTAN/SMS code, e.g. '36238285')."""
        return await self._get(
            "/departureBoards/website", {"stops": str(stop_id).strip()}
        )

    async def get_trip_progress(
        self, vehicle_id: str | None, journey_id: str | None
    ) -> dict[str, Any]:
        """Fetch live stop-by-stop trip progress for a vehicle/journey."""
        params: dict[str, str] = {}
        if vehicle_id:
            params["vehicle_id"] = str(vehicle_id).strip()
        if journey_id:
            params["journey_id"] = str(journey_id).strip()
        return await self._get("/trips/progress/app", params)

    async def get_all_vehicles(self) -> dict[str, Any]:
        """Fetch all active vehicles across Lothian Buses & Edinburgh Trams."""
        return await self._get("/vehicles/all")

    async def get_vehicles_by_route(self, route_name: str) -> dict[str, Any]:
        """Fetch active vehicles on a specific route."""
        return await self._get(
            "/vehicles/byRoute", {"route_name": str(route_name).strip()}
        )

    async def get_vehicle_by_id(self, vehicle_id: str) -> dict[str, Any]:
        """Fetch a single vehicle by its fleet ID."""
        return await self._get(
            "/vehicles/byID", {"vehicle_id": str(vehicle_id).strip()}
        )
