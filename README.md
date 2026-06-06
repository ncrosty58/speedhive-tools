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
# Run analysis directly from the primary SQLite cache
speedhive report-consistency --org 30476 --db-path ./web_data/speedhive.db --top 10
speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname" --db-path ./web_data/speedhive.db
speedhive extract-track-records --org 30476 --db-path ./web_data/speedhive.db

# Export a raw offline NDJSON dump
speedhive export-dump --org 30476 --output ./output

# Import raw offline NDJSON dumps into the primary SQLite cache
speedhive import-dump --org 30476 --dump-dir ./output --db-path ./web_data/speedhive.db

# Legacy offline dump analysis still works as a fallback when no primary DB is available
speedhive report-consistency --org 30476 --dump-dir ./output
speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname" --dump-dir ./output
speedhive extract-track-records --org 30476 --dump-dir ./output

# Sync organization data into the primary SQLite cache
speedhive sync-org --org 30476 --db-path ./web_data/speedhive.db --mode incremental --recent-backfill-events 3
```

Run `speedhive --help` for the full command list.

## Python Usage

```python
from speedhive.wrapper import SpeedhiveClient

client = SpeedhiveClient.create(token="your-api-token")
events = client.get_events(org_id=30476, limit=5)
```

## Preferred Workflow

1) **Sync data into the primary SQLite cache**:
   Use the web app sync flow or your own pipeline to populate `./web_data/speedhive.db`.

2) **Run analysis against the primary cache**:
   ```bash
   speedhive report-consistency --org 30476 --db-path ./web_data/speedhive.db
   speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname" --db-path ./web_data/speedhive.db
   speedhive extract-track-records --org 30476 --db-path ./web_data/speedhive.db
   ```

## Offline Workflow

1) **Export a raw data dump**:
   Downloads events, sessions, results, laps, and announcements to local NDJSON files.
   ```bash
   speedhive export-dump --org 30476 --output ./output
   ```

2) **Import raw dumps into the primary SQLite cache**:
   Imports all NDJSON files under `./output/30476/` into your main cache database.
   ```bash
   speedhive import-dump --org 30476 --dump-dir ./output --db-path ./web_data/speedhive.db
   ```

3) **Run offline analysis against the database**:
   ```bash
   speedhive report-consistency --org 30476 --dump-dir ./output
   speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname" --dump-dir ./output
   ```

## Output Format

`export-dump` creates raw NDJSON snapshots in `output/<org_id>/`:

```text
output/30476/
├── events.ndjson.gz
├── sessions.ndjson.gz
├── laps.ndjson.gz
├── announcements.ndjson.gz
├── results.ndjson.gz
└── .checkpoint.json
```

`import-dump` imports those files into the primary cache database, for example:
```text
web_data/
└── speedhive.db
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
