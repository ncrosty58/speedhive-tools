# speedhive-tools

Utilities and a robust Python client for working with MYLAPS Speedhive **Event Results**: organizations, events, sessions, announcements, and track/class records.

This README documents the endpoints your client calls and shows how to use the Python API to reach them.

> **Base URL (Event Results API):**
>
> `https://eventresults-api.speedhive.com/api/v0.2.3/eventresults`

---

## Table of Contents

- [Quick Start](#quick-start)
- [Endpoints used by this client](#endpoints-used-by-this-client)
- [How to call endpoints via the Python API](#how-to-call-endpoints-via-the-python-api)
  - [Get an organization](#get-an-organization)
  - [List events for an organization](#list-events-for-an-organization)
  - [Get event results](#get-event-results)
  - [Get sessions for an event](#get-sessions-for-an-event)
  - [Get announcements for a session](#get-announcements-for-a-session)
  - [Walk org → events → sessions → announcements](#walk-org--events--sessions--announcements)
  - [Get records by organization](#get-records-by-organization)
  - [Export JSON/CSV](#export-jsoncsv)
- [Headers, retries, and errors](#headers-retries-and-errors)
- [Notes](#notes)

---

## Quick Start

```bash
pip install requests
```

```python
from speedhive_tools.client import SpeedHiveClient

client = SpeedHiveClient(
    base_url="https://eventresults-api.speedhive.com/api/v0.2.3/eventresults",
    timeout=30,
    retries=2,
    rate_delay=0.25,
)
```

---

## Endpoints used by this client

All paths below are relative to the base: `.../api/v0.2.3/eventresults`.

- **GET** `/organizations/{org_id}` — organization details (mapped to `Organization`).
- **GET** `/organizations/{org_id}/events` — list events (offset/count; client can auto‑paginate).
- **GET** `/events/{event_id}/results` — event result plus optional `records` list; mapped to `EventResult`.
- **GET** `/events/{event_id}/sessions` — nested groups/sessions; client flattens to a list.
- **GET** `/sessions/{session_id}/announcements` — rows with announcement text; client normalizes.
- **GET** `/organizations/{org_id}/records` — organization’s track/class records; mapped to `TrackRecord`.

> Responses may be either a top‑level list or an object containing keys like `items`, `events`, or `rows`. The client handles these variants.

---

## How to call endpoints via the Python API

### Get an organization

```python
from speedhive_tools.client import SpeedHiveClient
client = SpeedHiveClient()
org = client.get_organization(30476)  # Waterford Hills
print(org.name, org.city, org.country)
```

### List events for an organization

```python
events = client.list_organization_events(30476, auto_paginate=True)
for ev in events:
    print(ev.event_name, ev.startDate)
```

### Get event results

```python
ev = client.get_event_results(1234)
print(ev.event_name, len(ev.records))
```

### Get sessions for an event

```python
sessions = client.get_sessions_for_event(1234)
print([s.get("id") for s in sessions])
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

# Filter only track/class record announcements
record_rows = [r for r in all_rows if client.find_track_record_announcements(client.get_announcement_text(r))]
print(f"record-like rows={len(record_rows)}")

# Parse into TrackRecord models
records = []
for r in record_rows:
    tr = client.parse_track_record_announcement(r)
    ok, reason = client.is_record_valid(tr)
    if ok or (reason and "Missing classAbbreviation" in str(reason)):
        records.append(tr)
```

### Get records by organization

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

## Headers, retries, and errors

The client sends:

```
Accept: application/json
User-Agent: speedhive-tools (+https://github.com/ncrosty58/speedhive-tools)
Apikey: <your_api_key>  # only if provided
```

It uses a pooled `requests.Session` with retry/backoff for idempotent methods. JSON parse errors, HTTP ≥ 400, and network exceptions raise `SpeedHiveAPIError(message, status, url)`.

---

## Notes

- This README covers the Event Results API endpoints your client calls.
- Practice‑related APIs exist under different bases but are **not used** by this client.
- Response shapes vary (list vs object with `items`/`events`/`rows`); the client already handles those variants.

---

## License

MIT (see `LICENSE`).
