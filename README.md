# speedhive-tools

A Python client, SQLite persistence layer, and CLI for scraping and analyzing [MyLaps Speedhive](https://speedhive.com) racing results.

It's the core engine behind the [`speedhive-tools-ui`](https://github.com/ncrosty58/speedhive-tools-ui) dashboard (vendored there as a git submodule), but works standalone as a library or command-line tool with no web UI required.

## What it does

- **Speedhive HTTP client** (`speedhive.wrapper.SpeedhiveClient`) — a hand-written, ergonomic wrapper around an OpenAPI-generated low-level client (`speedhive/generated/`) for organizations, events, sessions, results, laps, lap charts, announcements, and championships.
- **SQLite cache** (`speedhive.storage.SpeedhiveStorage`) — local persistence for everything the client fetches, with per-entity save/read methods and org-scoped pruning.
- **Org sync workflow** (`speedhive.workflows.refresh_org_cache`) — incremental or full re-sync of an organization into the cache, with configurable event caps and recent-event backfill.
- **Per-org settings resolution** (`speedhive.settings`) — a single, reusable mechanism for "does this org have its own override for X, else fall back to a global default" (Gemini keys, parsing engine, min-laps), backed by `<SPEEDHIVE_DATA_DIR>/orgs/<org_id>/settings.json`. Shared by the CLI and any host application; has no notion of email/notification settings, since those are policy owned entirely by a host app like `speedhive-tools-ui`.
- **Track-record curation** (`speedhive.workflows.track_records`) — parses announcer text for lap-record callouts (regex by default, optional Gemini LLM extraction via `speedhive.llm`, chosen per-org through `speedhive.settings`), normalizes classification names against an alias map, and maintains candidate/curated/rejected review queues per organization. Every manual edit to a curated record appends to that record's own edit history (what changed, when) rather than overwriting it silently.
- **Analyzers** (`speedhive.analyzers`) — driver consistency rankings (mean/stdev/coefficient-of-variation, with optional IQR outlier filtering and fuzzy name clustering), per-driver lap extraction, and average-lap-by-class-and-year pace charts.
- **NDJSON exporters/importers** (`speedhive.exporters`, `speedhive.workflows.import_sqlite_dump`) — portable dump/restore of an org's cache, lap records, track records, and curated records as newline-delimited JSON, individually or as a full ZIP-able dump.
- **Unified CLI** (`speedhive`) — one entry point for all of the above; new exporter/workflow/analyzer modules that expose a `main(argv)` are auto-registered as subcommands (`speedhive.cli.discovery`).

## Installation

```bash
pip install speedhive-tools
```

For development:
```bash
git clone https://github.com/ncrosty58/speedhive-tools.git
cd speedhive-tools
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Data & configuration

By default, the CLI and storage layer keep their SQLite cache and per-organization settings under a `./data` directory relative to the working directory (already gitignored). For anything unattended (cron, a systemd timer, a script), set `SPEEDHIVE_DATA_DIR` to a fixed absolute path explicitly rather than relying on that default — a relative path resolves differently depending on where the process happens to be invoked from.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SPEEDHIVE_DATA_DIR` | Root directory for the cache and org settings. | `./data` |
| `SPEEDHIVE_DB_PATH` | Explicit path to the SQLite cache file. | `<SPEEDHIVE_DATA_DIR>/speedhive.db` |

Per-organization behavior (parser engine, minimum laps for stats, Gemini key/model overrides) is configured in `data/orgs/<org_id>/settings.json`, read/written through `speedhive.settings`. Run `speedhive configure --org <id>` for an interactive setup wizard covering exactly those settings, or copy [settings.json.example](settings.json.example) by hand. `GEMINI_API_KEY`/`GEMINI_MODEL` can be set globally (bare env var) or per-org (`overrides` block in `settings.json`, or a `GEMINI_API_KEY_<org_id>`-style env var), with the org-specific value taking precedence.

Notification/email settings (Resend keys, recipient addresses) are **not** configured here — `speedhive-tools` has no code that sends email. That's entirely owned by `speedhive-tools-ui`; the CLI's `configure` wizard deliberately doesn't ask about them.

## CLI reference

Run `speedhive <command> --help` for full options on any of these:

```bash
# Sync an organization's cache (full or incremental)
speedhive sync-org --org 30476 --mode full
speedhive sync-org --org 30476 --mode incremental --recent-backfill-events 5

# Driver consistency rankings
speedhive report-consistency --org 30476 --min-laps 15 --ignore-outliers

# Fuzzy-match a driver and extract their laps
speedhive extract-driver-laps --org 30476 --driver "Jane Doe"

# Track-record curation: sync (if stale) then scan for new candidates
speedhive refresh-track-records --org 30476
# ...or scan the existing cache only, without contacting Speedhive
speedhive scan-track-records --org 30476

# Curated-record NDJSON import/export
speedhive export-curated-track-records --org 30476 --output curated.ndjson
speedhive import-curated-track-records --org 30476 --input curated.ndjson --mode merge

# Offline dumps
speedhive export-db-dump --org 30476 --output-dir ./output
speedhive import-dump --org 30476 --dump-dir ./output
speedhive export-dump --org 30476 --output ./output   # scrape straight to NDJSON, no DB required
speedhive export-lap-records --org 30476 --max-events 25

# Interactive per-org settings wizard (Gemini/parsing/min-laps only)
speedhive configure --org 30476
```

Both `scan-track-records` and `refresh-track-records` automatically pick up the org's `parsing.engine` setting (regex vs. Gemini) via `speedhive.settings.get_bulk_parser_for_org` — no separate flag needed.

## Python API

### Uncached scraping
```python
from speedhive.wrapper import SpeedhiveClient

client = SpeedhiveClient.create()
org = client.get_organization(30476)
events = client.iter_events(30476)          # generator over all events
sessions = client.get_sessions(event_id=12345)
laps = client.get_laps(session_id=67890)
```

### Cached storage + sync
```python
from speedhive.storage import SpeedhiveStorage
from speedhive.workflows.refresh_org_cache import refresh_org_cache

storage = SpeedhiveStorage("data/speedhive.db")
refresh_org_cache(client=client, storage=storage, org_id=30476, mode="incremental")

records = storage.get_track_records(30476, classification="Karting")
```

### Settings resolution
```python
from speedhive.settings import get_org_env_var, set_org_env_var, get_parsing_engine

set_org_env_var("GEMINI_API_KEY", 30476, "AIza...")
get_org_env_var("GEMINI_API_KEY", 30476)   # org override, else the bare GEMINI_API_KEY fallback
get_parsing_engine(30476)                   # "regex" or "llm"
```

More end-to-end scripts live in `examples/` (organizations, events, sessions, lap charts, announcements, streaming laps, track records).

## Development

```bash
pip install -e ".[dev]"
pytest              # full test suite (tests/)
ruff check src/     # lint
```

`speedhive/generated/` is an OpenAPI-generated low-level client and is not meant to be hand-edited.
