# speedhive-tools

Utilities and a robust Python client for working with MYLAPS Speedhive **Event Results**: organizations, events, sessions, announcements, and track/class records.

This README documents **the actual endpoints your client calls** and shows **how to use your Python API** to reach them.

> **Important:** Use the **Event Results API** base:
>
> `https://eventresults-api.speedhive.com/api/v0.2.3/eventresults`  (public Swagger lists this family and version)  citeturn4search15
>
> Your client builds paths under that base and uses the **`organizations`** prefix (offset/count pagination). citeturn1search3

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

# Use the documented Event Results base
client = SpeedHiveClient(
    base_url="https://eventresults-api.speedhive.com/api/v0.2.3/eventresults",  # citeturn4search15
    timeout=30,
    retries=2,
    rate_delay=0.25,
)
```

The client sets the standard headers (including optional `Apikey` if provided) and handles retry/backoff for GETs. citeturn1search3

---

## Endpoints used by this client

All paths below are relative to the base: `.../api/v0.2.3/eventresults`. citeturn4search15

- **GET** `/organizations/{org_id}` — organization details (mapped to `Organization`). citeturn1search3
- **GET** `/organizations/{org_id}/events` — list events (offset/count; client also auto‑paginates). citeturn1search3
- **GET** `/events/{event_id}/results` — event result + optional `records` list; mapped to `EventResult`. citeturn1search3
- **GET** `/events/{event_id}/sessions` — nested groups/sessions; client flattens to a list. citeturn1search3
- **GET** `/sessions/{session_id}/announcements` — rows with announcement text; client normalizes. citeturn1search3
- **GET** `/organizations/{org_id}/records` — organization’s track/class records; mapped to `TrackRecord`. citeturn1search3

> The existence of the Event Results API and version **v0.2.3** is publicly listed in Swagger for Speedhive Event Results. citeturn4search15

---

## How to call endpoints via the Python API

Below are concrete calls using your `SpeedHiveClient` to reach each endpoint and consume the payloads.

### Get an organization

```python
from speedhive_tools.client import SpeedHiveClient
client = SpeedHiveClient()
org = client.get_organization(30476)  # Waterford Hills
print(org.name, org.city, org.country)
```

*What it does:* calls **GET** `/organizations/30476` and maps the response to `Organization`. citeturn1search3

---

### List events for an organization

```python
events = client.list_organization_events(30476, auto_paginate=True)
for ev in events:
    print(ev.event_name, ev.startDate)
```

*What it does:* calls **GET** `/organizations/{org_id}/events` with offset/count pagination (auto‑iterating until empty), then maps items to `EventResult`. citeturn1search3

---

### Get event results

```python
ev = client.get_event_results(1234)
print(ev.event_name, len(ev.records))
```

*What it does:* calls **GET** `/events/{event_id}/results`, accepts both list/object shapes, merges any `records` into the result, and returns `EventResult`. citeturn1search3

---

### Get sessions for an event

```python
sessions = client.get_sessions_for_event(1234)
print([s.get("id") for s in sessions])
```

*What it does:* calls **GET** `/events/{event_id}/sessions`, walks nested `groups`/`sessions`, and returns a flat list of session dicts. citeturn1search3

---

### Get announcements for a session

```python
rows = client.get_session_announcements(9001)
texts = [client.get_announcement_text(r) for r in rows]
print(texts[:3])
```

*What it does:* calls **GET** `/sessions/{session_id}/announcements`, injects `sessionId`, and normalizes the text from multiple possible keys. citeturn1search3

---

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

*What it does:* sequentially calls the endpoints in the previous sections, enriches each row with event/session metadata, and runs your parsing & validation logic. citeturn1search3

> The example script `examples/get_records_example.py` demonstrates the same single‑pass workflow and logs malformed entries and raw record lines. citeturn1search1turn1search3

---

### Get records by organization

```python
normalized = client.get_track_records_by_org(30476)
for tr in normalized:
    print(tr.driver_name, tr.lap_time, tr.class_name)
```

*What it does:* calls **GET** `/organizations/{org_id}/records`, accepts list/object shapes (`records` or `items`), and normalizes each row to `TrackRecord`. citeturn1search3

---

### Export JSON/CSV

```python
client.export_records_to_json(normalized, "records_snake.json")
client.export_records_to_json_camel(normalized, "records_camel.json")
client.export_records_to_csv(normalized, "records.csv")
```

*What it does:* converts `TrackRecord` models to either snake‑case JSON, camelCase JSON (with `sessionId` when present), or CSV. citeturn1search3

---

## Headers, retries, and errors

Your client sends:

```
Accept: application/json
User-Agent: speedhive-tools (+https://github.com/ncrosty58/speedhive-tools)
Apikey: <your_api_key>  # only if provided
```

It uses a pooled `requests.Session` with robust retry/backoff for idempotent methods (HTTP 429/5xx). JSON parse errors, HTTP ≥ 400, and network exceptions raise `SpeedHiveAPIError(message, status, url)`. citeturn1search3

---

## Notes

- The Event Results API and version **v0.2.3** are publicly discoverable in Swagger; this README sticks to those endpoints. citeturn4search15
- Practice‑related APIs have their own base (Swagger UI is publicly visible) but are **not used** by this client. citeturn4search6
- Response shapes vary (list vs object with `items`/`events`/`rows`); the client already handles those variants. citeturn1search3

---

## License

MIT (see `LICENSE`).
