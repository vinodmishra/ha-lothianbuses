# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.1.0

### Added
- Initial release of the Lothian Buses & Edinburgh Trams custom component and bundled Lovelace card.
- Bundled stop and route directory covering 4,316 stops across Edinburgh, Midlothian, East Lothian, West Lothian, and Fife (including Edinburgh Trams to Newhaven).
- Auto-registered Mushroom-style custom Lovelace card (`custom:lothian-bus-card`) with live stop search, one-click stop creation, official route colour pills, route filtering, and an expandable stop-by-stop trip progress timeline.
- Shared live vehicle fleet telemetry cache (`/vehicles/all`) providing fleet numbers, live GPS speed, and compass headings.
- Dedicated schedule sensors per stop (`Next arrival`, `Next departure time`, `Next service`, `Upcoming schedule`, and per-route `Route X schedule` sensors) automatically exposed to Home Assistant Assist (`conversation`).
- Included `lothian_buses.get_schedule` action (`SupportsResponse.ONLY`) for on-demand schedule lookups in automations, scripts, and voice assistants.
