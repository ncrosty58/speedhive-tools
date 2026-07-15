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

## Getting Started

Start by syncing an organization from Speedhive into the local SQLite cache:

```bash
speedhive sync-org --org 30476
```

That cache becomes the source for analysis, exports, and track-record workflows:

```bash
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

If you need to refresh the cache later, run `sync-org` again for the organization.

## Python Client

`SpeedhiveClient` is the friendly live API client. It talks directly to Speedhive and gives you simple methods for the common lookups:

```python
from speedhive.wrapper import SpeedhiveClient

client = SpeedhiveClient.create(token="your-api-token")

org = client.get_organization(30476)
events = client.get_events(30476, limit=5)
event = client.get_event(12345, include_sessions=True)
sessions = client.get_sessions(12345)
laps = client.get_laps(67890)
announcements = client.get_announcements(67890)
track_records = client.get_track_records(30476)
fastest = client.get_fastest_track_record(30476, "FA")
```

Use the client when you want live API data. Use the CLI when you want to work from the synced local cache.

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

- SQLite is the local cache.
- NDJSON is used for exports and curated track-record workflow files.
- The UI repo uses this package as a submodule.
