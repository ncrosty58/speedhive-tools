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

Regenerating the client

If the OpenAPI spec changes you can regenerate the client and drop it into `mylaps_client/`.

<!-- Lightweight README for speedhive-tools -->
# speedhive-tools

Small utilities to interact with the MyLaps Event Results API using a locally-generated OpenAPI client.

**Quick Start**
- Requirements: Python 3.10+ and a virtualenv.
- Install:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**What’s in this repo**
- `mylaps_client/` — generated OpenAPI Python client (importable as `event_results_client` when running examples from the repo root).
- `examples/` — short, runnable examples that demonstrate common API tasks.
- `examples/processing/` — small data-processing helpers (convert NDJSON -> CSV/SQLite).
- `output/` — suggested place for example outputs (this directory is in `.gitignore`).

**Common commands**
- List events for an org:
  ```bash
  python examples/list_events_by_org.py 30476 --verbose
  ```
- Export announcements for an org (per-event JSON files):
  ```bash
  python examples/export_announcements_by_org.py 30476 --output ./output/announcements --verbose
  ```
- Full dump (stream NDJSON, gzipped by default):
  ```bash
  python examples/export_full_dump.py --org 30476 --output ./output/full_dump --verbose
  ```

**Process exported data**
- Extract laps to CSV:
  ```bash
  python examples/processing/extract_laps_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/laps_flat.csv
  ```
- Import laps to SQLite:
  ```bash
  python examples/processing/ndjson_to_sqlite.py --input output/full_dump/30476/laps.ndjson.gz --out output/full_dump/30476/dump.db
  sqlite3 output/full_dump/30476/dump.db "SELECT COUNT(*) FROM laps;"
  ```

**Notes & tips**
- Run examples from the repository root so the local `mylaps_client` package is on `sys.path`.
- Use `--token` on example CLIs when endpoints require authentication.
- The exporter supports `--max-events`, `--max-sessions-per-event`, and `--dry-run` for low-memory testing.
- Long runs write a checkpoint file (`outdir/.checkpoint.json`) so you can resume after interruptions.

**Regenerating the client**
If the API OpenAPI spec changes, regenerate the client and place it under `mylaps_client/`.

Example using `openapi-python-client`:
```bash
python -m openapi_python_client generate --url https://api2.mylaps.com/v3/api-docs --output-path ./mylaps_client
```

**Need help or next steps?**
- I can add CI tests with recorded fixtures, retries and backoff for the exporter, or more processing utilities (aggregation, progress summaries). Tell me which and I’ll implement it.

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




