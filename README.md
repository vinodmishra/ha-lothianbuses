# Lothian Buses & Edinburgh Trams for Home Assistant

Real-time **Lothian Buses**, **Lothian Country**, **East Coast Buses**, **NightBus**, and **Edinburgh Trams** departure boards for Home Assistant, complete with an automatically registered **Mushroom-style Lovelace card**, instant stop search, official route colour badges, live vehicle GPS telemetry, and an interactive stop-by-stop trip progress timeline.

Inspired by [`ha-london-dotmatrix`](https://github.com/szbence7/ha-london-dotmatrix), redesigned around a clean, native Home Assistant / Mushroom card aesthetic.

---

## Features

- **Bundled Stop & Route Directory**: Ships with **4,316 stops** across Edinburgh, Midlothian, East Lothian, West Lothian, and Fife (including all Edinburgh Trams stops to Newhaven) pre-mapped with routes, streets, localities, and compass bearings.
- **Live Stop Search in the Card Editor**: Search by stop name (`Princes Street`), street, locality (`Leith`), route number (`26`, `T50`, `N16`), or 8-digit SMS stop code (`36238285`) and add stops to Home Assistant with one click — without leaving your dashboard.
- **Official Route Colour Badges**: Authentic Lothian Buses, Lothian Country, East Coast Buses, NightBus, and Edinburgh Trams colour pills.
- **Interactive Trip Progress Drawer**: Click any live departure row to expand a real-time stop-by-stop timeline (`/trips/progress/app`) showing passed stops, your current stop, and upcoming stops with live ETAs.
- **Per-Card Route Filtering**: Filter busy stops (such as Princes Street or Haymarket) down to specific services via card config or interactive filter pills in the card header.
- **Live Fleet & Status Badges**: Optional vehicle fleet numbers (`#489`, `#T252`), live GPS speed (mph) & compass heading, low-floor accessibility indicators, and `Diverted` / `Part route` disruption alerts.
- **Recorder-Friendly**: Full departure arrays and route metadata are excluded from the Home Assistant Recorder database (`_unrecorded_attributes`) to prevent database bloat while keeping the primary sensor state (`minutes to next arrival`) available for automations and history graphs.

---

## Installation

1. Copy the `custom_components/lothian_buses` folder into your Home Assistant `<config>/custom_components/` directory (or add the repository via the built-in Home Assistant Marketplace).
2. **Restart Home Assistant**.

---

## Setup

1. Go to **Settings -> Devices & Services -> Add Integration**.
2. Search for **Lothian Buses & Edinburgh Trams** and add it (optionally adjust the polling interval; default is `30` seconds).
3. Add stops in either of two ways:
   - **Directly from your dashboard (easiest)**: Edit any Lovelace dashboard -> **Add Card** -> choose **Lothian Buses & Trams Card** -> type a stop name, street, route, or 8-digit stop code in the search box and click it. The integration creates the stop subentry and links the sensor automatically.
   - **From the Integration page**: Go to **Settings -> Devices & Services -> Lothian Buses & Edinburgh Trams** -> click **Add stop** and enter a stop name or 8-digit stop code.

---

## Lovelace Card (`custom:lothian-bus-card`)

The custom card is automatically served at `/lothian_buses/lothian-bus-card.js` and registered in Lovelace storage mode on startup.

### Visual Editor Options

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `entity` | `string` | *(required)* | Sensor entity ID (e.g. `sensor.clerwood_next_arrival`) |
| `title` | `string` | *(auto)* | Custom stop title override |
| `max_departures` | `number` | `6` | Maximum number of upcoming departures to display (`1`–`20`) |
| `routes` | `string[]` | `[]` | Optional list of route numbers to display (e.g. `["26", "31"]`) |
| `compact` | `boolean` | `false` | Compact row layout for dense dashboards |
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

## Sensor Attributes

Each stop creates a `sensor.<stop_name>_next_arrival` entity:

- **State**: Minutes until the next departure (`int`, or `None` when no departures are scheduled).
- **Attributes**:
  - `stop_id`: 8-digit SMS/NaPTAN stop code (e.g. `36238285`)
  - `stop_name`: Official stop name
  - `identifier`: Stop letter/bay identifier (e.g. `PQ`, `at`)
  - `direction`: Compass direction (`N`, `NE`, `E`, `SE`, `S`, `SW`, `W`, `NW`)
  - `street`: Street name
  - `locality`: Town/area (e.g. `Clermiston`, `Leith`)
  - `modes`: Active transit modes at this stop (`["bus"]`, `["tram"]`, or `["bus", "tram"]`)
  - `next_route`: Route number of the next service (`26`, `Tram`, etc.)
  - `next_destination`: Destination of the next service
  - `next_departure_time`: Scheduled/expected HH:MM time
  - `next_real_time`: `true` if live GPS tracked
  - `next_vehicle_id`: Fleet ID of the approaching vehicle
  - `departures`: Full list of upcoming departures with route colours, vehicle telemetry, and expected timestamps *(unrecorded)*
  - `lines`: Route metadata and colours serving the stop *(unrecorded)*

---

## Data Attribution

- Real-time departure and vehicle telemetry provided by **Lothian Buses / Edinburgh Trams** (`lothianapi.com`).
- Stop location and locality metadata contains public sector information licensed under the **UK Open Government Licence v3.0** from the Department for Transport **NaPTAN** dataset.
