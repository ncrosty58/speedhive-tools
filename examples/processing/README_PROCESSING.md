Processing exported NDJSON
=========================

This folder contains helper scripts to process the `output/full_dump/<org>/` NDJSON
files produced by `examples/export_full_dump.py`.

Included scripts
----------------

- `extract_laps_to_csv.py` — stream `laps.ndjson.gz` and write a flattened CSV of lap rows.
  ```bash
  python examples/processing/extract_laps_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/laps_flat.csv
  ```

- `ndjson_to_sqlite.py` — import NDJSON files into a SQLite database for SQL queries.
  ```bash
  python examples/processing/ndjson_to_sqlite.py --input output/full_dump/30476/laps.ndjson.gz --out output/full_dump/30476/dump.db
  sqlite3 output/full_dump/30476/dump.db "SELECT COUNT(*) FROM laps;"
  ```

- `extract_sessions_to_csv.py` — stream `sessions.ndjson.gz` and write a flattened CSV of sessions.
  ```bash
  python examples/processing/extract_sessions_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/sessions_flat.csv
  ```

- `extract_announcements_to_csv.py` — stream `announcements.ndjson.gz` and write a flattened CSV.
  ```bash
  python examples/processing/extract_announcements_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/announcements_flat.csv
  ```

- `processor_cli.py` — interactive CLI that scans `output/full_dump/` for orgs and runs the above extractors (and the SQLite import) for a selected org or `all`.
  ```bash
  # run interactively
  python examples/processing/processor_cli.py

  # run non-interactively for a specific org and run all steps
  python examples/processing/processor_cli.py --org 30476 --run-all
  ```

Notes
-----

- All scripts stream gzipped NDJSON files and avoid loading everything into RAM.
- Field names in the API are inconsistent; extractors contain normalization logic to handle common variants (e.g. `competitorId`/`competitor_id`, `lapNumber`/`lap_number`).

Quick workflow
--------------

1. Run the exporter to `output/full_dump/<org>/` (see top-level examples).
2. Run the processor CLI and pick the org to convert files to CSV/SQLite.

Example end-to-end commands
---------------------------

```bash
# run exporter (example)
python examples/export_full_dump.py --org 30476 --output ./output/full_dump --max-events 10

# run all processing steps for org 30476
python examples/processing/processor_cli.py --org 30476 --run-all

# then inspect results
ls -lh output/full_dump/30476
sqlite3 output/full_dump/30476/dump.db "SELECT COUNT(*) FROM laps;"
```
