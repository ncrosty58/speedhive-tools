"""Extract track-record announcements from SQLite database to JSON."""
from __future__ import annotations

import argparse
import json
import os
import sys
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extract track records from the primary SQLite cache to NDJSON")
    parser.add_argument("--org", type=int, required=True)
    parser.add_argument("--classification", default=None)
    parser.add_argument("--db-path", type=Path, default=default_db_path())
    parser.add_argument("--output", default=None, help="Output file path (NDJSON)")
    args = parser.parse_args(argv)

    if not args.db_path.exists():
        print(f"Error: Database file does not exist at '{args.db_path}'. Please sync or import first.", file=sys.stderr)
        return 1

    records = extract_records_from_storage(args.org, args.db_path, args.classification)

    # NDJSON, matching the other row-shaped exports: a {"_meta": {...}} first
    # line for document-level fields, then one record per line.
    meta = {
        "org_id": args.org,
        "classification": args.classification,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    lines = [json.dumps({"_meta": meta}, ensure_ascii=False)]
    lines.extend(json.dumps(record, ensure_ascii=False) for record in records)
    body = "\n".join(lines) + "\n"
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(body, encoding="utf8")
        print(f"Wrote {out_path} ({len(records)} records)")
    else:
        sys.stdout.write(body)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
