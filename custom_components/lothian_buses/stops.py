"""Bundled Edinburgh & Lothians stop directory and search engine."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .const import get_route_colors

STOPS_FILE = Path(__file__).parent / "data" / "stops.json"

_STOPS: list[dict[str, Any]] | None = None
_STOPS_BY_ID: dict[str, dict[str, Any]] = {}
_BUNDLED_COLORS: dict[str, tuple[str, str]] = {}


def load_stops() -> list[dict[str, Any]]:
    """Load the bundled stops database from disk (safe to call from executor)."""
    global _STOPS
    if _STOPS is not None:
        return _STOPS

    if not STOPS_FILE.exists():
        _STOPS = []
        return _STOPS

    raw = json.loads(STOPS_FILE.read_text(encoding="utf-8"))
    colors_raw = raw.get("route_colors", {})
    for rname, cinfo in colors_raw.items():
        if isinstance(cinfo, dict) and cinfo.get("bg") and cinfo.get("fg"):
            _BUNDLED_COLORS[rname] = (cinfo["bg"], cinfo["fg"])

    stops: list[dict[str, Any]] = []
    for item in raw.get("stops", []):
        stop = _enrich_stop(item)
        stops.append(stop)
        _STOPS_BY_ID[stop["id"]] = stop

    _STOPS = stops
    return _STOPS


def _enrich_stop(
    item: dict[str, Any], live_colors: dict[str, tuple[str, str]] | None = None
) -> dict[str, Any]:
    """Attach formatted line badge metadata to a stop dictionary."""
    modes = item.get("modes") or ["bus"]
    primary_mode = "tram" if "tram" in modes else "bus"
    routes = item.get("routes") or []
    merged_colors = {**_BUNDLED_COLORS, **(live_colors or {})}
    lines = []
    for rname in routes:
        bg, fg = get_route_colors(
            rname, "tram" if rname.lower() == "tram" else primary_mode, merged_colors
        )
        lines.append({"id": rname, "name": rname, "color": bg, "text_color": fg})

    name = item.get("name") or item["id"]
    street = item.get("street") or ""
    locality = item.get("locality") or ""
    indicator = item.get("indicator") or ""
    direction = item.get("direction") or ""

    search_blob = " ".join(
        part.lower()
        for part in (
            item["id"],
            name,
            street,
            locality,
            indicator,
            direction,
            " ".join(routes),
            "tram" if "tram" in modes else "",
        )
        if part
    )

    return {
        "id": str(item["id"]),
        "name": name,
        "street": street,
        "locality": locality,
        "indicator": indicator,
        "direction": direction,
        "lat": item.get("lat", 0.0),
        "lon": item.get("lon", 0.0),
        "modes": list(modes),
        "routes": list(routes),
        "lines": lines,
        "_search": search_blob,
    }


def get_stop_by_id(stop_id: str) -> dict[str, Any] | None:
    """Return a bundled stop by ID if known."""
    load_stops()
    stop = _STOPS_BY_ID.get(str(stop_id).strip())
    return _public_stop(stop) if stop else None


def _public_stop(stop: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the stop dict without internal search fields."""
    return {k: v for k, v in stop.items() if not k.startswith("_")}


def stop_from_board(
    stop_id: str,
    board: dict[str, Any],
    live_colors: dict[str, tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Construct or enrich a stop dictionary from a live /departureBoards/website payload."""
    load_stops()
    existing = _STOPS_BY_ID.get(str(stop_id).strip(), {})
    raw_stop = board.get("stop")
    stop_info = raw_stop if isinstance(raw_stop, dict) else {}
    services = board.get("services") or []
    live_routes = [
        str(s.get("service_name")).strip() for s in services if s.get("service_name")
    ]
    routes = list(dict.fromkeys(live_routes + list(existing.get("routes") or [])))

    modes = set(existing.get("modes") or [])
    for rname in routes:
        if rname.lower() == "tram":
            modes.add("tram")
        else:
            modes.add("bus")
    if not modes:
        modes = {"bus"}

    raw = {
        "id": str(stop_info.get("id") or stop_id).strip(),
        "name": stop_info.get("name") or existing.get("name") or str(stop_id),
        "street": existing.get("street") or "",
        "locality": existing.get("locality") or "",
        "indicator": stop_info.get("identifier") or existing.get("indicator") or "",
        "direction": stop_info.get("direction") or existing.get("direction") or "",
        "lat": existing.get("lat", 0.0),
        "lon": existing.get("lon", 0.0),
        "modes": sorted(modes),
        "routes": routes,
    }
    return _public_stop(_enrich_stop(raw, live_colors))


def search_stops(
    query: str,
    modes: list[str] | None = None,
    limit: int = 40,
    live_colors: dict[str, tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Search bundled Edinburgh & Lothians stops by name, street, locality, stop code, or route."""
    load_stops()
    clean_q = query.strip().lower()
    if not clean_q:
        return []

    tokens = [t for t in re.split(r"\s+", clean_q) if t]
    mode_filter = set(modes) if modes else None

    scored: list[tuple[tuple[int, int, int, str], dict[str, Any]]] = []
    for stop in _STOPS or []:
        if mode_filter and not mode_filter.intersection(stop["modes"]):
            continue
        blob = stop["_search"]
        if not all(tok in blob for tok in tokens):
            continue

        sid_low = stop["id"].lower()
        name_low = stop["name"].lower()
        street_low = stop["street"].lower()
        loc_low = stop["locality"].lower()
        routes_low = [r.lower() for r in stop["routes"]]

        # Lower score tuple = better match
        if sid_low == clean_q:
            rank = 0
        elif name_low == clean_q:
            rank = 1
        elif clean_q in routes_low:
            rank = 2
        elif name_low.startswith(clean_q):
            rank = 3
        elif sid_low.startswith(clean_q):
            rank = 4
        elif clean_q in name_low:
            rank = 5
        elif street_low.startswith(clean_q) or loc_low.startswith(clean_q):
            rank = 6
        else:
            rank = 7

        exact_id_rank = 0 if sid_low == clean_q else 1
        has_routes_rank = 0 if stop["routes"] else 1
        tram_bonus = 0 if "tram" in stop["modes"] else 1
        scored.append(
            (
                (
                    exact_id_rank,
                    has_routes_rank,
                    rank,
                    tram_bonus,
                    -len(stop["routes"]),
                    stop["name"],
                ),
                stop,
            )
        )

    scored.sort(key=lambda item: item[0])
    results: list[dict[str, Any]] = []
    for _, stop in scored[:limit]:
        pub = _public_stop(_enrich_stop(stop, live_colors) if live_colors else stop)
        results.append(pub)
    return results
