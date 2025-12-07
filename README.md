# speedhive-tools

Utilities and examples for interacting with the MyLaps / Event Results API using a locally-generated OpenAPI Python client.

This repository contains a generated client under `mylaps_client/` and example scripts that demonstrate how to list events and export session announcements for an organization.

Table of contents

- Quick start
- Examples
- Exporter details
- Troubleshooting
- Regenerating the client
- Contributing

Quick start

Requirements
- Python 3.10+
- `pip install -r requirements.txt`

Create and activate a virtualenv, then install:

```bash
python -m venv .venv
# speedhive-tools

Small, practical tools for the MyLaps / Event Results API using a locally-generated OpenAPI Python client.

Quick overview
- Generated client: `mylaps_client/` (importable as `event_results_client` when running examples from the repo root).
- Examples live in `examples/` and are runnable without installing the client.
# 🚀 speedhive-tools

Small, playful utilities for the MyLaps Event Results API — examples included ✨

Why this repo
---------------------------------
- A locally-generated OpenAPI client lives in `mylaps_client/`.
- Example scripts show common tasks (list events, export announcements, fetch laps/results).

Quick start — get running ⚡
---------------------------------
Requirements: Python 3.10+

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Client usage (one-line) 🧩
---------------------------------
Import and construct a client:

```python
from event_results_client import AuthenticatedClient
client = AuthenticatedClient(base_url="https://api2.mylaps.com", token="YOUR_TOKEN")
```

Quick examples (run from repo root) 🧰
---------------------------------
- List events by org id:

```bash
python examples/list_events_by_org.py 30476
```

- Export announcements (writes to `output/announcements` by default):

```bash
python examples/export_announcements_by_org.py 30476 --output ./output/announcements --verbose
```

- Get session results (summary + raw):

```bash
python examples/get_session_results.py 9751807 --verbose
```

Extra examples ✨
---------------------------------
- List events by name (partial match):

```bash
python examples/list_events_by_org.py "Waterford Hills" --partial --verbose
```

- Export with more concurrency (be nice to the API):

```bash
python examples/export_announcements_by_org.py 30476 --concurrency 40 --verbose
```

- Print sessions for an event (or write with `--output`):

```bash
python examples/get_event_sessions.py 123456 --verbose
```

Notes & tips 📝
---------------------------------
- Example outputs default to `output/` (this folder is in `.gitignore`).
- Use `--token` when endpoints require authentication.
- Lower `--concurrency` if you see rate limits.

Testing 🧪
---------------------------------
- Minimal checks are in `tests/`:

```bash
pytest -q tests/test_examples_imports.py
```

Want more?
---------------------------------
- I can add CI, recorded fixtures for offline tests, or a polished `README_CLIENT.md` with client patterns — say the word and I'll do it! 🎯

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
  - `python examples/export_announcements_by_org.py ORG_ID --output OUTDIR [--token TOKEN] [--verbose] [--concurrency N]`
- Behavior:
  - Fetches events for the organization, fetches sessions for each event, and fetches announcements for each session concurrently.
  - Writes one file per event that contains at least one session with announcements. Files are named `event_<event_id>_announcements.json`.
  - Each event file contains `{ "id": <event_id>, "name": "<event name>", "sessions": [ ... ] }` where `sessions` includes only sessions that had announcements.

CLI flags

- `--token` — pass an API token to use an authenticated client.
- `--verbose` — print debug info including HTTP status codes and response sizes.
- `--concurrency N` — set the maximum concurrent requests (positive integer). Overrides the default semaphore value (20).

Concurrency tuning

- The exporter uses `asyncio` and a semaphore to limit concurrency (default is 20). You can change this at runtime with `--concurrency N` to increase or decrease the number of simultaneous requests. Example:

```bash
python examples/export_announcements_by_org.py 30476 --output ./announcements --concurrency 40 --verbose
```

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




