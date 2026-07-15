"""Export lap records for an organization from the primary SQLite cache to NDJSON."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from speedhive.ndjson import write_ndjson_record
from speedhive.storage import SpeedhiveStorage


def default_db_path() -> Path:
    return Path(os.environ.get("SPEEDHIVE_DB_PATH", "./web_data/speedhive.db"))


def get_lap_records(
    storage: SpeedhiveStorage,
    org_id: int,
    max_events: Optional[int] = None,
) -> Iterator[Dict[str, Any]]:
    """Generate lap records for the given organization from the SQLite database."""
    events_rec = storage.get_events(org_id)
    events = events_rec.payload if isinstance(events_rec.payload, list) else []

    if max_events is not None:
        events = events[:max_events]

    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = event.get("id")
        if not event_id:
            continue
        event_name = event.get("name")
        base_event = {"org_id": org_id, "event_id": event_id, "event_name": event_name}

        sessions_rec = storage.get_event_sessions(int(event_id))
        sessions = sessions_rec.payload if isinstance(sessions_rec.payload, list) else []
        for session in sessions:
            if not isinstance(session, dict) or not session.get("id"):
                continue
            sid = int(session["id"])
            laps_rec = storage.get_laps(sid)
            laps = laps_rec.payload if isinstance(laps_rec.payload, list) else []
            yield {**base_event, "session_id": sid, "rows_count": len(laps), "rows": laps}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export lap records to NDJSON")
    parser.add_argument("--org", type=int, required=True, help="Organization ID")
    parser.add_argument("--max-events", type=int, default=25, help="Maximum number of events to export")
    parser.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    parser.add_argument("--output", "-o", default=None, help="Output NDJSON file path (default: stdout)")
    args = parser.parse_args(argv)

    if not args.db_path.exists():
        print(f"Database cache does not exist at: {args.db_path}", file=sys.stderr)
        return 1

    storage = SpeedhiveStorage(args.db_path)

    # If output file is provided, open it, else print to stdout
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for record in get_lap_records(storage, args.org, args.max_events):
                write_ndjson_record(f, record)
        print(f"Wrote lap records to {out_path}", file=sys.stderr)
    else:
        for record in get_lap_records(storage, args.org, args.max_events):
            write_ndjson_record(sys.stdout, record)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
