# speedhive-tools

A Python client, SQLite persistence layer, and CLI for scraping and analyzing
[MyLaps Speedhive](https://speedhive.com) race results. It powers the
[speedhive-tools-ui](https://github.com/ncrosty58/speedhive-tools-ui) dashboard,
but works standalone as a library or command-line tool.

Install:

```bash
pip install speedhive-tools
```

or, for local development:

```bash
git clone https://github.com/ncrosty58/speedhive-tools.git
cd speedhive-tools
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

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
├── generated/                   # Auto-generated OpenAPI models/endpoints
├── utils/                       # Lap-time parsing, outlier detection, text parsing
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

## Programmatic usage

### Scrape live from the API

```python
from speedhive.wrapper import SpeedhiveClient

client = SpeedhiveClient.create()
org = client.get_organization(30476)
events = client.iter_events(30476)          # generator over all events
sessions = client.get_sessions(event_id=12345)
laps = client.get_laps(session_id=67890)
```

### Sync an org into a local SQLite cache

`SpeedhiveStorage` is constructed once and threaded through every call that
touches it:

```python
from speedhive.storage import SpeedhiveStorage
from speedhive.wrapper import SpeedhiveClient
from speedhive.workflows.refresh_org_cache import refresh_org_cache

client = SpeedhiveClient.create()
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
LLM instead — `speedhive.llm.gemini` has the Gemini client (config via
`GEMINI_API_KEY`/`GEMINI_MODEL` env vars) and `speedhive.llm.track_records`
has the provider-agnostic prompt/schema/parsing logic. `run_sync_and_diff`/
`storage.get_track_records` also accept a `parse_cache` (announcement identity
-> cached result) plus an `on_parsed` callback, so repeat scans only pay for
genuinely new announcements instead of re-parsing an org's entire history
every time:

```python
from speedhive.llm import parse_track_records_bulk_with_gemini

scan = curation.run_sync_and_diff(
    30476, storage, "./web_data/track_records",
    bulk_parser=parse_track_records_bulk_with_gemini,
)
```

### Offline dumps

Export a synced org to portable NDJSON, or load one back into a fresh cache:

```python
from speedhive.exporters.export_db_dump import export_db_dump
from speedhive.workflows.import_sqlite_dump import import_dump_to_storage

export_db_dump(storage, org_id=30476, output_dir="./snapshots/30476")
import_dump_to_storage(org=30476, dump_dir="./snapshots", storage=storage)
```

---

## Command-line interface

Installing the package registers a `speedhive` executable.

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

All commands accept `--db-path` (defaults to `$SPEEDHIVE_DB_PATH` or
`./web_data/speedhive.db`). Run `speedhive <command> --help` for full options.

```bash
speedhive sync-org --org 30476 --mode incremental --recent-backfill-events 5
speedhive report-consistency --org 30476 --min-laps 15 --top 20 --ignore-outliers
speedhive refresh-track-records --org 30476
```

---

## Configuration

| Variable | Purpose |
| :--- | :--- |
| `SPEEDHIVE_DB_PATH` | Default SQLite cache path used by CLI commands |
| `TRACK_RECORDS_STALE_HOURS` | How old the cache can be before `get_cache_status` reports `needs_sync` (default `20`) |
| `GOTIFY_URL`, `GOTIFY_APP_TOKEN` | Optional push notification when new track-record candidates are found |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Gemini credentials for `speedhive.llm`'s LLM-based track-record parser (default model `gemini-2.5-flash`) |

---

## Testing

```bash
pip install -e ".[dev]"
pytest
```
