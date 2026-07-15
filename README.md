# speedhive-tools

CLI toolkit and Python library for the MyLaps Speedhive Event Results API.

## Install

```bash
pip install speedhive-tools
```

## Related Projects

- Web UI: `speedhive-tools-ui` at https://github.com/ncrosty58/speedhive-tools-ui

For local development:

```bash
git clone https://github.com/ncrosty58/speedhive-tools.git
cd speedhive-tools
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Quick CLI Usage

```bash
# Sync organization data into the primary SQLite cache (default database is ./web_data/speedhive.db)
speedhive sync-org --org 30476

# Run analysis directly from the SQLite cache
speedhive report-consistency --org 30476 --top 10
speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname"
speedhive extract-track-records --org 30476
speedhive scan-track-records --org 30476
speedhive refresh-track-records --org 30476

# Offline utility commands (exporting raw dumps, then importing into cache)
speedhive export-dump --org 30476 --output ./output
speedhive import-dump --org 30476 --dump-dir ./output
```

Run `speedhive --help` for the full command list.

## Python Usage

```python
from speedhive.wrapper import SpeedhiveClient

client = SpeedhiveClient.create(token="your-api-token")
events = client.get_events(org_id=30476, limit=5)
```

## Standard CLI Workflow

All analysis commands query the central SQLite cache (`./web_data/speedhive.db` by default). There are two standard ways to populate this cache:

### Option A: Direct Sync (Recommended)
Query the remote Mylaps Speedhive API directly to populate the cache:
```bash
speedhive sync-org --org 30476
```

### Option B: Offline Export / Import Ingest
If you want to migrate data or run analysis offline:
1) **Export raw data dump**:
   ```bash
   speedhive export-dump --org 30476 --output ./output
   ```
2) **Import raw dumps into the SQLite cache**:
   ```bash
   speedhive import-dump --org 30476 --dump-dir ./output
   ```

### Running Analysis
Once data is in the SQLite cache, run reports against the database:
```bash
speedhive report-consistency --org 30476
speedhive extract-driver-laps --org 30476 --driver "Firstname/Lastname"
speedhive extract-track-records --org 30476
speedhive scan-track-records --org 30476
speedhive refresh-track-records --org 30476
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

`extract-track-records`, `export-lap-records`, and `export-db-dump` emit NDJSON
as well. `extract-track-records` writes a `{"_meta": {...}}` first line
(org id, classification filter, generated-at timestamp) followed by one record
per line.

Track-record curation lives in `speedhive.processing.track_records_curation`:

- `run_sync_and_diff(...)` assumes the SQLite cache is already populated and only performs extract/normalize/diff against curated and rejected records.
- `refresh_and_scan(...)` is the orchestration helper used by the UI and CLI when they want to refresh the org cache first and then run the curation scan.
- `load_curated(...)`, `save_curated(...)`, `load_candidates(...)`, `save_candidates(...)`, `load_rejected(...)`, and `save_rejected(...)` all use the shared NDJSON storage helpers.

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
└── processing/
    └── track_records_curation.py  # Track-record curation and review-state orchestration
```

## Notes

- **SQLite Backend**: All CSV storage workflows have been deprecated. Relational querying is fully powered by a local, indexed SQLite database file.
- Packaging is configured via `pyproject.toml` (PEP 621 + setuptools backend).
- The generated API client uses `attrs`; no Pydantic dependency.

## License

MIT © Nathan Crosty
