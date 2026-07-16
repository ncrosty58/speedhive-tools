# speedhive-tools

[![PyPI](https://img.shields.io/pypi/v/speedhive-tools)](https://pypi.org/project/speedhive-tools/)
[![Python](https://img.shields.io/pypi/pyversions/speedhive-tools)](https://pypi.org/project/speedhive-tools/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Python client, SQLite persistence layer, and CLI for scraping and analyzing
[MyLaps Speedhive](https://speedhive.com) race results. It powers the
[speedhive-tools-ui](https://github.com/ncrosty58/speedhive-tools-ui) dashboard,
but works standalone as a library or command-line tool — no dashboard or
web framework required.

## Features

- **HTTP client** for the Speedhive API — organizations, events, sessions,
  results, laps, lap charts, announcements, championships.
- **SQLite cache** (`SpeedhiveStorage`) — sync once, query fast and offline;
  incremental or full re-sync per organization.
- **CLI** (`speedhive ...`) for syncing, exporting, and analyzing without
  writing any code.
- **Track-record curation workflow** — extracts announcer-flagged track/class
  records from session announcements, diffs against a human-curated list, and
  queues only new/changed candidates for review.
- **Optional LLM-based parsing** (Gemini) for the track-record workflow, for
  announcer phrasings a regex can't catch — regex remains the zero-dependency
  default.
- **Offline NDJSON dumps** — export a synced org to portable files and
  reload them into a fresh cache elsewhere, no API access required.

## Installation

```bash
pip install speedhive-tools
```

For local development:

```bash
git clone https://github.com/ncrosty58/speedhive-tools.git
cd speedhive-tools
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Quickstart

The fastest path from nothing to queryable data — sync one organization into
a local SQLite cache, then read from it:

```python
from speedhive.wrapper import SpeedhiveClient
from speedhive.storage import SpeedhiveStorage
from speedhive.workflows.refresh_org_cache import refresh_org_cache

client = SpeedhiveClient.create()
storage = SpeedhiveStorage("speedhive.db")

refresh_org_cache(client=client, storage=storage, org_id=30476, mode="full")

records = storage.get_track_records(30476)
print(f"{len(records)} track records found")
```

Or the CLI equivalent, no code required:

```bash
speedhive sync-org --org 30476 --mode full --db-path speedhive.db
speedhive export-track-records --org 30476 --db-path speedhive.db
```

The rest of this README is two parallel guides — pick whichever matches how
you want to use this project:

- **[CLI Guide](#cli-guide)** — you just want to run commands, no Python.
- **[Python API Guide](#python-api-guide)** — you're writing code against
  `SpeedhiveClient`/`SpeedhiveStorage` directly.

Both sit on the same architecture, described next.

---

## How it fits together

```
SpeedhiveClient  --scrapes-->  SpeedhiveStorage (SQLite)  --queries-->  reports / exports
     |                                |
     +------ workflows/ orchestrate both -----+
```

- **`SpeedhiveClient`** (`speedhive.wrapper`) talks to the Speedhive HTTP API.
- **`SpeedhiveStorage`** (`speedhive.storage`) is the single SQLite persistence
  and query layer — every event, session, result, lap, and announcement gets
  cached here, and every read (including derived data like parsed track
  records) goes through it.
- **Workflows** (`speedhive.workflows`) orchestrate the two: `refresh_org_cache`
  pulls from the client and writes to storage; the `track_records` workflow
  reads from storage, diffs against a curated file store, and writes candidate
  records for human review.
- **Exporters / analyzers** are thin, mostly-CLI-facing layers that read from
  an already-populated `SpeedhiveStorage` and produce NDJSON, reports, or
  driver-lap extracts.

A `SpeedhiveStorage` instance is cheap to construct but not free — its
constructor opens a connection and runs schema DDL. Library functions that
need one take it as a parameter rather than a raw path, so callers doing
multi-step work (sync, then scan, then export) build it once and pass it
through instead of reopening it at every step.

```
src/speedhive/
├── client.py                    # Low-level HTTP client
├── wrapper.py                   # SpeedhiveClient — high-level API wrapper
├── storage.py                   # SpeedhiveStorage — SQLite cache + queries
├── ndjson.py                    # Streaming NDJSON helpers
├── llm.py                       # Optional Gemini client for LLM-based track-record parsing (env-var config)
├── generated/                   # Auto-generated OpenAPI models/endpoints
├── utils/                       # Lap-time parsing, outlier detection, regex + LLM text parsing
│   ├── lap_analysis.py          # parse_track_record_text (regex) + lap-time/outlier helpers
│   └── llm_track_records.py     # parse_track_record_text_llm — provider-agnostic LLM alternative
├── analyzers/                   # analyze_consistency, analyze_driver_laps (CLI)
├── exporters/                   # export_db_dump, export_lap_records, export_track_records, ...
├── workflows/
│   ├── refresh_org_cache.py     # Sync one org from the API into storage
│   ├── import_sqlite_dump.py    # Load an offline NDJSON dump into storage
│   └── track_records/
│       ├── extract.py           # extract_records_from_api — API-side scraping (no storage)
│       └── curation.py          # sync/diff orchestration against a curated NDJSON store
├── stores/                      # File-backed stores (curated/rejected/pending track records)
└── cli/main.py                  # `speedhive` command-line entry point
```

---

## CLI Guide

Installing the package registers a `speedhive` executable. Every command
accepts `--db-path` (defaults to `$SPEEDHIVE_DB_PATH` or
`./web_data/speedhive.db`) — run `speedhive <command> --help` for full options
on any of them.

### 1. Sync an organization

```bash
speedhive sync-org --org 30476 --mode full --db-path speedhive.db
```

Once synced, `--mode incremental` only re-checks new/updated events (plus a
handful of recent ones, via `--recent-backfill-events`) instead of
re-scraping everything:

```bash
speedhive sync-org --org 30476 --mode incremental --recent-backfill-events 5
```

### 2. Explore what's cached

```bash
speedhive report-consistency --org 30476 --min-laps 15 --top 20 --ignore-outliers
speedhive extract-driver-laps --org 30476 --driver "Jane Doe"
```

### 3. Export to NDJSON

```bash
speedhive export-lap-records --org 30476 --db-path speedhive.db
speedhive export-track-records --org 30476 --classification GT3
```

### 4. Track-record curation

```bash
# Refresh the cache if stale, then diff announcer-flagged records against
# the curated list -- writes new candidates for review, nothing automatic
speedhive refresh-track-records --org 30476

# Or just diff an already-synced cache, no API calls:
speedhive scan-track-records --org 30476

# Export/import the human-approved list
speedhive export-curated-track-records --org 30476
speedhive import-curated-track-records --org 30476 --input curated.ndjson
```

### 5. Portable offline dumps

Move a synced org between machines without re-hitting the API:

```bash
speedhive export-db-dump --org 30476 --output-dir ./snapshots/30476
speedhive import-dump --org 30476 --dump-dir ./snapshots
```

### Full command reference

| Command | Purpose |
| :--- | :--- |
| `sync-org --org ID [--mode full\|incremental]` | Scrape an org from the API into the SQLite cache |
| `report-consistency --org ID [--driver NAME]` | Rank drivers by lap-time consistency (CV), optionally look up one driver's percentile |
| `extract-driver-laps --org ID --driver NAME` | Fuzzy-match a driver and dump their race laps + stats to JSON |
| `export-track-records --org ID [--classification C]` | Export parsed track/class records from the cache to NDJSON |
| `export-lap-records --org ID` | Export raw lap rows per session to NDJSON |
| `export-db-dump --org ID --output-dir DIR` | Export a full offline NDJSON dump of an org |
| `import-dump --org ID --dump-dir DIR` | Load an offline NDJSON dump into the SQLite cache |
| `export-dump --org ID --output DIR` | Full raw dump export (events/sessions/results/laps/announcements) |
| `scan-track-records --org ID` | Diff the curated track-record store against an already-synced cache |
| `refresh-track-records --org ID [--force]` | Refresh the cache if stale, then scan for track-record candidates |
| `export-curated-track-records --org ID` | Export the human-approved curated record list to NDJSON |
| `import-curated-track-records --org ID --input FILE` | Merge or replace the curated record list from NDJSON |

---

## Python API Guide

This is for writing code directly against the library's classes — no CLI
involved. Each step builds on the last.

### Talk to the API directly

For quick, uncached, one-off lookups, `SpeedhiveClient` is enough on its own:

```python
from speedhive.wrapper import SpeedhiveClient

client = SpeedhiveClient.create()
org = client.get_organization(30476)
events = client.iter_events(30476)          # generator over all events
sessions = client.get_sessions(event_id=12345)
laps = client.get_laps(session_id=67890)
```

See `examples/` in this repo for more of these (announcements, championships,
lap charts, streaming laps to a file, etc.) — small, runnable, dependency-free
scripts that use only `SpeedhiveClient`, no SQLite involved.

### Sync into a local cache

For anything beyond a one-off lookup, sync into `SpeedhiveStorage` instead of
re-hitting the API every time. Construct it once and thread it through every
call that touches it:

```python
from speedhive.storage import SpeedhiveStorage
from speedhive.workflows.refresh_org_cache import refresh_org_cache

storage = SpeedhiveStorage("speedhive.db")

refresh_org_cache(
    client=client,
    storage=storage,
    org_id=30476,
    mode="incremental",          # or "full" to re-scrape everything
    recent_backfill_events=3,    # also re-check the N most recent events
)
```

### Query the cache

Reads — including derived queries like parsed track records — are methods on
`SpeedhiveStorage` itself:

```python
org = storage.get_organization(30476).payload
laps = storage.get_laps(session_id=67890).payload
status = storage.get_org_status(30476)                 # freshness/staleness info
records = storage.get_track_records(30476, classification="Karting")
```

### Track-record curation workflow

Speedhive announcers flag new track/class records in session announcements.
The `track_records` workflow extracts those, normalizes classification codes
against a per-org alias map, diffs them against a curated NDJSON file, and
writes only new/changed candidates out for human review — nothing is written
to the curated file automatically.

```python
from speedhive.workflows.track_records import curation

# Refresh storage if the cache looks stale, then scan for new record candidates
outcome = curation.refresh_and_scan(
    org_id=30476,
    client=client,
    storage=storage,
    track_records_root="./web_data/track_records",
)

# Or just diff against an already-synced cache, no API calls:
scan = curation.run_sync_and_diff(30476, storage, "./web_data/track_records")
```

By default, extraction uses the regex-based `parse_track_record_text`, which
only catches one exact announcer phrasing. Pass a `bulk_parser` (one call
covering every announcement text for the org, aligned by position) to use an
LLM instead:

```python
from speedhive.llm import parse_track_records_bulk_with_gemini

scan = curation.run_sync_and_diff(
    30476, storage, "./web_data/track_records",
    bulk_parser=parse_track_records_bulk_with_gemini,
)
```

`speedhive.llm` is the actual Gemini client (config via
`GEMINI_API_KEY`/`GEMINI_MODEL` env vars — see Configuration below);
`speedhive.utils.llm_track_records` is the provider-agnostic prompt/schema/
parsing logic underneath it, which takes an injected `call_llm_fn` so it has
no dependency on Gemini specifically if you want to plug in a different model.

`run_sync_and_diff`/`storage.get_track_records` also accept a `parse_cache`
(announcement identity -> cached result) plus an `on_parsed` callback, so
repeat scans only pay for genuinely new announcements instead of re-parsing
an org's entire history every time — see `tests/test_llm.py` for a worked
example of wiring the cache up yourself.

### Offline dumps

Export a synced org to portable NDJSON, or load one back into a fresh cache:

```python
from speedhive.exporters.export_db_dump import export_db_dump
from speedhive.workflows.import_sqlite_dump import import_dump_to_storage

export_db_dump(storage, org_id=30476, output_dir="./snapshots/30476")
import_dump_to_storage(org=30476, dump_dir="./snapshots", storage=storage)
```

---

## Examples

`examples/` has small, standalone scripts against `SpeedhiveClient` only (no
storage, no caching) — good starting points for exploring a single endpoint:

```bash
python examples/example_get_organization.py --org 30476
python examples/example_get_session_announcements.py --session 67890
python examples/example_stream_announcements.py --org 30476 --output-file announcements.ndjson
python examples/example_track_records.py --org 30476 --output-file records.ndjson
```

Run any of them with `--help` to see its full argument list.

---

## Configuration

| Variable | Purpose |
| :--- | :--- |
| `SPEEDHIVE_DB_PATH` | Default SQLite cache path used by CLI commands |
| `TRACK_RECORDS_STALE_HOURS` | How old the cache can be before `get_cache_status` reports `needs_sync` (default `20`) |
| `GOTIFY_URL`, `GOTIFY_APP_TOKEN` | Optional push notification when new track-record candidates are found |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Gemini credentials for `speedhive.llm`'s LLM-based track-record parser (default model `gemini-2.5-flash`) |

---

## Development

```bash
pip install -e ".[dev]"
pytest              # test suite
ruff check src/     # lint
```

Releases are tag-triggered (`git tag vX.Y.Z && git push origin vX.Y.Z`) — CI
runs the test suite, builds the package, publishes to PyPI, and creates the
GitHub release automatically. Bump `version` in `pyproject.toml` first.

## License

[MIT](LICENSE) © Nathan Crosty
