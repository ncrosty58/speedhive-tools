# speedhive-tools

Utilities and examples for interacting with the MyLaps / Event Results API using a locally-generated OpenAPI Python client.

This repo keeps a generated client under `mylaps_client/` and includes several small utilities and examples that show how to list events and export session announcements for an organization.

Quick links

- `mylaps_client/` — the generated OpenAPI client package (importable as `event_results_client` when running examples from the repo root).
- `examples/list_events_by_org.py` — list events for an organization (by name or numeric id).
- `examples/export_announcements_by_org.py` — async exporter that writes one combined JSON file per event containing only sessions that have announcements.
- `mylaps_client_wrapper.py` — tiny helper that constructs `Client` / `AuthenticatedClient`.
- `requirements.txt` — dependencies used by the generated client and examples.

Why this repo

The Event Results API returns useful data but the payload shapes can vary between endpoints and API versions. We generated a typed Python client from the OpenAPI spec and added small example scripts that handle real-world quirks (null nested fields, grouped sessions, multiple endpoint versions). The exporter is async and concurrent so it runs reasonably fast for orgs with many events/sessions.

Requirements

- Python 3.10 or newer
- Install dependencies from `requirements.txt` (use a virtualenv)

Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Running examples

Note: examples assume you run them from the repository root so the local `mylaps_client` directory is on `sys.path`.

1) List events by organization id

```bash
python examples/list_events_by_org.py 30476 --verbose
```

2) List events by organization name (partial match)

```bash
python examples/list_events_by_org.py "Waterford Hills" --partial --verbose
```

3) Export announcements for an org (combined per-event JSON)

```bash
python examples/export_announcements_by_org.py 30476 --output ./announcements --verbose
```

4) Run exporter with authentication token (if needed)

```bash
python examples/export_announcements_by_org.py 30476 --token YOUR_TOKEN --output ./announcements
```

5) Example: run exporter and compress outputs (shell)

```bash
python examples/export_announcements_by_org.py 30476 --output ./announcements
tar -czf announcements_30476.tar.gz -C announcements .
```

6) Example: run exporter then combine all event files into a single file

```bash
python examples/export_announcements_by_org.py 30476 --output ./announcements
python - <<'PY'
import json, glob
all_events = []
for path in sorted(glob.glob('announcements/event_*_announcements.json')):
    all_events.append(json.load(open(path)))
json.dump({'org_id':30476, 'events': all_events}, open('announcements_all_30476.json','w'), indent=2)
PY
```

Detailed examples and CLI options

`examples/list_events_by_org.py` (high level)

- Usage:
  - `python examples/list_events_by_org.py ORG_ID_OR_NAME [--partial] [--token TOKEN] [--verbose]`
- Behavior:
  - Accepts either a numeric org id or a name string.
  - If a name is provided, it performs normalized, case-insensitive matching; `--partial` enables substring matching.
  - Prints `id: name` lines and basic debug info when `--verbose`.

`examples/export_announcements_by_org.py` (high level)

- Usage:
  - `python examples/export_announcements_by_org.py ORG_ID --output OUTDIR [--token TOKEN] [--verbose]`
- Behavior:
  - Fetches events for the organization, fetches sessions for each event, and fetches announcements for each session concurrently.
  - Writes one file per event that contains at least one session with announcements. Files are named `event_<event_id>_announcements.json`.
  - Each event file contains `{ "id": <event_id>, "name": "<event name>", "sessions": [ ... ] }` where `sessions` includes only sessions that had announcements.

CLI flags

- `--token` — pass an API token to use an authenticated client.
- `--verbose` — print debug info including HTTP status codes and response sizes.

Concurrency tuning

- The exporter uses `asyncio` and a semaphore to limit concurrency (default is 20). If you expect heavy load or want to go faster, consider increasing the concurrency value in the code, or ask to expose a `--concurrency` CLI flag.

Sample output (event file)

```json
{
  "id": 3245417,
  "name": "2025 Waterford Hills WHRRI Race #6",
  "sessions": [
    {
      "id": 4538623,
      "name": "Race 1",
      "announcements": { "rows": [ ... ] }
    },
    {
      "id": 4538624,
      "name": "Race 2",
      "announcements": [ { ... }, { ... } ]
    }
  ]
}
```

Notes about payload shapes

- The API sometimes returns `sessions: null` or nests sessions under `groups` — the examples include handling for those cases.
- Announcement payloads vary: sometimes a dict with `rows`, sometimes a list. The exporter tries to normalize using `RunAnnouncements` model when `rows` is present, otherwise it writes the raw JSON.

Troubleshooting tips

- If you get no events for a known org id:
  - Run `python examples/list_events_by_org.py ORG_ID --verbose` to show raw response sizes.
  - Confirm the org id is correct and that you are hitting the right API base URL (`https://api2.mylaps.com`).
- If parsing fails with TypeError from generated models:
  - The examples sanitize `null` fields (e.g. `sessions`) before calling `from_dict`. If you encounter a new shape, capture the raw response (use `--verbose`) and report it so the sanitizer can be adapted.
- If you need to restrict the date range or filter events:
  - The generated client exposes underlying endpoints; modify examples to filter `events` by `startDate`/`endDate` or other parameters.

Regenerating the client

If the OpenAPI spec changes you can regenerate the client and drop it into `mylaps_client/`.

High-level steps (example using `openapi-python-client`):

```bash
python -m openapi_python_client generate --url https://api2.mylaps.com/v3/api-docs --output-path ./mylaps_client
```

After regenerating, run the examples to validate and adjust any sanitization logic if payload shapes changed.

Testing and CI

- There is a minimal import test under `tests/` to ensure the generated package imports correctly. Add unit tests or mocks if you want to run the exporter in CI.

Contributing and next steps

If you'd like I can implement any of the following (pick one or more):

- Add a `--concurrency` CLI flag to control parallelism.
- Add an `--aggregate` flag to emit a single combined file for all events instead of per-event files.
- Add a unit test that verifies exporter output using recorded fixtures (recommended for CI).

Suggested git commit message for README update

```
docs: expand README with many practical examples and troubleshooting
```

If you'd like changes to the wording, additional examples (for example, filtering events by date or exporting CSV summaries), or a `--concurrency` CLI flag added to the exporter code, tell me which item to add first and I'll implement it.
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
