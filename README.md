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
source .venv/bin/activate
pip install -r requirements.txt
```

Examples

1) List events by organization id (verbose)

```bash
python examples/list_events_by_org.py 30476 --verbose
```

2) List events by organization name (partial match)

```bash
python examples/list_events_by_org.py "Waterford Hills" --partial --verbose
```

3) Export announcements for an org (combined per-event JSON, verbose)

```bash
python examples/export_announcements_by_org.py 30476 --output ./announcements --verbose
```

3b) Export announcements using more concurrency (faster, but use with care)

```bash
python examples/export_announcements_by_org.py 30476 --output ./announcements --concurrency 40 --verbose
```

4) Exporter with authentication token

```bash
python examples/export_announcements_by_org.py 30476 --token YOUR_TOKEN --output ./announcements
```

5) Compress results after running exporter

```bash
# speedhive-tools

Utilities and examples for interacting with the MyLaps / Event Results API using a locally-generated OpenAPI Python client.

This repository contains a generated client under `mylaps_client/` and several small example scripts that demonstrate common tasks like listing events, exporting session announcements, and fetching session/lap data. The examples are designed to be runnable from the repository root without installing the generated client.

Quick start

Requirements
- Python 3.10+

Create & activate a virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Overview of examples

- `examples/list_events_by_org.py` — list events for an organization (by id or name).
- `examples/export_announcements_by_org.py` — async exporter that writes one combined JSON file per event containing only sessions that have announcements. Supports `--concurrency` to tune parallelism.
- `examples/get_event_sessions.py` — fetch all session objects for a given `event_id` (handles both top-level `sessions` lists and grouped `groups` -> `sessions`).
- `examples/get_session_laps.py` — fetch lap rows for a session (`session_id`) and write a JSON file (defaults to `session_laps.json`).

Running the examples

Note: run these from the repository root so `mylaps_client/` is on `sys.path`.

1) List events by organization id (verbose):

```bash
python examples/list_events_by_org.py 30476 --verbose
```

2) List events by organization name (partial match):

```bash
python examples/list_events_by_org.py "Waterford Hills" --partial --verbose
```

3) Export announcements for an org (combined per-event JSON):

```bash
python examples/export_announcements_by_org.py 30476 --output ./announcements --verbose
```

4) Export with an authentication token (if required by your account):

```bash
python examples/export_announcements_by_org.py 30476 --token YOUR_TOKEN --output ./announcements
```

5) Export using higher concurrency (faster; monitor API rate limits):

```bash
python examples/export_announcements_by_org.py 30476 --output ./announcements --concurrency 40 --verbose
```

6) Fetch all sessions for a specific event and print JSON summary:

```bash
python examples/get_event_sessions.py 123456 --verbose
```

7) Fetch lap rows for a session and write to `session_laps.json`:

```bash
python examples/get_session_laps.py 789012 --output session_789012_laps.json --verbose
```

8) Fetch session classification/results and write a JSON summary:

```bash
python examples/get_session_results.py 9751807 --output session_9751807_results.json --verbose
```

Exporter details

- Script: `examples/export_announcements_by_org.py`
- Behavior: fetches events for an organization, fetches sessions for each event (the examples handle `sessions` + `groups` shapes and `sessions: null` cases), then fetches announcements per session concurrently. Writes one JSON per event that contains at least one session with announcements.
- Output filename pattern: `event_<event_id>_announcements.json` in the specified output directory.
- Concurrency: implemented with `asyncio` and a semaphore. Default is 20, but you can override at runtime with `--concurrency N`.

CLI flags (examples)

- `--token` — pass an API token to use an authenticated client.
- `--verbose` — print debug info including HTTP status codes and response sizes.
- `--concurrency N` — set the maximum concurrent requests (positive integer). Use with caution to avoid API throttling.

Output format (per-event)

Each event output is a JSON object with `id`, `name`, and a `sessions` array. Each session entry contains `id`, `name`, and an `announcements` field which is either a dict with `rows` or a list depending on the API payload.

Example event file (truncated)

```json
{
  "id": 3245417,
  "name": "2025 Waterford Hills WHRRI Race #6",
  "sessions": [
    {
      "id": 4538623,
      "name": "Race 1",
      "announcements": { "rows": [ /* ... */ ] }
    }
  ]
}
```

Notes on payload shapes and robustness

- The API sometimes returns `sessions: null` or nests sessions inside `groups`. The examples sanitize these shapes before attempting to parse into generated models.
- Announcement responses vary between a dict (`{"rows": [...]}`) and a raw list. The exporter attempts to normalize using the generated `RunAnnouncements` model where appropriate and falls back to raw JSON when necessary.

Troubleshooting

- If no events are returned for a known org id: run `python examples/list_events_by_org.py ORG_ID --verbose` to inspect raw responses.
- If parsing fails: re-run with `--verbose` to capture response sizes and raw payloads; share the raw payload if you'd like me to add sanitizer logic.
- If you receive HTTP 429 or rate-limit errors: lower `--concurrency` and add backoff/retries in code.

Regenerating the client

If the OpenAPI spec changes, regenerate the client and drop the `mylaps_client/` package into the repo root. Example using `openapi-python-client`:

```bash
python -m openapi_python_client generate --url https://api2.mylaps.com/v3/api-docs --output-path ./mylaps_client
```

After regenerating, run the examples to validate and adjust sanitization where payload shapes differ.

Testing

- There is a minimal test under `tests/test_examples_imports.py` that verifies example files contain a `main` function. Run it with:

```bash
pytest -q tests/test_examples_imports.py
```

If you want tests that exercise network calls, I recommend recording fixtures (responses) and mocking the generated client's controllers so CI can run deterministically.

Suggested commit message

```
docs: replace duplicated README with clean examples-first README

- document new examples: get_event_sessions, get_session_laps
- document exporter `--concurrency` flag and usage
- include quick-start, troubleshooting, and test notes
```

If you'd like, I can also:

- Add CI (GitHub Actions) to run the minimal tests and linting.
- Add recommended default concurrency values and a short note about safe ranges.
- Add example output samples captured from a recent run (sanitized).

Questions? Which follow-up would you like me to do next?

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

Suggested git commit message for README update

```
docs: expand README with many practical examples and troubleshooting
```


