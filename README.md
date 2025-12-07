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

## Usage

### Export Commands

| Command | Description |
|---------|-------------|
| `export_full_dump.py --org <id>` | Export all data (events, sessions, laps, announcements) |
| `list_events_by_org.py <id>` | List events for an organization |
| `export_announcements_by_org.py <id>` | Export announcements only |
| `get_event_sessions.py <event_id>` | Get sessions for a specific event |
| `get_session_laps.py <session_id>` | Get lap times for a session |
| `get_session_results.py <session_id>` | Get results for a session |

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
python examples/processing/extract_laps_to_csv.py --input <dir> --out laps.csv
python examples/processing/extract_sessions_to_csv.py --input <dir> --out sessions.csv
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

## Project Structure

```
speedhive-tools/
├── mylaps_client/          # Generated OpenAPI client (event_results_client)
├── examples/
│   ├── export_full_dump.py          # Main exporter
│   ├── list_events_by_org.py        # List org events
│   ├── export_announcements_by_org.py
│   ├── get_event_sessions.py
│   ├── get_session_laps.py
│   ├── get_session_results.py
│   └── processing/
│       ├── processor_cli.py         # Interactive processor
│       ├── extract_laps_to_csv.py
│       ├── extract_sessions_to_csv.py
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
