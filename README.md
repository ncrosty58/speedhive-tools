# 🚀 speedhive-tools

Utilities and examples for interacting with the MyLaps / Event Results API using a locally-generated OpenAPI Python client.

This repository bundles a generated client (`mylaps_client/`) and a set of small, focused example scripts and processing helpers for exporting and post-processing event/session/lap data.

---

## 📚 Table of Contents

- [Quick Start](#quick-start)
- [What’s in this repo](#whats-in-this-repo)
- [Common Commands](#common-commands)
- [Process Exported Data](#process-exported-data)
- [Interactive Processor CLI](#interactive-processor-cli)
- [Notes & Tips](#notes--tips)
- [Regenerating the Client](#regenerating-the-client)
- [Testing & CI](#testing--ci)
- [Contributing & Next Steps](#contributing--next-steps)

---

## 🚀 Quick Start

Requirements: Python 3.10+ and a virtualenv.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run examples from the repository root so the bundled `mylaps_client` is importable.

---

## 📁 What’s in this repo

- `mylaps_client/` — generated OpenAPI Python client (importable as `event_results_client`).
- `examples/` — small, focused example scripts (exporters, API usage).
- `examples/processing/` — streaming NDJSON -> CSV/SQLite helpers and an interactive processor CLI.
- `tests/` — unit tests for processing helpers.
- `output/` — suggested location for exporter output (ignored by git).

---

## 🛠️ Common Commands

- List events for an org:

```bash
python examples/list_events_by_org.py 30476 --verbose
```

- Export announcements for an org (per-event JSON files):

```bash
python examples/export_announcements_by_org.py 30476 --output ./output/announcements --verbose
```

- Full dump (stream NDJSON, gzipped by default):

```bash
python examples/export_full_dump.py --org 30476 --output ./output/full_dump --verbose
```

---

## 📦 Process Exported Data

- Extract laps to CSV:

```bash
python examples/processing/extract_laps_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/laps_flat.csv
```

- Extract sessions to CSV:

```bash
python examples/processing/extract_sessions_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/sessions_flat.csv
```

- Extract announcements to CSV (also writes `announcements_summary.json`):

```bash
python examples/processing/extract_announcements_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/announcements_flat.csv
```

- Import laps to SQLite:

```bash
python examples/processing/ndjson_to_sqlite.py --input output/full_dump/30476/laps.ndjson.gz --out output/full_dump/30476/dump.db
sqlite3 output/full_dump/30476/dump.db "SELECT COUNT(*) FROM laps;"
```

---

## 🧭 Interactive Processor CLI

The processor CLI scans `output/full_dump/` and can run extractors for a chosen org interactively. Run:

```bash
python examples/processing/processor_cli.py
# or non-interactive for a specific org
python examples/processing/processor_cli.py --org 30476 --run-all
```

The CLI supports choosing output formats and which data types to process (laps, sessions, announcements).

---

## 📝 Notes & Tips

- Run examples from the repo root so local imports work.
- Use `--token` for APIs that require authentication.
- Exporter supports `--max-events`, `--max-sessions-per-event`, and `--dry-run` for testing.
- Long exports create a checkpoint file (`outdir/.checkpoint.json`) so runs can resume after interruption.

---

## 🔁 Regenerating the Client

If the MyLaps API spec changes, regenerate the client and place it in `mylaps_client/`.

Example with `openapi-python-client`:

```bash
python -m openapi_python_client generate --url https://api2.mylaps.com/v3/api-docs --output-path ./mylaps_client
```

---

## ✅ Testing & CI

- Unit tests are under `tests/` and validate the streaming extractors.
- I can add a GitHub Actions workflow to run tests and publish on tag; let me know if you'd like that.

---

## 🤝 Contributing & Next Steps

If you'd like, I can:

- Harden the exporter (retries/backoff, schema checks).
- Improve SQLite schema and indexing for analysis workloads.
- Add CI workflow to run tests and publish releases automatically.

---

If you'd like a different TOC layout, or want me to include examples for a specific org (e.g., `Waterford Hills`), tell me and I'll update this README.
# speedhive-tools

Utilities and examples for interacting with the MyLaps / Event Results API using a locally-generated OpenAPI Python client.

This repository contains a generated client under `mylaps_client/` and example scripts that demonstrate how to list events and export session announcements for an organization.

## Table of contents

- Quick Start
- What’s in this repo
- Common commands
- Process exported data
- Notes & tips
- Regenerating the client
- Testing and CI
- Contributing and next steps

## Quick Start

Requirements: Python 3.10+ and a virtualenv.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## What’s in this repo

- `mylaps_client/` — generated OpenAPI Python client (importable as `event_results_client` when running examples from the repo root).
- `examples/` — runnable examples that demonstrate common API tasks.
- `examples/processing/` — data-processing helpers (convert NDJSON -> CSV/SQLite) and an interactive CLI.
- `output/` — suggested place for example outputs (this directory is in `.gitignore`).

## Common commands

- List events for an org:

```bash
python examples/list_events_by_org.py 30476 --verbose
```

- Export announcements for an org (per-event JSON files):

```bash
python examples/export_announcements_by_org.py 30476 --output ./output/announcements --verbose
```

- Full dump (stream NDJSON, gzipped by default):

```bash
python examples/export_full_dump.py --org 30476 --output ./output/full_dump --verbose
```

## Process exported data

- Extract laps to CSV:

```bash
python examples/processing/extract_laps_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/laps_flat.csv
```

- Extract sessions to CSV:

```bash
python examples/processing/extract_sessions_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/sessions_flat.csv
```

- Extract announcements to CSV:

```bash
python examples/processing/extract_announcements_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/announcements_flat.csv
```

- Import laps to SQLite:

```bash
python examples/processing/ndjson_to_sqlite.py --input output/full_dump/30476/laps.ndjson.gz --out output/full_dump/30476/dump.db
sqlite3 output/full_dump/30476/dump.db "SELECT COUNT(*) FROM laps;"
```

- Interactive processor CLI (scan `output/full_dump/` and run steps):

```bash
python examples/processing/processor_cli.py
# or non-interactive for a specific org
python examples/processing/processor_cli.py --org 30476 --run-all
```

## Notes & tips

- Run examples from the repository root so the local `mylaps_client` package is on `sys.path`.
- Use `--token` on example CLIs when endpoints require authentication.
- The exporter supports `--max-events`, `--max-sessions-per-event`, and `--dry-run` for low-memory testing.
- Long runs write a checkpoint file (`outdir/.checkpoint.json`) so you can resume after interruptions.

## Regenerating the client

If the API OpenAPI spec changes, regenerate the client and place it under `mylaps_client/`.

Example using `openapi-python-client`:

```bash
python -m openapi_python_client generate --url https://api2.mylaps.com/v3/api-docs --output-path ./mylaps_client
```

## Testing and CI

- There are minimal tests under `tests/` (including processing extractor tests). Add CI and recorded fixtures if you want reproducible runs in CI.

## Contributing and next steps

If you'd like I can implement any of the following:

- Add retries/backoff to the exporter and recorded fixtures for CI.
- Add extra extractors (results/classifications) or tune CSV columns.
- Add a GitHub Actions workflow to build and publish to PyPI on tag.

---

If you'd like me to change the TOC style (e.g. a shorter TOC or grouped sections), tell me which layout you prefer.
# speedhive-tools

Utilities and examples for interacting with the MyLaps / Event Results API using a locally-generated OpenAPI Python client.

This repository contains a generated client under `mylaps_client/` and example scripts that demonstrate how to list events and export session announcements for an organization.

Table of contents

- Quick start
- Examples
- Exporter details
- Troubleshooting

- Regenerating the client

- Contributing


