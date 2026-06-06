"""Extract track-record announcements from offline dump and write CSV."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, List

from speedhive.processing.lap_analysis import load_session_map, parse_track_record_text
from speedhive.processing.ndjson import open_ndjson


def extract_rows(org: int, dump_dir: Path) -> List[Dict[str, Any]]:
    """Read announcements dump and return parsed track-record rows."""
    dump = dump_dir / str(org)
    anns_path = dump / "announcements.ndjson.gz"
    if not anns_path.exists():
        anns_path = dump / "announcements.ndjson"
    if not anns_path.exists():
        return []

    events_path = dump / "events.ndjson.gz"
    if not events_path.exists():
        events_path = dump / "events.ndjson"
    event_names: Dict[int, str] = {}
    if events_path.exists():
        for event in open_ndjson(events_path):
            event_id = event.get("event_id") or event.get("eventId") or (event.get("raw") or {}).get("id")
            if event_id is None:
                continue
            try:
                event_names[int(event_id)] = event.get("event_name") or (event.get("raw") or {}).get("name") or ""
            except Exception:
                continue

    session_map = load_session_map(dump_dir, org)
    rows: List[Dict[str, Any]] = []
    for obj in open_ndjson(anns_path):
        event_id = obj.get("event_id") or obj.get("eventId")
        try:
            event_name = event_names.get(int(event_id)) if event_id is not None else obj.get("event_name")
        except Exception:
            event_name = obj.get("event_name")

        session_id = obj.get("session_id") or obj.get("sessionId")
        session_name = None
        try:
            if session_id is not None:
                session_name = (session_map.get(str(int(session_id))) or {}).get("name")
        except Exception:
            session_name = None

        announcements = obj.get("announcements") or obj.get("rows") or obj.get("announcement") or []
        if isinstance(announcements, dict):
            announcements = announcements.get("announcements") or announcements.get("rows") or []
        if isinstance(announcements, str):
            announcements = [announcements]
        if not isinstance(announcements, list):
            continue

        for ann in announcements:
            if isinstance(ann, dict):
                text = ann.get("text") or ann.get("message") or ""
                timestamp = ann.get("timestamp") or ann.get("time")
            else:
                text = str(ann)
                timestamp = None
            parsed = parse_track_record_text(text)
            if not parsed:
                continue
            rows.append(
                {
                    "event_id": event_id,
                    "event_name": event_name,
                    "session_id": session_id,
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
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extract track records from announcements dump into CSV")
    parser.add_argument("--org", type=int, required=True)
    parser.add_argument("--dump-dir", type=Path, default=Path("./output"))
    parser.add_argument("--out-dir", type=Path, default=Path("./output"))
    args = parser.parse_args(argv)

    rows = extract_rows(args.org, args.dump_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_file = args.out_dir / f"track_records_{args.org}.csv"
    headers = [
        "event_id",
        "event_name",
        "session_id",
        "session_name",
        "classification",
        "lap_time",
        "lap_time_seconds",
        "driver",
        "marque",
        "timestamp",
        "text",
    ]
    with out_file.open("w", encoding="utf8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
