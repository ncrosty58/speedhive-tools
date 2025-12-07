# speedhive-tools

Tools and examples for working with the MyLaps / Event Results API using a locally-generated OpenAPI Python client.

This repository contains a generated Python client (under `mylaps_client`), a small wrapper, and example scripts that demonstrate how to list events and export session announcements for an organization.

**Contents**

- `mylaps_client/` – generated OpenAPI Python client (importable as `event_results_client` when `mylaps_client` is on `sys.path`).
- `examples/` – runnable example scripts:
  - `list_events_by_org.py` — list events for an organization (by name or numeric id).
  - `export_announcements_by_org.py` — async exporter that writes one combined JSON per event containing only sessions that have announcements.
- `mylaps_client_wrapper.py` – small helper for creating `Client`/`AuthenticatedClient` instances.
- `requirements.txt` – runtime dependencies required by the generated client and examples.

## Project Overview

The goal of these tools is to make it easy to programmatically access event/session/announcement data from the Event Results API (MyLaps). The repository keeps the generated client local so examples can run without installing a package globally.

Key features
- Generated OpenAPI client for typed API access (`event_results_client`).
- Example scripts that are resilient to API payload shape differences (e.g. `sessions` sometimes nested in `groups` or present as `null`).
- Async exporter (`export_announcements_by_org.py`) that fetches session announcements concurrently and writes one JSON-per-event with only sessions that contain announcements.

## Requirements

- Python 3.10+ (the generated client targets modern Python).
- Install dependencies listed in `requirements.txt` (recommended in a virtualenv).

# speedhive-tools

Tools and examples for working with the MyLaps / Event Results API using a locally-generated OpenAPI Python client.

This repository contains a generated Python client (under `mylaps_client`), a small wrapper, and example scripts that demonstrate how to list events and export session announcements for an organization.

**Contents**

- `mylaps_client/` – generated OpenAPI Python client (importable as `event_results_client` when `mylaps_client` is on `sys.path`).
- `examples/` – runnable example scripts:
  - `list_events_by_org.py` — list events for an organization (by name or numeric id).
  - `export_announcements_by_org.py` — async exporter that writes one combined JSON per event containing only sessions that have announcements.
- `mylaps_client_wrapper.py` – small helper for creating `Client`/`AuthenticatedClient` instances.
- `requirements.txt` – runtime dependencies required by the generated client and examples.

## Project Overview

The goal of these tools is to make it easy to programmatically access event/session/announcement data from the Event Results API (MyLaps). The repository keeps the generated client local so examples can run without installing a package globally.

Key features
- Generated OpenAPI client for typed API access (`event_results_client`).
- Example scripts that are resilient to API payload shape differences (e.g. `sessions` sometimes nested in `groups` or present as `null`).
- Async exporter (`export_announcements_by_org.py`) that fetches session announcements concurrently and writes one JSON-per-event with only sessions that contain announcements.

## Requirements

- Python 3.10+ (the generated client targets modern Python).
- Install dependencies listed in `requirements.txt` (recommended in a virtualenv).

Install (example):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Note: the generated client uses `httpx` and `attrs`.

## Running the examples

All examples assume you run them from the repository root so they can import the local `mylaps_client` directory. Example commands below:

- List events for an organization id (e.g. `30476`):

```bash
python examples/list_events_by_org.py 30476 --verbose
```

- Export announcements (async, concurrency, combined per-event):

```bash
python examples/export_announcements_by_org.py 30476 --output ./announcements --verbose
```

If you need to authenticate (some endpoints may require an API token), pass `--token` to the examples:

```bash
python examples/export_announcements_by_org.py 30476 --token YOUR_TOKEN --output ./announcements
```

Output format for the exporter
- Each event that has announcements produces a file named `event_<event_id>_announcements.json` under the output directory.
- Each event file contains a JSON object:

```json
{
  "id": 12345,
  "name": "Event Name",
  "sessions": [
    {
      "id": 111,
      "name": "Practice",
      "announcements": { ... }  // raw or normalized announcements payload
    },
    {
      "id": 222,
      "name": "Race",
      "announcements": [ ... ]
    }
  ]
}
```

- Sessions with no announcements are excluded.
- Events where no sessions have announcements are skipped (no file created).

Concurrency and performance
- The exporter uses `asyncio` plus a semaphore (default concurrency = 20) to fetch announcements concurrently. This greatly speeds up runs when an org has many sessions.
- To change concurrency you can update the `concurrency` argument in `export_announcements_for_org_async` or I can expose a `--concurrency` CLI flag if you prefer.

Troubleshooting & notes
- API payloads are sometimes inconsistent (for example: `sessions` may be `null` or sessions may be nested in `groups`). The examples include sanitization logic to handle those cases.
- If you get empty results where you expect data, try running with `--verbose` to print response sizes/status codes and a sample of the content.
- If authentication is required, supply a valid API token via `--token`.

Development & contributing
- If you regenerate the client (e.g. the OpenAPI spec changes), put the new generated package under `mylaps_client/` and verify the examples still run.
- Tests: there is a minimal import test under `tests/` — run your test runner to validate imports.

---
If you want any changes to the README wording or additional examples, tell me what to include and I'll update it.
