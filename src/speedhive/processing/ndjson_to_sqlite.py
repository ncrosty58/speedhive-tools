"""Import laps NDJSON(.gz) into a lightweight SQLite table."""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from speedhive.processing.ndjson import open_ndjson


def ingest_laps(in_path: Path, db_path: Path) -> int:
    """Ingest lap rows into `laps` table and return inserted row count."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
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
    for record in open_ndjson(in_path):
        rows = record.get("rows") or record.get("lapRows") or record.get("laps") or []
        for row in rows:
            competitor = row.get("competitorId") or row.get("competitor_id") or row.get("id")
            lap_number = row.get("lapNumber") or row.get("lap_number") or row.get("lap")
            lap_time = row.get("lapTime") or row.get("lap_time") or row.get("time")
            cur.execute(
                "INSERT INTO laps VALUES (?,?,?,?,?)",
                (record.get("event_id"), record.get("session_id"), competitor, lap_number, lap_time),
            )
            inserted += 1

    conn.commit()
    conn.close()
    return inserted


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Import laps NDJSON(.gz) into SQLite")
    parser.add_argument("--input", type=Path, default=Path("output/30476/laps.ndjson.gz"))
    parser.add_argument("--out", type=Path, default=Path("output/30476/dump.db"))
    args = parser.parse_args(argv)

    if not args.input.exists():
        print("Input file not found:", args.input)
        return 2
    inserted = ingest_laps(args.input, args.out)
    print(f"Inserted {inserted} rows into {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
