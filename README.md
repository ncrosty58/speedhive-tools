# speedhive-tools

[![PyPI version](https://img.shields.io/pypi/v/speedhive-tools.svg)](https://pypi.org/project/speedhive-tools/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Command-line toolkit and client wrapper for the MyLaps Event Results API (export, process, analyze).

**This README covers:** the unified `speedhive` CLI, how discovery and module registration work, the `SpeedhiveClient` wrapper, example scripts (in `examples/`), and how to run tests.

Command-line toolkit and client wrapper for the MyLaps Event Results API (export, process, analyze).

**This README covers:** the unified `speedhive` CLI, how discovery and module registration work, the `SpeedhiveClient` wrapper, example scripts (in `examples/`), and how to run tests.

## Highlights

- Export events, sessions, laps, and announcements to gzipped NDJSON
- Process exported dumps into reproducible analysis artifacts (JSON/CSV/SQLite)
- Unified CLI with interactive and scripted modes
- Auto-discovery of exporter/processor/analyzer modules with optional argparse integration
- Lightweight `SpeedhiveClient` wrapper to make the generated API client easier to use

## Installation

From PyPI:

```bash
pip install speedhive-tools
```

From source (developer):

```bash
git clone https://github.com/ncrosty58/speedhive-tools.git
cd speedhive-tools
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Primary Usage — `speedhive` CLI

The `speedhive` entrypoint (installed console script or `python -m speedhive_tools.cli`) is the recommended interface.

Interactive mode (explore available actions and discovered modules):

```bash
speedhive
# or when running from source
python -m speedhive_tools.cli
```

When invoked without a subcommand the CLI launches a short interactive front screen that:

- Lists discovered commands grouped by category: Exporters, Processors, Analyzers
- Lets you select a command to run and optionally provide extra args
 - Includes a small set of core scripted workflows (export-full-dump, extract-driver-laps, report-consistency)

Scripted usage (automation / CI):

```bash
# Export a full dump for an organization (writes files under `output/<org>/`)
speedhive export-full-dump --org 30476 --output ./output --verbose

# Show the top N most consistent drivers
speedhive report-consistency --org 30476 --top 10 --min-laps 20

# Extract laps for a specific driver
speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname"

# Extract track records to CSV
speedhive extract-track-records --org 30476
```

Use `speedhive <subcommand> --help` for details on flags for the built-in core commands.

## Discovery and Extension

The CLI performs runtime discovery of any modules under these packages:

- `speedhive_tools.exporters`
- `speedhive_tools.processors`
- `speedhive_tools.analyzers`

Discovery rules:

- Any module exposing a callable `main()` is considered a runnable command and will be listed in the interactive menu.
- The CLI will attempt to register discovered modules with `argparse` so `speedhive <cmd> --help` can show flags.

Registration behavior:

- If a discovered module defines a `register_subparser(parser: argparse.ArgumentParser)` function the CLI will call it so the module can declare its own flags (recommended for full integration).
- If `register_subparser` is not present or registration fails, the CLI falls back to a passthrough subparser that accepts `extra_args` (nargs=argparse.REMAINDER) and forwards those to the module's `main()` as `argv`.

How to integrate a new module:

1. Implement `main(argv=None)` in your module (existing convention).
2. Optionally implement `register_subparser(parser)` to expose flags and improve `--help` output.

This approach keeps existing modules working (no mandatory changes) while enabling a richer CLI experience when modules opt in.

## Examples (quick start)

Example scripts are in the `examples/` directory. They demonstrate using the `SpeedhiveClient` wrapper and how to call common endpoints.

Run an example directly (from the repository root):

```bash
python -m examples.example_get_events --org 30476 --limit 5
python -m examples.example_get_session_laps --session 12345
python -m examples.example_server_time
```

List of provided example scripts (each defines `main(argv=None)`):

- `examples/example_server_time.py` — get server time
- `examples/example_get_events.py` — list events for an org
- `examples/example_get_event_sessions.py` — list sessions for an event
- `examples/example_get_session_laps.py` — fetch laps for a session
- `examples/example_get_session_results.py` — fetch classification/results
- `examples/example_get_session_announcements.py` — fetch session announcements
- `examples/example_get_lap_chart.py` — fetch lap chart data
- `examples/example_championships.py` — list/fetch championships
- `examples/example_track_records.py` — find track records
- `examples/example_get_organization.py` — get organization details

These examples are intentionally minimal and synchronous; they demonstrate how to use the `SpeedhiveClient` wrapper from `mylaps_client_wrapper.py`.

## SpeedhiveClient wrapper

The module `mylaps_client_wrapper.py` provides the `SpeedhiveClient` class — a small, ergonomic wrapper around the generated `event_results_client` API. It exposes convenience methods such as:

- `get_events(org_id, limit=None)`
- `iter_events(org_id)`
- `get_event(event_id)`
- `get_sessions(event_id)`
- `get_session(session_id)`
- `get_laps(session_id, flatten=True)`
- `get_results(session_id)`
- `get_announcements(session_id)`
- `get_lap_chart(session_id)`
- `get_championships(org_id)`
- `get_track_records(org_id, ...)`
- `get_server_time()`

Example usage:

```python
from mylaps_client_wrapper import SpeedhiveClient

client = SpeedhiveClient()
events = client.get_events(org_id=30476, limit=5)
for e in events:
	print(e.get('id'), e.get('name'))

laps = client.get_laps(session_id=12345)
```

See `examples/` for small scripts that show common patterns.

## Offline workflow (recommended)

1. Export a canonical full dump:

```bash
speedhive export-full-dump --org 30476 --output ./output --no-resume
```

2. Run processors and analyzers directly on the exported dump (artifacts computed on-demand, no API calls required):

```bash
speedhive report-consistency --org 30476 --top 10
speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname"
speedhive extract-track-records --org 30476
```

## Output format

Exported NDJSON layout (gzipped files):

```
output/<org_id>/
├── events.ndjson.gz
├── sessions.ndjson.gz
├── laps.ndjson.gz
├── announcements.ndjson.gz
└── .checkpoint.json
```

Processor outputs (examples):

- `output/track_records_<org>.csv` — track records extracted from announcements
- `output/driver_laps_<org>_<driver>.csv` — laps for a specific driver

## Running tests

Install test deps and run pytest:

```bash
pip install -r requirements.txt
pytest -q
```

New tests include `tests/test_examples_scripts.py` which validates that each example module exposes a callable `main()`.

## Developer notes (package layout)

- `speedhive_tools/exporters` — exporter modules (e.g. `export_full_dump.py`)
- `speedhive_tools/processors` — processors and extractors
- `speedhive_tools/analyzers` — reporting and analysis utilities
- `mylaps_client_wrapper.py` — `SpeedhiveClient` wrapper
- `examples/` — runnable example scripts demonstrating wrapper usage

If you add new modules that should be visible in the CLI make them discoverable by placing them in one of the exporter/processor/analyzer packages and either provide `main()` (required) or also provide `register_subparser(parser)` (recommended) for argparse help integration.

## Contributing

Contributions welcome. Open an issue or PR and include tests for new functionality.

## License

[MIT](LICENSE) © Nathan Crosty

## Links

- [PyPI Package](https://pypi.org/project/speedhive-tools/)
- [MyLaps API Documentation](https://api2.mylaps.com/v3/api-docs)
- [GitHub Repository](https://github.com/ncrosty58/speedhive-tools)
