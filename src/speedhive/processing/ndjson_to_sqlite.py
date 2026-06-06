"""Import laps NDJSON(.gz) from an offline dump into a lightweight SQLite table."""
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
    parser = argparse.ArgumentParser(description="Import laps NDJSON(.gz) from offline dump into SQLite")
    parser.add_argument("--org", type=int, required=True, help="Organization ID")
    parser.add_argument("--dump-dir", type=Path, default=Path("./output"), help="Root dump directory")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory for SQLite DB (defaults to dump-dir/<org>/)")
    args = parser.parse_args(argv)

    dump = args.dump_dir / str(args.org)
    in_path = dump / "laps.ndjson.gz"
    if not in_path.exists():
        in_path = dump / "laps.ndjson"
    if not in_path.exists():
        print("Input file not found:", in_path)
        return 2

    out_dir = args.out_dir or dump
    db_path = out_dir / f"laps_{args.org}.db"
    inserted = ingest_laps(in_path, db_path)
    print(f"Inserted {inserted} rows into {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
