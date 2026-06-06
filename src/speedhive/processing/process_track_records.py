"""Extract track-record announcements from SQLite database to JSON."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from speedhive.processing.process_lap_analysis import extract_iso_date, parse_track_record_text
from speedhive.storage import SpeedhiveStorage


def default_db_path() -> Path:
    return Path(os.environ.get("SPEEDHIVE_DB_PATH", "./web_data/speedhive.db"))


def extract_records_from_storage(org: int, db_path: Path, classification: str | None = None) -> List[Dict[str, Any]]:
    storage = SpeedhiveStorage(db_path)
    if not storage.org_has_sessions(org):
        return []

    session_map = storage.load_session_payloads(org)
    event_map = storage.load_event_payloads(org)
    announcements_map = storage.load_announcements_payloads(org)

    records: List[Dict[str, Any]] = []
    wanted_class = classification.upper() if classification else None

    for session_id, announcements in announcements_map.items():
        session_raw = session_map.get(session_id, {})
        event_id = (
            session_raw.get("event_id")
            or session_raw.get("eventId")
            or (session_raw.get("event") or {}).get("id")
        )
        event_key = str(int(event_id)) if event_id not in (None, "") else None
        event_raw = event_map.get(event_key or "", {})
        event_name = (
            (event_raw or {}).get("name")
            or (session_raw.get("event") or {}).get("name")
            or session_raw.get("event_name")
            or session_raw.get("eventName")
        )
        session_name = session_raw.get("name") or session_raw.get("sessionName")

        for announcement in announcements:
            if not isinstance(announcement, dict):
                continue
            text = announcement.get("text") or announcement.get("message") or ""
            parsed = parse_track_record_text(text)
            if not parsed:
                continue
            class_name = (parsed.get("classification") or "Unknown").upper()
            if wanted_class and class_name != wanted_class:
                continue
            timestamp = (
                announcement.get("timestamp")
                or announcement.get("time")
                or extract_iso_date(session_raw)
                or extract_iso_date(event_raw)
            )
            records.append(
                {
                    "event_id": int(event_id) if event_id not in (None, "") else None,
                    "event_name": event_name,
                    "session_id": int(session_id),
                    "session_name": session_name,
                    "classification": parsed.get("classification"),
                    "lap_time": parsed.get("lap_time"),
                    "lap_time_seconds": parsed.get("lap_time_seconds"),
                    "driver": parsed.get("driver"),
                    "marque": parsed.get("marque"),
                    "timestamp": timestamp,
                    "text": text,
                }
            )

    records.sort(key=lambda row: ((row.get("classification") or "").upper(), row.get("lap_time_seconds") or float("inf")))
    return records


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
    parser = argparse.ArgumentParser(description="Extract track records from the primary SQLite cache to JSON")
    parser.add_argument("--org", type=int, required=True)
    parser.add_argument("--classification", default=None)
    parser.add_argument("--dump-dir", type=Path, default=Path("./output"), help="Legacy offline dump root used only when the DB has no org data")
    parser.add_argument("--db-path", type=Path, default=default_db_path())
    parser.add_argument("--output", default=None, help="Output file path (JSON)")
    args = parser.parse_args(argv)

    if args.db_path.exists():
        records = extract_records_from_storage(args.org, args.db_path, args.classification)
        if not records:
            records = extract_records(args.org, args.dump_dir, args.classification)
    else:
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
