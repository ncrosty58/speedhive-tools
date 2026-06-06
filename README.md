# speedhive-tools

Command-line toolkit and Python library for the MyLaps Speedhive Event Results API.

---

## Installation

```bash
pip install speedhive-tools
```

For development:

```bash
git clone https://github.com/ncrosty58/speedhive-tools.git
cd speedhive-tools
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

---

## Quick start – `speedhive` CLI

The installed console script `speedhive` provides a unified interface.

```bash
speedhive export-full-dump --org 30476 --output ./output
speedhive report-consistency --org 30476 --top 10
speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname"
speedhive extract-track-records --org 30476
```

Run `speedhive --help` to see all commands.  
The CLI auto‑discovers modules under `speedhive.exporters`, `speedhive.processors`, and `speedhive.analyzers`.

---

## Python library – `SpeedhiveClient` wrapper

```python
from speedhive.wrapper import SpeedhiveClient

client = SpeedhiveClient.create(token="your-api-token")

events = client.get_events(org_id=30476, limit=5)
for e in events:
    print(e["name"])

laps = client.get_laps(session_id=12345)
```

Available methods:  
`get_organization`, `get_events`, `iter_events`, `get_event`, `get_sessions`, `get_session`, `get_laps`, `get_results`, `get_announcements`, `get_lap_chart`, `get_championships`, `get_championship`, `get_server_time`, `get_track_records`, `get_fastest_track_record`, `iter_track_records_by_event`.

---

## Example scripts

The `examples/` directory contains runnable scripts demonstrating common tasks.  
Run them directly from the repository root:

```bash
python -m examples.example_get_events --org 30476 --limit 5
python -m examples.example_get_session_laps --session 12345
```

All examples use `SpeedhiveClient.create()`.

---

## Offline workflow (recommended)

1. Export a full dump:

```bash
speedhive export-full-dump --org 30476 --output ./output
```

2. Process and analyse the exported files without further API calls:

```bash
speedhive report-consistency --org 30476 --top 10
speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname"
```

The processing tools (`speedhive.processing.lap_analysis.compute_laps_and_enriched`) work directly on the dumped NDJSON files.

---

## Output format

Exported data is placed in `output/<org_id>/`:

```
output/30476/
├── events.ndjson.gz
├── sessions.ndjson.gz
├── laps.ndjson.gz
├── announcements.ndjson.gz
├── results.ndjson.gz
└── .checkpoint.json
```

---

## Developer notes

Package layout (under `src/speedhive/`):

```
src/speedhive/
├── client.py          # BaseClient, Client, AuthenticatedClient
├── wrapper.py         # SpeedhiveClient (user‑friendly wrapper)
├── generated/         # auto‑generated API client (httpx/attrs)
├── processing/        # ndjson, lap_analysis, etc.
├── cli/
│   ├── main.py        # CLI entry point
│   └── discovery.py   # auto‑discovery of subcommands
├── exporters/         # exporter modules (e.g. export_full_dump)
├── analyzers/         # analysis modules
└── processors/        # future processors
```

### Design decisions

- **No Pydantic dependency** – the generated API client uses `attrs` for models, and the wrapper returns plain dicts from `json.loads`. This keeps the dependency footprint small and avoids mixing validation frameworks. If stricter validation is needed later, it can be added selectively without affecting the rest of the codebase.

---

## Contributing

Pull requests welcome. Add tests for new functionality.

---

## License

MIT © Nathan Crosty
