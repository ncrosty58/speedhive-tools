
# speedhive-tools — Python Client (Updated README)

A robust, retry-friendly Python client for the **MYLAPS Speedhive Event Results API**. This README documents the endpoints implemented in `client.py`, clarifies the valid public base URL, and provides usage examples plus export helpers.

> **Public base URL** (recommended):
>
> - `https://eventresults-api.speedhive.com/api/v0.2.3/eventresults`
>
> This is the Event Results API used by this client by default.

> **Note on `api.speedhive.com`**: The client contains a conditional branch that treats the hostname `api.speedhive.com` as a distinct path family (`orgs`). This appears to be **legacy/internal** and is **not** publicly documented. Do **not** set your `base_url` to `api.speedhive.com`. Use the default Event Results base shown above.

---

## Installation

Clone the repository and install locally:

```bash
git clone https://github.com/ncrosty58/speedhive-tools
cd speedhive-tools
pip install -e .  # editable install
```

If a published package exists, you can instead do:

```bash
pip install speedhive-tools
```

---

## Quick Start

```python
from speedhive_tools.client import SpeedHiveClient

client = SpeedHiveClient(
    api_key="YOUR_API_KEY",                 # optional; some endpoints may work without
    base_url="https://eventresults-api.speedhive.com/api/v0.2.3/eventresults",  # default
    timeout=30,
    retries=2,
    rate_delay=0.0,
)

# Fetch an organization by ID
org = client.get_organization(12345)

# List events for an organization (auto pagination)
events = client.list_organization_events(12345, auto_paginate=True)

# Get results for a specific event
result = client.get_event_results(67890)

# Get track records for an org
records = client.get_track_records_by_org(12345)

# Export records in CSV
client.export_records_to_csv(12345, "out/records.csv")
```

---

## Path Prefix & Pagination

With the public base URL above, the client uses the **`organizations`** path prefix and **offset/count** pagination.

- Path prefix examples:
  - `GET /organizations/{org_id}`
  - `GET /organizations/{org_id}/events`
  - `GET /organizations/{org_id}/records`
- Pagination: `offset` + `count`

Internally, the client still contains logic for an `orgs` path family if the hostname equals `api.speedhive.com`. That branch is kept for **compatibility** but is not needed for public usage.

---

## Endpoint Reference & Usage

Paths shown are **relative** to `base_url`.

### Organizations

#### Get an organization
- **Method**: `get_organization(org_id: int) -> Organization`
- **Endpoint**: `/{orgs_prefix}/{org_id}` (prefix resolves to `organizations`)

#### List an organization’s events
- **Method**: `list_organization_events(org_id: int, *, per_page=None, page=None, count=None, offset=None, auto_paginate=False) -> List[EventResult]`
- **Endpoint**: `/{orgs_prefix}/{org_id}/events`
- **Pagination behavior** (public base):
  - If `auto_paginate=True`, iterates `offset`/`count` until exhausted.
  - Else, returns a single page using provided `count` and `offset`.
- **Convenience (raw)**: `get_events_for_org(org_id, count=200, offset=0) -> List[Dict]` returns raw event dicts.

#### Stream an organization’s events (raw)
- **Method**: `iter_organization_events(org_id: int, *, count: int = 200) -> Iterator[Dict]`
- **Endpoint**: `/{orgs_prefix}/{org_id}/events`

### Event Results

#### Get results for a specific event
- **Method**: `get_event_results(event_id: int) -> EventResult`
- **Endpoint**: `/events/{event_id}/results`

### Track Records (By Organization)

#### Get track records for an organization
- **Method**: `get_track_records_by_org(org_id: int) -> List[TrackRecord]`
- **Endpoint**: `/{orgs_prefix}/{org_id}/records`

### Event Sessions & Announcements

#### List sessions for an event (flattened)
- **Method**: `get_sessions_for_event(event_id: int) -> List[Dict]`
- **Endpoint**: `/events/{event_id}/sessions`

#### Get announcements for a session
- **Method**: `get_session_announcements(session_id: int) -> List[Dict]`
- **Endpoint**: `/sessions/{session_id}/announcements`

#### Walk all sessions & announcements for an org
- **Method**: `get_all_session_announcements_for_org(org_id: int) -> List[Dict]`
- **Process**:
  1. List org events.
  2. For each event, list sessions.
  3. For each session, fetch announcements.
  4. Enrich rows with `eventId`, `eventName`, `sessionName`, `eventDate`, and `trackName`.

### Global Events Feed

#### List global events
- **Method**: `list_global_events(*, sport="All", sport_category="Motorized", count=200, offset=0, auto_paginate=True, extra_params=None) -> List[EventResult]`
- **Endpoint**: `/events`
- **Query Parameters**:
  - `sport`: defaults to `"All"`
  - `sportCategory`: defaults to `"Motorized"`
  - Any additional filters can be supplied via `extra_params` (merged into query string).

#### Stream global events (low-RAM)
- **Method**: `iter_global_events(*, sport="All", sport_category="Motorized", count=200, start_offset=0, extra_params=None) -> Iterator[Dict]`
- **Endpoint**: `/events`

### Lap Data (Per Session & Position)

#### Get lap data
- **Method**: `get_session_lap_data(session_id: int, position: int = 1) -> List[Dict]`
- **Endpoint**: `/sessions/{session_id}/lapdata/{position}/laps`

#### Stream lap data
- **Method**: `iter_session_lap_data(session_id: int, position: int = 1) -> Iterator[Dict]`
- **Endpoint**: `/sessions/{session_id}/lapdata/{position}/laps`

#### Export lap data to NDJSON
- **Method**: `export_session_lapdata_to_ndjson(session_id: int, position: int, out_path: Union[str, Path]) -> int`
- **Writes**: One JSON object per line at `out_path`, returning the number of rows written.

---

## Announcement Parsing → TrackRecord

- Detects “New Track Record” / “New Class Record” variants and ignores negations like “unofficial”, “not counted”, etc.
- Supports multiple textual patterns, including:
  - `New (MM:SS.mmm) for CLASS by DRIVER in MARQUE`
  - `New (MM:SS.mmm) for CLASS by DRIVER`
  - Separator-based announcements: `CLASS • TIME • DRIVER • (MARQUE) • DATE`
- Validation via `is_record_valid(record)` ensures required fields are present (`lapTime`, `driverName`, `trackName`, `classAbbreviation`).
- CamelCase export (`export_records_to_json_camel`) **normalizes** lap time to `M:SS.mmm`.

---

## Export Helpers

- `export_records_to_json(org_or_records, out_path) -> int`
- `export_records_to_csv(org_or_records, out_path) -> int`
- `export_records_to_json_camel(org_or_records, out_path) -> int`
- `export_session_lapdata_to_ndjson(session_id, position, out_path) -> int`

For all export methods, you may pass either an `org_id` (int) or a pre-fetched iterable of `TrackRecord` objects.

---

## Error Handling

All HTTP and parsing issues raise `SpeedHiveAPIError(message, status=None, url=None)`.

- Status ≥ 400: detailed message with response preview.
- Network failures are wrapped with URL context.
- `204 No Content` → `{}`.
- Invalid JSON → `SpeedHiveAPIError("Invalid JSON response")`.

---

## License

MIT (see repository license).

