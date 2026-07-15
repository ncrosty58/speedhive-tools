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

## Python

```python
from speedhive.wrapper import SpeedhiveClient

client = SpeedhiveClient.create(token="your-api-token")
events = client.get_events(org_id=30476, limit=5)
```

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
