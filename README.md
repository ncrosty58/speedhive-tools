# speedhive-tools

CLI toolkit and Python library for the MyLaps Speedhive Event Results API.

## Install

```bash
pip install speedhive-tools
```

For local development:

```bash
git clone https://github.com/ncrosty58/speedhive-tools.git
cd speedhive-tools
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Quick CLI Usage

```bash
# Export raw offline data dump
speedhive export-full-dump --org 30476 --output ./output

# Compile raw offline NDJSON dumps into local SQLite database
speedhive to-sqlite --org 30476 --dump-dir ./output

# Run offline analysis and records extraction (reads from SQLite database)
speedhive report-consistency --org 30476 --top 10
speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname"
speedhive extract-track-records --org 30476

# Sync and update local organization cache files
speedhive refresh-org-cache --org 30476 --cache-root ./web_data/cache --mode incremental --recent-backfill-events 3
```

Run `speedhive --help` for the full command list.

## Python Usage

```python
from speedhive.wrapper import SpeedhiveClient

client = SpeedhiveClient.create(token="your-api-token")
events = client.get_events(org_id=30476, limit=5)
```

## Offline Workflow

1) **Export full raw data dump**:
   Downloads events, sessions, results, laps, and announcements to local NDJSON files.
   ```bash
   speedhive export-full-dump --org 30476 --output ./output
   ```

2) **Compile raw dumps to SQLite database**:
   Imports all NDJSON files under `./output/30476/` into a structured SQLite database.
   ```bash
   speedhive to-sqlite --org 30476 --dump-dir ./output
   ```

3) **Run offline analysis against the database**:
   ```bash
   speedhive report-consistency --org 30476
   speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname"
   ```

## Output Format

`export-full-dump` creates raw cache snapshots in `output/<org_id>/`:

```text
output/30476/
├── events.ndjson.gz
├── sessions.ndjson.gz
├── laps.ndjson.gz
├── announcements.ndjson.gz
├── results.ndjson.gz
└── .checkpoint.json
```

`to-sqlite` compiles those files into:
```text
output/30476/
└── laps_30476.db
```

## Project Structure

Canonical implementation lives in `src/speedhive/`:

```text
src/speedhive/
├── client.py
├── wrapper.py
├── generated/           # Auto-generated API client bindings
├── cli/                 # CLI entry point and dynamic discovery
│   ├── discovery.py
│   └── main.py
├── exporters/           # Scrapers and cache sync modules
│   ├── export_org_cache.py
│   ├── export_full_dump.py
│   └── ...
├── analyzers/           # Performance and lap analysis
│   ├── analyze_consistency.py
│   └── analyze_driver_laps.py
└── processing/          # SQLite ETL and track record compilation
    ├── process_sqlite_import.py
    ├── process_track_records.py
    ├── process_lap_analysis.py
    └── ndjson.py
```

## Notes

- **SQLite Backend**: All CSV storage workflows have been deprecated. Relational querying is fully powered by a local, indexed SQLite database file.
- Packaging is configured via `pyproject.toml` (PEP 621 + setuptools backend).
- The generated API client uses `attrs`; no Pydantic dependency.

## License

MIT © Nathan Crosty
