# speedhive-tools

CLI toolkit and Python library for the MyLaps Speedhive API.

## Install

```bash
pip install speedhive-tools
```

## Develop

```bash
git clone https://github.com/ncrosty58/speedhive-tools.git
cd speedhive-tools
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Common Commands

```bash
speedhive sync-org --org 30476
speedhive report-consistency --org 30476
speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname"
speedhive export-track-records --org 30476
speedhive scan-track-records --org 30476
speedhive refresh-track-records --org 30476
speedhive export-dump --org 30476 --output ./output
speedhive import-dump --org 30476 --dump-dir ./output
speedhive export-curated-track-records --org 30476 --output ./curated.ndjson
speedhive import-curated-track-records --org 30476 --input ./curated.ndjson
```

Run `speedhive --help` for the full command list.

## Getting Started

There are two ways to use this package:

- Use `SpeedhiveClient` for direct API calls.
- Use the CLI analysis and export commands against the local SQLite cache.

If you want the cache-based commands, sync an organization first:

```bash
speedhive sync-org --org 30476
```

After that, commands like `report-consistency`, `extract-driver-laps`, `scan-track-records`, and `refresh-track-records` can use the local cache. Run `sync-org` again whenever you want to refresh it.

## Python

```python
from speedhive.wrapper import SpeedhiveClient

client = SpeedhiveClient.create(token="your-api-token")
events = client.get_events(org_id=30476, limit=5)
```

### Friendly Client

`SpeedhiveClient` is the simplest way to talk to the API. It hides the low-level generated client and gives you direct methods for the common lookups:

```python
from speedhive.wrapper import SpeedhiveClient

client = SpeedhiveClient.create(token="your-api-token")

org = client.get_organization(30476)
events = client.iter_events(30476)
event = client.get_event(12345, include_sessions=True)
sessions = client.get_sessions(12345)
laps = client.get_laps(67890)
announcements = client.get_announcements(67890)
track_records = client.get_track_records(30476)
fastest = client.get_fastest_track_record(30476, "FA")
```

Use `get_*` when you want a list or one object. Use `iter_events(...)` when you want to stream events without loading the whole set at once.

## Package Layout

```text
src/speedhive/
├── analysis/      # Shared parsing and computation helpers
├── analyzers/     # Read-only reports
├── cli/           # CLI entry points
├── exporters/     # NDJSON and file exporters
├── stores/        # Workflow file persistence
└── workflows/     # Sync, import, and track-record orchestration
```

## Notes

- SQLite is the main local cache.
- NDJSON is used for exports and curated track-record workflow files.
- The UI repo uses this package as a submodule.
