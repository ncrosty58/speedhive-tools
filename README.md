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
speedhive export-full-dump --org 30476 --output ./output
speedhive report-consistency --org 30476 --top 10
speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname"
speedhive extract-track-records --org 30476
```

Run `speedhive --help` for the full command list.

## Python Usage

```python
from speedhive.wrapper import SpeedhiveClient

client = SpeedhiveClient.create(token="your-api-token")
events = client.get_events(org_id=30476, limit=5)
```

## Offline Workflow

1) Export a full dump:

```bash
speedhive export-full-dump --org 30476 --output ./output
```

2) Run offline analysis/processing against exported NDJSON:

```bash
speedhive report-consistency --org 30476
speedhive extract-driver-laps --org 30476 --driver "Firstname Lastname"
```

## Output Format

`export-full-dump` writes `output/<org_id>/`:

```text
output/30476/
├── events.ndjson.gz
├── sessions.ndjson.gz
├── laps.ndjson.gz
├── announcements.ndjson.gz
├── results.ndjson.gz
└── .checkpoint.json
```

## Project Structure

Canonical implementation lives in `src/speedhive/`:

```text
src/speedhive/
├── client.py
├── wrapper.py
├── generated/      # generated API client
├── cli/            # CLI entry + auto-discovery
├── exporters/
├── analyzers/
└── processing/     # offline processors/helpers
```

Legacy `speedhive_tools/` and `mylaps_client_wrapper.py` are compatibility shims that forward to `src/speedhive`.

## Notes

- Packaging is configured via `pyproject.toml` (PEP 621 + setuptools backend).
- The generated API client uses `attrs`; no Pydantic dependency.

## License

MIT © Nathan Crosty
