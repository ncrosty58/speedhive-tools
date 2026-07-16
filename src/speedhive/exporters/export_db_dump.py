"""Export an offline NDJSON dump of an organization from the primary SQLite cache."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from speedhive.ndjson import write_ndjson_record
from speedhive.storage import SpeedhiveStorage


def default_db_path() -> Path:
    db_path = os.environ.get("SPEEDHIVE_DB_PATH")
    if db_path:
        return Path(db_path)
    data_dir = os.environ.get("SPEEDHIVE_DATA_DIR", "./data")
    return Path(data_dir) / "speedhive.db"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

def export_db_dump(
    storage: SpeedhiveStorage,
    org_id: int,
    output_dir: Path,
    max_events: Optional[int] = None,
) -> Dict[str, Any]:
    """Export SQLite database cache contents to NDJSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    events_rec = storage.get_events(org_id)
    events = events_rec.payload if isinstance(events_rec.payload, list) else []
    if max_events is not None:
        events = events[:max_events]

    events_path = output_dir / "events.ndjson"
    sessions_path = output_dir / "sessions.ndjson"
    laps_path = output_dir / "laps.ndjson"
    anns_path = output_dir / "announcements.ndjson"
    results_path = output_dir / "results.ndjson"

    events_count = 0
    sessions_count = 0
    laps_records_count = 0

    with open(events_path, "w", encoding="utf-8") as events_fh, \
         open(sessions_path, "w", encoding="utf-8") as sessions_fh, \
         open(laps_path, "w", encoding="utf-8") as laps_fh, \
         open(anns_path, "w", encoding="utf-8") as anns_fh, \
         open(results_path, "w", encoding="utf-8") as results_fh:
        for event in events:
            if not isinstance(event, dict):
                continue
            event_id = event.get("id")
            if not event_id:
                continue
            event_name = event.get("name")
            base_event = {"org_id": org_id, "event_id": event_id, "event_name": event_name}
            write_ndjson_record(events_fh, {**base_event, "raw": event})
            events_count += 1

            sessions_rec = storage.get_event_sessions(int(event_id))
            sessions = sessions_rec.payload if isinstance(sessions_rec.payload, list) else []
            for session in sessions:
                if not isinstance(session, dict):
                    continue
                session_id = session.get("id")
                if not session_id:
                    continue
                session_id_int = int(session_id)
                write_ndjson_record(sessions_fh, {**base_event, "session_id": session_id_int, "raw": session})
                sessions_count += 1

                anns_rec = storage.get_announcements(session_id_int)
                announcements = anns_rec.payload if isinstance(anns_rec.payload, list) else []
                write_ndjson_record(anns_fh, {**base_event, "session_id": session_id_int, "announcements": announcements})

                results_rec = storage.get_results(session_id_int)
                results = results_rec.payload if isinstance(results_rec.payload, list) else []
                write_ndjson_record(results_fh, {**base_event, "session_id": session_id_int, "results": results})

                laps_rec = storage.get_laps(session_id_int)
                laps = laps_rec.payload if isinstance(laps_rec.payload, list) else []
                write_ndjson_record(laps_fh, {**base_event, "session_id": session_id_int, "rows_count": len(laps), "rows": laps})
                laps_records_count += 1

    manifest = {
        "org_id": org_id,
        "saved_at": _iso_utc(_utc_now()),
        "events_count": events_count,
        "sessions_count": sessions_count,
        "laps_records_count": laps_records_count,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"path": str(output_dir), **manifest}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export SQLite database cache contents to NDJSON files")
    parser.add_argument("--org", type=int, required=True, help="Organization ID")
    parser.add_argument("--db-path", type=Path, default=default_db_path(), help="Primary SQLite cache path")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory to save NDJSON files")
    parser.add_argument("--max-events", type=int, default=None, help="Maximum number of events to export")
    args = parser.parse_args(argv)

    if not args.db_path.exists():
        print(f"Database cache does not exist at: {args.db_path}", file=sys.stderr)
        return 1

    storage = SpeedhiveStorage(args.db_path)
    summary = export_db_dump(storage, args.org, args.output_dir, args.max_events)
    print(f"Exported dump to {summary['path']} ({summary['events_count']} events, {summary['sessions_count']} sessions)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
