# speedhive-tools

[![PyPI version](https://img.shields.io/pypi/v/speedhive-tools.svg)](https://pypi.org/project/speedhive-tools/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/ncrosty58/speedhive-tools/actions/workflows/publish.yml/badge.svg)](https://github.com/ncrosty58/speedhive-tools/actions)

Python toolkit for the [MyLaps Event Results API](https://api2.mylaps.com/v3/api-docs). Export race events, sessions, laps, and announcements to CSV, SQLite, or JSON with a single command.

## Features

- **Full Data Export** — Stream events, sessions, laps, and announcements for any organization
- **Multiple Output Formats** — CSV, SQLite, JSON, and compressed NDJSON
- **Memory Efficient** — Streaming architecture handles large datasets without high RAM usage
- **Resumable Downloads** — Checkpoint support for interrupted exports
- **Interactive CLI** — Process exported data with guided prompts or batch flags

## Installation

### From PyPI

```bash
pip install speedhive-tools
```

### From Source

```bash
git clone https://github.com/ncrosty58/speedhive-tools.git
cd speedhive-tools
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

### 1. Export Data

Export all data for an organization (events, sessions, laps, announcements):

```bash
python examples/export_full_dump.py --org 30476 --output ./output/full_dump --verbose
```

### 2. Process to CSV

Convert the exported NDJSON to flat CSV files:

```bash
python examples/processing/extract_laps_to_csv.py \
    --input output/full_dump/30476 \
    --out output/full_dump/30476/laps.csv
```

### 3. Or Use the Interactive CLI

```bash
python examples/processing/processor_cli.py
```

## Offline workflow

This project supports a simple offline workflow that lets you reproduce analytics from a canonical full dump without contacting the API during analysis.

- **Export (one-time / repeatable):** `examples/export_full_dump.py` writes NDJSON files under `output/full_dump/<org>/`. The exporter now includes session classification/results in `results.ndjson` when the API supports it.

    ```bash
    python3 examples/export_full_dump.py --org 30476 --output ./output/full_dump --verbose --no-resume
    ```

- **Process (offline):** `examples/process_full_dump.py` reads the dump directory and produces analysis-ready JSON files in `output/`:
    - `output/laps_by_driver_<org>.json` — mapping driver keys (`session<id>_pos<n>`) to lap-time lists
    - `output/consistency_<org>_enriched.json` — per-driver aggregated stats with `name` populated from `results.ndjson` when available

    ```bash
    python3 examples/process_full_dump.py --org 30476 --dump-dir output/full_dump --out-dir output
    ```

- **Report (offline):** Example scripts under `examples/fun` (e.g. `report_driver_consistency.py`) read the `output/` artifacts above and run without API access.

    ```bash
    python3 examples/fun/report_driver_consistency.py --name "Nathan Crosty" --org 30476
    ```

Notes and tips:
- The authoritative analysis files live under `output/` — prefer `output/consistency_<org>_enriched.json` and `output/laps_by_driver_<org>.json` for downstream reporting.
- Avoid keeping old copies of generated files at the repository root (e.g. `./consistency_<org>_enriched.json`) — they can be stale. Remove them to prevent confusion.
- To force the exporter to re-fetch session results, run it with `--no-resume` so checkpoints are cleared and `results.ndjson` is repopulated.


## Usage

### Export Commands

| Command | Description |
|---------|-------------|
| `export_full_dump.py --org <id>` | Export all data (events, sessions, laps, announcements) |
| `export_events.py <org_id>` | Export events for an organization |
| `export_sessions.py <event_id>` | Export sessions for an event |
| `export_laps.py <session_id>` | Export lap times for a session |
| `export_results.py <session_id>` | Export results/classification for a session |
| `export_announcements.py --org <id>` | Export announcements for an organization |
| `export_championships.py --org <id>` | Export championships for an organization |
| `export_championships.py --championship <id>` | Export championship standings |
| `export_lap_chart.py <session_id>` | Export lap chart data for visualizations |
| `export_track_records.py --org <id>` | Export track records for an organization |
| `get_fastest_records.py --org <id>` | Get fastest track record for each classification |

### Export Options

```bash
python examples/export_full_dump.py \
    --org 30476 \
    --output ./output/full_dump \
    --max-events 10 \
    --max-sessions-per-event 5 \
    --concurrency 2 \
    --verbose \
    --dry-run
```

| Flag | Description |
|------|-------------|
| `--org` | Organization ID (required, repeatable) |
| `--output` | Output directory (default: `./output/full_dump`) |
| `--max-events` | Limit number of events to export |
| `--max-sessions-per-event` | Limit sessions per event |
| `--concurrency` | Parallel request limit (default: 5) |
| `--token` | API token for authenticated endpoints |
| `--dry-run` | Preview without writing files |
| `--verbose` | Enable detailed logging |

### Processing Commands

Convert exported NDJSON to analysis-ready formats:

```bash
# Extract to CSV
python examples/processing/extract_events_to_csv.py --input <dir> --out events.csv
python examples/processing/extract_sessions_to_csv.py --input <dir> --out sessions.csv
python examples/processing/extract_laps_to_csv.py --input <dir> --out laps.csv
python examples/processing/extract_announcements_to_csv.py --input <dir> --out announcements.csv

# Import to SQLite
python examples/processing/ndjson_to_sqlite.py --input <dir>/laps.ndjson.gz --out dump.db
```

### Processor CLI

Interactive mode for batch processing:

```bash
# Interactive - prompts for org and output options
python examples/processing/processor_cli.py

# Non-interactive - process all data types
python examples/processing/processor_cli.py --org 30476 --run-all
```

## Using the Client Library

If you want to build your own programs using the MyLaps API, use the `SpeedhiveClient` wrapper for a simple, Pythonic interface.

### Quick Start

```python
from mylaps_client_wrapper import SpeedhiveClient

client = SpeedhiveClient()

# Get events for an organization
events = client.get_events(org_id=30476, limit=10)
for event in events:
    print(f"{event['name']} - {event.get('date')}")

# Get sessions for an event
sessions = client.get_sessions(event_id=123456)

# Get lap times for a session
laps = client.get_laps(session_id=789012)
for lap in laps:
    print(f"Lap {lap.get('lapNumber')}: {lap.get('lapTime')}")

# Get results/classification
results = client.get_results(session_id=789012)

# Get track records for an organization
records = client.get_track_records(org_id=30476, classification="IT7")
for record in records:
    print(f"{record['classification']}: {record['lap_time']} by {record['driver']}")

# Get the fastest track record for a classification
fastest = client.get_fastest_track_record(org_id=30476, classification="IT7")
if fastest:
    print(f"Fastest IT7: {fastest['lap_time']} by {fastest['driver']}")
```

### Available Methods

| Method | Description |
|--------|-------------|
| `get_organization(org_id)` | Get organization details |
| `get_events(org_id, limit, offset)` | Get events for an organization |
| `iter_events(org_id)` | Iterate all events (handles pagination) |
| `get_event(event_id)` | Get event details |
| `get_sessions(event_id)` | Get sessions for an event |
| `get_session(session_id)` | Get session details |
| `get_laps(session_id)` | Get all lap times for a session |
| `get_results(session_id)` | Get classification/standings |
| `get_announcements(session_id)` | Get session announcements |
| `get_lap_chart(session_id)` | Get position changes per lap (for visualizations) |
| `get_championships(org_id)` | Get championships for an organization |
| `get_championship(championship_id)` | Get championship standings |
| `get_track_records(org_id, classification, limit_events)` | Get track records for an organization |
| `get_fastest_track_record(org_id, classification, limit_events)` | Get fastest track record for a classification |
| `iter_track_records_by_event(org_id, classification)` | Memory-efficient iterator for track records |
| `get_server_time()` | Get API server time |

### With Authentication

Some endpoints require authentication:

```python
client = SpeedhiveClient(token="YOUR_API_TOKEN")
```

### Pagination Example

Iterate through all events without worrying about pagination:

```python
client = SpeedhiveClient()

for event in client.iter_events(org_id=30476):
    print(event['name'])
    
    # Get all sessions and laps for each event
    for session in client.get_sessions(event['id']):
        laps = client.get_laps(session['id'])
        print(f"  {session['name']}: {len(laps)} laps")
```

### Track Records

Track records are extracted from session announcements. The API efficiently scans events to find "New Track Record" announcements. Records now include an optional `marque` field (car make/model) when present in the announcement, and driver names are normalized (leading bracketed competitor numbers such as "[25]" are removed).

```python
client = SpeedhiveClient()

# Get all track records for an organization
records = client.get_track_records(org_id=30476)

# Filter by classification
it7_records = client.get_track_records(org_id=30476, classification="IT7")

# Get only the fastest (current) record for a classification
fastest = client.get_fastest_track_record(org_id=30476, classification="IT7")
if fastest:
    print(f"{fastest['classification']}: {fastest['lap_time']} by {fastest['driver']}")

# Memory-efficient iteration (processes one event at a time)
for record in client.iter_track_records_by_event(org_id=30476):
    print(f"{record['classification']}: {record['lap_time']}")
```

**Performance Tips:**
- Use `limit_events` parameter to limit the scan for testing/development
- Use `iter_track_records_by_event()` for large organizations to avoid loading all data into memory
- Filter by `classification` to reduce processing time

### Using the Raw Client

For advanced use cases, you can access the underlying generated client directly:

```python
import sys
sys.path.insert(0, "mylaps_client")

from event_results_client import Client
from event_results_client.api.organization_controller.get_event_list import sync_detailed
import json

client = Client(base_url="https://api2.mylaps.com")
response = sync_detailed(id=30476, client=client, count=50)
events = json.loads(response.content)
```

For the full API specification, see the [MyLaps API Documentation](https://api2.mylaps.com/v3/api-docs).

## Project Structure

```
speedhive-tools/
├── mylaps_client/          # Generated OpenAPI client (event_results_client)
├── mylaps_client_wrapper.py # User-friendly API wrapper (SpeedhiveClient)
├── examples/
│   ├── export_full_dump.py          # Bulk exporter (all data for org)
│   ├── export_events.py             # Export events for an org
│   ├── export_sessions.py           # Export sessions for an event
│   ├── export_laps.py               # Export laps for a session
│   ├── export_results.py            # Export results for a session
│   ├── export_announcements.py      # Export announcements
│   ├── export_championships.py      # Export championships/standings
│   ├── export_lap_chart.py          # Export lap chart data
│   └── processing/
│       ├── processor_cli.py         # Interactive processor
│       ├── extract_events_to_csv.py
│       ├── extract_sessions_to_csv.py
│       ├── extract_laps_to_csv.py
│       ├── extract_announcements_to_csv.py
│       └── ndjson_to_sqlite.py
├── tests/                  # Unit tests
└── output/                 # Default export location (gitignored)
```

## Output Format

The exporter creates gzipped NDJSON files:

```
output/full_dump/<org_id>/
├── events.ndjson.gz
├── sessions.ndjson.gz
├── laps.ndjson.gz
├── announcements.ndjson.gz
└── .checkpoint.json        # Resume state
```

## Development

### Run Tests

```bash
pip install pytest
pytest
```

### Regenerate API Client

If the MyLaps API spec changes:

```bash
pip install openapi-python-client
openapi-python-client generate --url https://api2.mylaps.com/v3/api-docs --output-path ./mylaps_client
```

### Build Distribution

```bash
pip install build
python -m build
```

## CI/CD

This project uses GitHub Actions for automated testing and PyPI publishing. Pushing a version tag triggers:

1. Run test suite
2. Build sdist and wheel
3. Publish to PyPI

```bash
git tag v0.1.3
git push origin v0.1.3
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

[MIT](LICENSE) © Nathan Crosty

## Links

- [PyPI Package](https://pypi.org/project/speedhive-tools/)
- [MyLaps API Documentation](https://api2.mylaps.com/v3/api-docs)
- [GitHub Repository](https://github.com/ncrosty58/speedhive-tools)
