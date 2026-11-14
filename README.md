# Lothian Buses & Edinburgh Trams for Home Assistant

A custom component and bundled Lovelace card for Home Assistant providing real-time **Lothian Buses**, **Lothian Country**, **East Coast Buses**, **NightBus**, and **Edinburgh Trams** departure boards, live vehicle telemetry, and voice-ready schedule sensors for Home Assistant Assist.

**This component is fully Home Assistant Marketplace (formerly HACS) compliant.**

---

## Features

- **Bundled Stop & Route Directory**: Ships with **4,316 stops** across Edinburgh, Midlothian, East Lothian, West Lothian, and Fife (including all Edinburgh Trams stops to Newhaven) pre-mapped with routes, streets, localities, and compass bearings.
- **Auto-Registered Mushroom Lovelace Card (`custom:lothian-bus-card`)**: Automatically served and registered in Lovelace storage mode — no manual resource configuration required.
- **Live Stop Search in the Card Editor**: Search by stop name (`Princes Street`), street, locality (`Leith`), route number (`26`, `Tram`, `N16`), or 8-digit SMS stop code (`36238285`) and add stops to Home Assistant with one click directly from your dashboard.
- **Official Route Colour Badges**: Authentic Lothian Buses, Lothian Country, East Coast Buses, NightBus, and Edinburgh Trams colour pills.
- **Interactive Trip Progress Drawer**: Click any live departure row to expand a real-time stop-by-stop timeline showing passed stops, your current stop, and upcoming stops with live ETAs.
- **Per-Card Route Filtering**: Filter busy stops (such as Princes Street or Haymarket) down to specific services via card config or interactive filter pills in the card header.
- **Live Fleet & Status Badges**: Vehicle fleet numbers (`#489`), live GPS speed (mph) & compass heading, and `Diverted` / `Part route` disruption alerts.
- **Home Assistant Assist & Voice Schedule Sensors**: Automatically exposes natural-language schedule sensors per stop and per route to Home Assistant Assist (`conversation`), plus a `lothian_buses.get_schedule` action for automations and TTS announcements.

---

## Installation

### Method 1: Home Assistant Marketplace / HACS (Recommended)

1. Open Home Assistant and navigate to **Marketplace** (or **HACS**).
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Add the URL of this repository: `https://github.com/vinodmishra/ha-lothianbuses`
4. Select the category **Integration**.
5. Click **Add** and then download **Lothian Buses & Edinburgh Trams**.
6. Restart Home Assistant.

### Method 2: Manual

1. Download or clone this repository.
2. Copy the `custom_components/lothian_buses` directory to your `custom_components` directory in your Home Assistant configuration folder.
3. Restart Home Assistant.

---

## Configuration & Setup

### Step 1: Add the Integration in Home Assistant

1. In Home Assistant, navigate to **Settings → Devices & Services → Add Integration**.
2. Search for **Lothian Buses & Edinburgh Trams** and select it.
3. Choose **Add stops later from the dashboard card editor** (recommended) or search for stops immediately during setup.

### Step 2: Add Stops & the Dashboard Card

You can add stops in either of two ways:

- **Directly from your dashboard (easiest)**:
  1. Edit any Lovelace dashboard and click **Add Card**.
  2. Select **Lothian Buses & Edinburgh Trams Card**.
  3. Type a stop name, street, route number, or 8-digit stop code in the search box and click the matching stop. The integration creates the stop subentry and links the sensor automatically.
- **From the Integration page**:
  1. Go to **Settings → Devices & Services → Lothian Buses & Edinburgh Trams**.
  2. Click **Add stop** and search by stop name, street, route, or 8-digit stop code.

---

## Lovelace Card (`custom:lothian-bus-card`)

### Visual Editor Options

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `entity` | `string` | *(required)* | Primary stop sensor entity ID (e.g. `sensor.clerwood_terminus_at_n_next_arrival`) |
| `title` | `string` | *(auto)* | Custom stop title override |
| `max_departures` | `number` | `6` | Maximum number of upcoming departures to display (`1`–`20`) |
| `routes` | `string[]` | `[]` | Optional list of route numbers to display (e.g. `["26", "31"]`) |
| `compact` | `boolean` | `false` | Compact single-line row layout for dense dashboards |
| `show_header` | `boolean` | `true` | Show the Mushroom-style stop header |
| `show_route_filter` | `boolean` | `true` | Show interactive route filter chips when multiple routes serve the stop |
| `show_vehicle_info` | `boolean` | `true` | Show live vehicle fleet badge (`#489`), GPS speed (mph), and heading |
| `show_clock` | `boolean` | `true` | Show live clock in the card header |

### Example YAML

```yaml
type: custom:lothian-bus-card
entity: sensor.princes_street_next_arrival
title: Princes Street (Westbound)
max_departures: 6
routes:
  - "26"
  - "44"
  - "Tram"
compact: false
show_header: true
show_route_filter: true
show_vehicle_info: true
show_clock: true
```

---

## Schedule Sensors & Home Assistant Assist

Each configured stop creates a device with sensors that are automatically exposed to **Home Assistant Assist (`conversation`)**:

| Sensor | Entity Suffix | State Description |
| :--- | :--- | :--- |
| **Next arrival** | `*_next_arrival` | Minutes until the next departure (`int`, `duration`) + full `departures` and `spoken_schedule` attributes |
| **Next departure time** | `*_next_departure_time` | Exact `timestamp` of the next departure |
| **Next service** | `*_next_service` | Summary of the next service (e.g. `Route 14 to Muirhouse in 5 min (23:04)`) |
| **Upcoming schedule** | `*_upcoming_schedule` | Next 4 departures across all routes (e.g. `14 to Muirhouse: 5 min (23:04); 21 to Gyle Centre: 12 min (23:11)`) |
| **Route `<X>` schedule** | `*_route_<x>_schedule` | Next 3 departures for a specific route at this stop (e.g. `To Muirhouse: 5 min (23:04), 35 min (23:34)`) |

### Using the `lothian_buses.get_schedule` Action

You can also query live stop schedules on demand in Developer Tools, scripts, or automations (returns `spoken_summary` and structured `stops` data):

```yaml
action: lothian_buses.get_schedule
data:
  stop_id: "36253698"
  route: "14"
  max_departures: 4
response_variable: bus_schedule
```

---

## Data Attribution

- Real-time departure and vehicle telemetry provided by **Lothian Buses / Transport for Edinburgh** (`lothianapi.com`).
- Stop location and locality metadata contains public sector information licensed under the **UK Open Government Licence v3.0** from the Department for Transport **NaPTAN** dataset.
