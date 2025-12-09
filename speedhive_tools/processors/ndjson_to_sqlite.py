"""Import NDJSON (gzipped) into a small SQLite database for fast queries.

This example focuses on `laps.ndjson.gz` and writes a `laps` table.

Usage:
  python examples/processing/ndjson_to_sqlite.py --input output/full_dump/30476 --out output/full_dump/30476/dump.db
"""
from __future__ import annotations

import argparse
import gzip
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict


def ingest_laps(in_path: Path, db_path: Path) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS laps (
            event_id INTEGER,
            session_id INTEGER,
            competitor_id TEXT,
            lap_number INTEGER,
            lap_time TEXT
        )
        """
    )

    inserted = 0
    with gzip.open(in_path, "rt", encoding="utf8") as inf:
        for line in inf:
            if not line.strip():
                continue
            rec: Dict[str, Any] = json.loads(line)
            rows = rec.get("rows") or rec.get("lapRows") or rec.get("laps") or []
            for r in rows:
                competitor = r.get("competitorId") or r.get("competitor_id") or r.get("id")
                lapnum = r.get("lapNumber") or r.get("lap_number") or r.get("lap")
                laptime = r.get("lapTime") or r.get("lap_time") or r.get("time")
                c.execute("INSERT INTO laps VALUES (?,?,?,?,?)", (rec.get("event_id"), rec.get("session_id"), competitor, lapnum, laptime))
                inserted += 1
    conn.commit()
    conn.close()
    return inserted


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Import laps NDJSON gz -> SQLite DB")
    p.add_argument("--input", type=Path, default=Path("output/full_dump/30476/laps.ndjson.gz"), help="Input laps NDJSON gz file path")
    p.add_argument("--out", type=Path, default=Path("output/full_dump/30476/dump.db"), help="Output SQLite DB path")
    args = p.parse_args(argv)

    if not args.input.exists():
        print("Input file not found:", args.input)
        return 2

    n = ingest_laps(args.input, args.out)
    print(f"Inserted {n} rows into {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
