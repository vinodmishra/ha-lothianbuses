"""Constants for the Lothian Buses & Edinburgh Trams integration."""

from __future__ import annotations

DOMAIN = "lothian_buses"
VERSION = "0.1.0"

API_BASE = "https://lothianapi.com"

CONF_STOP_ID = "stop_id"
CONF_STOP_NAME = "stop_name"
CONF_STREET = "street"
CONF_LOCALITY = "locality"
CONF_IDENTIFIER = "identifier"
CONF_DIRECTION = "direction"
CONF_MODES = "modes"
CONF_ROUTES = "routes"
CONF_QUERY = "query"
CONF_STOPS = "stops"

CONF_SCAN_INTERVAL = "scan_interval"
CONF_MAX_DEPARTURES = "max_departures"

DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 15
MAX_SCAN_INTERVAL = 300
DEFAULT_MAX_DEPARTURES = 20
FLEET_CACHE_TTL = 30  # seconds between /vehicles/all refreshes

SUBENTRY_STOP = "stop"

ATTRIBUTION = (
    "Real-time data via Lothian Buses / Transport for Edinburgh & NaPTAN (OGL v3.0)"
)

MODE_NAMES = {
    "bus": "Lothian Bus",
    "tram": "Edinburgh Tram",
}

MODE_ICONS = {
    "bus": "🚌",
    "tram": "🚊",
}

DEFAULT_BUS_COLOR = ("#85193C", "#FFFFFF")  # Lothian madder red
DEFAULT_TRAM_COLOR = ("#949394", "#FFFFFF")  # Edinburgh Trams silver/grey
DEFAULT_NIGHT_COLOR = ("#1A1B2F", "#FFD100")  # NightBus dark navy & gold

# Official Lothian Buses, Lothian Country, East Coast Buses & Edinburgh Trams route colours (bg, fg)
ROUTE_COLORS: dict[str, tuple[str, str]] = {
    "Tram": ("#949394", "#FFFFFF"),
    "T50": ("#949394", "#FFFFFF"),
    "1": ("#98C8ED", "#000000"),
    "2": ("#4DA32F", "#000000"),
    "3": ("#DECE00", "#000000"),
    "4": ("#D7B5CE", "#000000"),
    "5": ("#F9B233", "#000000"),
    "7": ("#F49F95", "#000000"),
    "8": ("#117032", "#FFFFFF"),
    "9": ("#BC8B89", "#000000"),
    "10": ("#6A2655", "#FFFFFF"),
    "11": ("#B11A23", "#FFFFFF"),
    "12": ("#9CC872", "#000000"),
    "14": ("#A69DAD", "#000000"),
    "15": ("#8D5B4C", "#FFFFFF"),
    "16": ("#AE9A64", "#000000"),
    "17": ("#5A934F", "#000000"),
    "18": ("#C96CA5", "#000000"),
    "19": ("#C57F00", "#000000"),
    "20": ("#9E6B55", "#FFFFFF"),
    "21": ("#D7B27B", "#000000"),
    "22": ("#7C3F61", "#FFFFFF"),
    "23": ("#27348B", "#FFFFFF"),
    "24": ("#E7657F", "#000000"),
    "25": ("#951B81", "#FFFFFF"),
    "26": ("#E30613", "#FFFFFF"),
    "27": ("#ED6F30", "#000000"),
    "29": ("#AC8ABF", "#000000"),
    "30": ("#CA8C16", "#000000"),
    "31": ("#7B6A58", "#FFFFFF"),
    "33": ("#901426", "#FFFFFF"),
    "34": ("#2B2171", "#FFFFFF"),
    "35": ("#BA313D", "#FFFFFF"),
    "36": ("#327775", "#FFFFFF"),
    "37": ("#355FAA", "#FFFFFF"),
    "38": ("#76B82A", "#000000"),
    "41": ("#4A5D9E", "#FFFFFF"),
    "43": ("#387823", "#FFFFFF"),
    "44": ("#9D9D9C", "#000000"),
    "45": ("#008D7F", "#FFFFFF"),
    "46": ("#E30613", "#FFFFFF"),
    "47": ("#7B9CC0", "#000000"),
    "48": ("#52516E", "#FFFFFF"),
    "49": ("#16A0BB", "#000000"),
    "61": ("#387823", "#FFFFFF"),
    "63": ("#009FE3", "#000000"),
    "70": ("#A8CCC1", "#000000"),
    "72": ("#95C11F", "#000000"),
    "74": ("#C88014", "#000000"),
    "100": ("#002C4D", "#FFFFFF"),
    "104": ("#B51F63", "#FFFFFF"),
    "106": ("#CD8BB5", "#000000"),
    "107": ("#CD8BB5", "#000000"),
    "113": ("#00A651", "#000000"),
    "120": ("#7D3F61", "#FFFFFF"),
    "124": ("#20419A", "#FFFFFF"),
    "140": ("#6B1687", "#FFFFFF"),
    "200": ("#0076BD", "#FFFFFF"),
    "300": ("#0076BD", "#FFFFFF"),
    "400": ("#0076BD", "#FFFFFF"),
    "X4": ("#F15A29", "#000000"),
    "X5": ("#20419A", "#FFFFFF"),
    "X6": ("#CD8BB5", "#000000"),
    "X7": ("#DA1C5C", "#FFFFFF"),
    "X18": ("#A6529A", "#FFFFFF"),
    "X19": ("#09488A", "#FFFFFF"),
    "X26": ("#E30613", "#FFFFFF"),
    "X27": ("#00A0DD", "#000000"),
    "X28": ("#00A0DD", "#000000"),
    "X31": ("#7B6A58", "#FFFFFF"),
    "X33": ("#901426", "#FFFFFF"),
    "X37": ("#355FAA", "#FFFFFF"),
    "X43": ("#387823", "#FFFFFF"),
    "X44": ("#9D9D9C", "#000000"),
}


def get_route_colors(
    route_name: str,
    mode: str = "bus",
    live_colors: dict[str, tuple[str, str]] | None = None,
) -> tuple[str, str]:
    """Return (background_hex, text_hex) for a Lothian route or Tram."""
    clean = (route_name or "").strip()
    if live_colors and clean in live_colors:
        return live_colors[clean]
    if clean in ROUTE_COLORS:
        return ROUTE_COLORS[clean]
    if clean.lower() == "tram" or mode == "tram":
        return DEFAULT_TRAM_COLOR
    if clean.upper().startswith("N") and len(clean) > 1 and clean[1:].isdigit():
        return DEFAULT_NIGHT_COLOR
    return DEFAULT_BUS_COLOR
