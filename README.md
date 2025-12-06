
# speedhive-tools — Python Client

A robust, retry-friendly Python client for the **Speedhive Event Results API**. This README documents the endpoints implemented in `client.py`, highlights pagination behavior across different API host families, and provides usage examples plus export helpers.

> **Targets**: Works with Speedhive's event results endpoints hosted under both:
>
> - `https://eventresults-api.speedhive.com/api/v0.2.3/eventresults` *(default)* — uses the `organizations` path family.
> - `https://api.speedhive.com` *(if you set `base_url` to this host)* — uses the `orgs` path family.
>
> The client auto-detects which path family to use based on the hostname you pass in `base_url`.

---

## Installation

```bash
pip install speedhive-tools
```

(Or include this client in your project as a module. Ensure `requests` is available.)

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

# List events for an organization (auto pagination based on host family)
events = client.list_organization_events(12345)

# Get results for a specific event
result = client.get_event_results(67890)

# Get track records for an org
records = client.get_track_records_by_org(12345)

# Export records in CSV
client.export_records_to_csv(12345, "out/records.csv")
```

---

## Authentication & Headers

The client sets these default headers:

- `Accept: application/json`
- `User-Agent: speedhive-tools (+https://github.com/ncrosty58/speedhive-tools)`
- If you provide `api_key`, it sets `Apikey: <YOUR_API_KEY>`.

Retries are enabled for idempotent methods (`GET`, `HEAD`, `OPTIONS`) with a backoff factor of `0.5`. You can adjust connection pool sizes via `pool_connections` and `pool_maxsize` in the constructor.

---

## Path Families & Pagination Semantics

Two Speedhive host families use different path prefixes **and** pagination styles; the client handles both:

- **`organizations` family** (default base URL):
  - Path prefix: `organizations`
  - Pagination: `offset` / `count` (numeric offset + page size)
  - Methods here use the client's internal `offset` paginator.

- **`orgs` family** (`api.speedhive.com`):
  - Path prefix: `orgs`
  - Pagination: `page` / `per_page` (page number + page size) and a top-level `totalPages` value.
  - Methods here use the client's internal `page` paginator and iterate pages until `totalPages`.

You don’t need to choose this manually—**the client auto-selects** based on the `base_url` hostname.

---

## Endpoint Reference & Usage

Below are the implemented endpoints and their corresponding client methods. Paths shown are **relative** to `base_url`.

### Organizations

#### Get an organization
- **Method**: `get_organization(org_id: int) -> Organization`
- **Endpoint**: `/{orgs_prefix}/{org_id}`
  - `orgs_prefix` is either `organizations` or `orgs` depending on `base_url`.
- **Returns**: An `Organization` model built from the API payload.

#### List an organization’s events
- **Method**: `list_organization_events(org_id: int, *, per_page=None, page=None, count=None, offset=None, auto_paginate=False) -> List[EventResult]`
- **Endpoints**:
  - `/{orgs_prefix}/{org_id}/events`
- **Pagination behavior**:
  - For `orgs` family: uses `page`/`per_page` and **fetches all pages** (up to `totalPages`) even when `auto_paginate=False`.
  - For `organizations` family: if `auto_paginate=True`, iterates `offset`/`count` until exhausted; otherwise returns a single page using provided `count` and `offset`.
- **Convenience (raw)**: `get_events_for_org(org_id, count=200, offset=0) -> List[Dict]` returns raw event dicts, honoring the active path family.

### Event Results

#### Get results for a specific event
- **Method**: `get_event_results(event_id: int) -> EventResult`
- **Endpoint**: `/events/{event_id}/results`
- **Notes**:
  - Handles variations in payload shape (`event`, `result`, `records`, `items`, `results`).
  - Normalizes into a single `EventResult` model.

### Track Records (By Organization)

#### Get track records for an organization
- **Method**: `get_track_records_by_org(org_id: int) -> List[TrackRecord]`
- **Endpoint**: `/{orgs_prefix}/{org_id}/records`
- **Notes**:
  - Accepts different payload wrappers (`records`, `items`, list).
  - Maps rows to `TrackRecord` with tolerant field picking.

### Event Sessions & Announcements

#### List sessions for an event (flattened)
- **Method**: `get_sessions_for_event(event_id: int) -> List[Dict]`
- **Endpoint**: `/events/{event_id}/sessions`
- **Notes**:
  - The API may return grouped structures (`groups` nesting). The client recursively flattens to a simple list of session dicts.

#### Get announcements for a session
- **Method**: `get_session_announcements(session_id: int) -> List[Dict]`
- **Endpoint**: `/sessions/{session_id}/announcements`
- **Notes**:
  - Returns rows (`rows`), ensures each row has `sessionId`.
  - If `text` is missing/blank, derives a textual representation using `get_announcement_text`.

#### Walk all sessions & announcements for an org
- **Method**: `get_all_session_announcements_for_org(org_id: int) -> List[Dict]`
- **Process**:
  1. List org events (using the correct pagination family).
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
- **Notes**:
  - If `auto_paginate=True`, uses offset/count pagination until exhausted.

#### Stream global events (low-RAM)
- **Method**: `iter_global_events(*, sport="All", sport_category="Motorized", count=200, start_offset=0, extra_params=None) -> Iterator[Dict]`
- **Endpoint**: `/events`
- **Returns**: An iterator over raw event dicts.

### Lap Data (Per Session & Position)

#### Get lap data
- **Method**: `get_session_lap_data(session_id: int, position: int = 1) -> List[Dict]`
- **Endpoint**: `/sessions/{session_id}/lapdata/{position}/laps`
- **Returns**: List of lap dictionaries (or empty list if none / unexpected payload).

#### Stream lap data
- **Method**: `iter_session_lap_data(session_id: int, position: int = 1) -> Iterator[Dict]`
- **Endpoint**: `/sessions/{session_id}/lapdata/{position}/laps`

#### Export lap data to NDJSON
- **Method**: `export_session_lapdata_to_ndjson(session_id: int, position: int, out_path: Union[str, Path]) -> int`
- **Writes**: One JSON object per line at `out_path`, returning the number of rows written.

---

## Announcement Parsing → TrackRecord

The client includes robust parsing to turn announcement text into `TrackRecord` objects:

- Detects “New Track Record” / “New Class Record” variants and ignores negations like “unofficial”, “not counted”, etc.
- Supports multiple textual patterns, including:
  - `New (MM:SS.mmm) for CLASS by DRIVER in MARQUE`  
  - `New (MM:SS.mmm) for CLASS by DRIVER`  
  - Separator-based announcements: `CLASS • TIME • DRIVER • (MARQUE) • DATE`  
  - Fallback anchored on lap time with heuristic extraction of class, driver, marque, and date.
- Validation via `is_record_valid(record)` ensures required fields are present (`lapTime`, `driverName`, `trackName`, `classAbbreviation`).

> **CamelCase export normalization**: when exporting records in camelCase (`export_records_to_json_camel`), lap times are normalized to `M:SS.mmm`. If the `lap_time` field is a float (seconds), it is formatted accordingly.

---

## Export Helpers

- `export_records_to_json(org_or_records, out_path) -> int`  
  Writes `{ "records": [...] }` to `out_path` (snake_case field names). Returns count.

- `export_records_to_csv(org_or_records, out_path) -> int`  
  Writes CSV with headers: `driver_name, lap_time, track_name, date, vehicle, class_name`. Returns count.

- `export_records_to_json_camel(org_or_records, out_path) -> int`  
  Writes `{ "records": [...] }` with camelCase keys and **normalized** `lapTime`. Returns count.

- `export_session_lapdata_to_ndjson(session_id, position, out_path) -> int`  
  Writes lap rows (one per line) as NDJSON. Returns count.

For all export methods, you may pass either an `org_id` (int) or a pre-fetched iterable of `TrackRecord` objects.

---

## Error Handling

All HTTP and parsing issues raise `SpeedHiveAPIError(message, status=None, url=None)`. 

- A `status >= 400` yields a detailed message with a preview of the response body.
- Network failures (connection timeouts, DNS, etc.) are wrapped with URL context.
- `204 No Content` results in `{}`.
- Invalid JSON responses trigger `SpeedHiveAPIError("Invalid JSON response")`.

---

## Advanced Usage Examples

### Stream Org Events & Save Announcements as Records

```python
from speedhive_tools.client import SpeedHiveClient

client = SpeedHiveClient(api_key="YOUR_API_KEY")
rows = client.get_all_session_announcements_for_org(12345)

parsed_records = []
for row in rows:
    rec = client.parse_track_record_announcement(row)
    ok, reason = client.is_record_valid(rec)
    if ok:
        parsed_records.append(rec)

client.export_records_to_json_camel(parsed_records, "out/parsed-records.json")
```

### Global Events Filtered by Sport Category

```python
events = client.list_global_events(sport="Kart", sport_category="Motorized")
for e in events:
    print(e.name, e.id)
```

### Lap Data for P1 (Winner) in a Session

```python
laps = client.get_session_lap_data(session_id=555555, position=1)
print(f"Fetched {len(laps)} laps")
client.export_session_lapdata_to_ndjson(555555, 1, "out/laps.ndjson")
```

---

## Notes & Compatibility

- This client is tolerant of the API’s varying payload shapes and field names.
- It centralizes retries and timeouts via one `requests.Session` instance.
- When `rate_delay` is set, the client sleeps briefly between pagination batches, which can help avoid rate limits.

---

## Changelog (client additions)

- Added detection of host family (`orgs` vs `organizations`) and matching pagination helpers.
- Implemented `get_sessions_for_event`, `get_session_announcements`, and `get_all_session_announcements_for_org`.
- Added announcement parsing (regex heuristics) and `is_record_valid`.
- Implemented global events feed: `iter_global_events`, `list_global_events`.
- Added lap data endpoints: `get_session_lap_data`, `iter_session_lap_data`, `export_session_lapdata_to_ndjson`.
- Added record export helpers with camelCase normalization of `lapTime`.

---

## License

MIT (see repository license).

