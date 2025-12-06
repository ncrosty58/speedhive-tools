
# speedhive-tools

Utilities and a robust Python client for working with **MYLAPS Speedhive Event Results**—organizations, events, sessions, announcements, and (derived) track/class records. The client targets the **Event Results API**:

> **Base URL:** `https://eventresults-api.speedhive.com/api/v0.2.3/eventresults`  
> Swagger documents paths like `/events`, `/events/{id}/sessions`, `/organizations/{id}`, `/organizations/{id}/events`, `/sessions/{id}/announcements`, etc.  
> Sources: [Event Results Swagger](https://eventresults-api.speedhive.com/swagger/docs/v1), [Speedhive site](https://speedhive.mylaps.com/), [MYLAPS Speedhive overview](https://mylaps.com/motorsports/services/speedhive/)

---

## Table of Contents
- [Quick Start](#quick-start)
- [Global Events Feed (New)](#global-events-feed-new)
- [Endpoints used by this client](#endpoints-used-by-this-client)
- [Python Examples](#python-examples)
  - [Get an organization](#get-an-organization)
  - [List events for an organization](#list-events-for-an-organization)
  - [Get event details (+sessions)](#get-event-details-sessions)
  - [Get sessions for an event](#get-sessions-for-an-event)
  - [Get announcements for a session](#get-announcements-for-a-session)
  - [Walk org → events → sessions → announcements](#walk-org--events--sessions--announcements)
  - [Records (derived from announcements)](#records-derived-from-announcements)
  - [Export JSON/CSV](#export-jsoncsv)
- [Low‑RAM Streaming Dump](#low-ram-streaming-dump)
- [Headers, retries, and errors](#headers-retries-and-errors)
- [Notes](#notes)
- [License](#license)

---

## Quick Start

> **Heads‑up:** In the current repo layout, the client module file is `speedhive_client.py`. Until you package this as `speedhive_tools/`, import from the file directly. (If you publish to PyPI later, the `from speedhive_tools.client import SpeedHiveClient` import will be correct.)

```bash
pip install requests
```

```python
# Current repo layout (top-level module file):
from speedhive_client import SpeedHiveClient

client = SpeedHiveClient(
    base_url="https://eventresults-api.speedhive.com/api/v0.2.3/eventresults",
    timeout=30,
    retries=2,
    rate_delay=0.25,
)
```

---

## Global Events Feed (New)

Two public client methods expose the **global `/events`** feed. The API supports filters `sport`, `sportCategory` and pagination via `count`/`offset`. It also accepts `startDate`, `endDate`, and `country`. (Leave `sport` unset to get all sports—`"All"` is a UI label, not a valid enum value.)  
Source: [Event Results Swagger](https://eventresults-api.speedhive.com/swagger/docs/v1)

```python
# Stream raw global events (low RAM)
for ev in client.iter_global_events(
        sport=None,  # None = all sports
        sport_category="Motorized",
        count=200,
        start_date=None, end_date=None, country=None):
    print(ev.get("id"), ev.get("name"))

# Return mapped EventResult-like objects from the global feed (auto-paginates)
results = client.list_global_events(
    sport=None, sport_category="Motorized", count=200)
for er in results:
    print(er.event_id, er.event_name)
```

> The `/events` path and its query params (`sport`, `sportCategory`, `count`, `offset`, `startDate`, `endDate`, `country`) are documented in the Event Results Swagger.

---

## Endpoints used by this client

All paths below are relative to the base: **`/api/v0.2.3/eventresults`**.  
Source: [Event Results Swagger](https://eventresults-api.speedhive.com/swagger/docs/v1)

| Method | Path | What it returns |
| :-- | :-- | :-- |
| **GET** | `/events` | **Global events** list with filters (`sport`, `sportCategory`, `count`, `offset`, `startDate`, `endDate`, `country`). Returns an **array of `EventDto`**. |
| **GET** | `/events/{eventId}` | A single **event**; optional `sessions=true` to include a `SessionGroupingDto`. |
| **GET** | `/events/{id}/sessions` | A **`SessionGroupingDto`** containing `groups` and `sessions`. |
| **GET** | `/organizations/{id}` | **Organization** details. |
| **GET** | `/organizations/{id}/events` | A list of **events for the organization** (`count`, `offset`, optional `sportCategory`). |
| **GET** | `/sessions/{id}/announcements` | **Run announcements** (`RunAnnouncementsDto` with `rows[timestamp,text]`). |
| **GET** | `/sessions/{id}/classification` | **Classification** rows for a session. |
| **GET** | `/sessions/{id}/lapchart` | **Lap chart** for a session. |

> Response types like `EventDto`, `SessionGroupingDto`, `RunAnnouncementsDto`, and the presence of `rows` within announcements are defined in Swagger.

> **Note:** There is **no `/events/{eventId}/results`** endpoint in the Swagger. Pull per‑event data via `events/{eventId}?sessions=true` plus session endpoints (classification, lapchart, announcements).

---

## Python Examples

> The site pages below are just illustrative examples of Waterford Hills sessions found in Speedhive; your client consumes the API endpoints above.  
> Examples: [Session 6764536](https://speedhive.mylaps.com/sessions/6764536), [Session 9234119](https://speedhive.mylaps.com/sessions/9234119), [Session 11334071](https://speedhive.mylaps.com/sessions/11334071)

### Get an organization
```python
client = SpeedHiveClient()
org = client.get_organization(30476)  # Waterford Hills example
print(org.name, org.city, org.country)
```

### List events for an organization
```python
events = client.list_organization_events(30476, auto_paginate=True)
for ev in events:
    print(ev.event_name, ev.startDate)
```

### Get event details (+sessions)
```python
event = client.get_event(1234, include_sessions=True)  # sessions=true
print(event.name, bool(event.sessions))
```

### Get sessions for an event
```python
sessions_grouping = client.get_sessions_for_event(1234)
print([s.get("id") for s in (sessions_grouping.get("sessions") or [])])
```

### Get announcements for a session
```python
rows = client.get_session_announcements(9001)
texts = [client.get_announcement_text(r) for r in rows]
print(texts[:3])
```

### Walk org → events → sessions → announcements
```python
all_rows = client.get_all_session_announcements_for_org(30476)
print(f"rows={len(all_rows)}")

# Filter record-like announcements
record_rows = [
    r for r in all_rows
    if client.find_track_record_announcements(client.get_announcement_text(r))
]
print(f"record-like rows={len(record_rows)}")

# Parse into TrackRecord models (derived from announcements)
records = []
for r in record_rows:
    tr = client.parse_track_record_announcement(r)  # text → TrackRecord
    ok, reason = client.is_record_valid(tr)
    if ok or (reason and "Missing classAbbreviation" in str(reason)):
        records.append(tr)
```

### Records (derived from announcements)
```python
normalized = client.get_track_records_by_org(30476)
for tr in normalized:
    print(tr.driver_name, tr.lap_time, tr.class_name)
```

### Export JSON/CSV
```python
client.export_records_to_json(normalized, "records_snake.json")
client.export_records_to_json_camel(normalized, "records_camel.json")
client.export_records_to_csv(normalized, "records.csv")
```

---

## Low‑RAM Streaming Dump

A ready‑to‑use script streams the global feed, deduplicates org IDs, and iteratively dumps per‑org data (events → sessions → announcements → derived records) to **NDJSON/JSON**—keeping RAM usage tiny. It follows the API’s `/events` feed and org‑scoped endpoints above.  
Source: [Event Results Swagger](https://eventresults-api.speedhive.com/swagger/docs/v1)

```bash
python dump_speedhive_database_streaming.py
```

- Appends NDJSON under `./dump/` and a small **SQLite index** `dump/index.sqlite` (tables: `orgs`, `progress`) to dedupe orgs & resume.  
- Set `SPEEDHIVE_API_KEY` if your environment requires an API key for some endpoints.  
- Example event/session pages for Waterford Hills are available on Speedhive for reference; your client uses API endpoints rather than HTML scraping.

> Repo note: Current tree shows `speedhive_client.py` and `speedhive_example_runner.py`. Add the streaming dump script next to them or update docs accordingly.  
> Source: [ncrosty58/speedhive-tools (repo index)](https://github.com/ncrosty58/speedhive-tools)

---

## Headers, retries, and errors

The client sends:
```
Accept: application/json
User-Agent: speedhive-tools (+https://github.com/ncrosty58/speedhive-tools)
Apikey: <your_api_key>  # only if provided
```

Many Event Results endpoints indicate `Apikey` security in Swagger; public reads generally work without a key, but you can pass one if your environment requires it.  
Source: [Event Results Swagger](https://eventresults-api.speedhive.com/swagger/docs/v1)

We use a pooled `requests.Session` with retry/backoff for GETs. JSON parse errors, HTTP ≥ 400, and network exceptions raise `SpeedHiveAPIError(message, status, url)`.

---

## Notes

- This README covers **Event Results** endpoints your client calls. Speedhive’s site/app surfaces that same Event Results platform for global event discovery and per‑event results.  
Sources: [Speedhive site](https://speedhive.mylaps.com/), [MYLAPS Speedhive overview](https://mylaps.com/motorsports/services/speedhive/)
- **Practice APIs** live under different bases (e.g., `https://practice-api.speedhive.com`) and are **not used** by this client. Swagger UIs are published separately.  
Sources: [Practice Swagger UI](https://practice-api.speedhive.com/swagger/ui/index)
- Response shapes vary:  
  - `/events` → **array** of `EventDto`.  
  - `/events/{id}/sessions` → **`SessionGroupingDto`** with `groups` & `sessions`.  
  - `/sessions/{id}/announcements` → **`RunAnnouncementsDto`** with `rows`.  
These are documented in Swagger and handled automatically by the client.  
Source: [Event Results Swagger](https://eventresults-api.speedhive.com/swagger/docs/v1)

---

## License
MIT (see `LICENSE`).
