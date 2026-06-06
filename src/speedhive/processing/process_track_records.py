"""Extract track-record announcements from SQLite database to JSON."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def extract_records(org: int, dump_dir: Path, classification: str | None = None) -> List[Dict[str, Any]]:
    """Return parsed track record rows from local SQLite database, auto-ingesting if missing."""
    db_path = dump_dir / str(org) / f"laps_{org}.db"
    if not db_path.exists():
        # Run the sqlite ingestion first to build the database
        from speedhive.processing.process_sqlite_import import main as sqlite_main
        sqlite_main(["--org", str(org), "--dump-dir", str(dump_dir)])

    # If it still doesn't exist (e.g. no dump files), return empty list
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        # Check if track_records table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='track_records'")
        if not cur.fetchone():
            # Try running ingestion to create the table
            from speedhive.processing.process_sqlite_import import main as sqlite_main
            sqlite_main(["--org", str(org), "--dump-dir", str(dump_dir)])
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='track_records'")
            if not cur.fetchone():
                return []

        query = """
            SELECT event_id, event_name, session_id, session_name, classification,
                   lap_time, lap_time_seconds, driver, marque, timestamp, text
            FROM track_records
        """
        params = []
        if classification:
            query += " WHERE UPPER(classification) = ?"
            params.append(classification.upper())

        query += " ORDER BY UPPER(classification) ASC, lap_time_seconds ASC"
        cur.execute(query, params)

        records = []
        for row in cur.fetchall():
            records.append({
                "event_id": row[0],
                "event_name": row[1],
                "session_id": row[2],
                "session_name": row[3],
                "classification": row[4],
                "lap_time": row[5],
                "lap_time_seconds": row[6],
                "driver": row[7],
                "marque": row[8],
                "timestamp": row[9],
                "text": row[10],
            })
        return records
    finally:
        conn.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extract track records from SQLite database to JSON")
    parser.add_argument("--org", type=int, required=True)
    parser.add_argument("--classification", default=None)
    parser.add_argument("--dump-dir", type=Path, default=Path("./output"))
    parser.add_argument("--output", default=None, help="Output file path (JSON)")
    args = parser.parse_args(argv)

    records = extract_records(args.org, args.dump_dir, args.classification)

    payload = {
        "org_id": args.org,
        "classification": args.classification,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "records": records,
    }
    body = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(body, encoding="utf8")
        print(f"Wrote {out_path} ({len(records)} records)")
    else:
        print(body)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
