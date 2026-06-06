"""Extract track-record announcements from an offline organization dump to JSON."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from speedhive.processing.lap_analysis import load_session_map, parse_track_record_text
from speedhive.processing.ndjson import open_ndjson


def extract_records(org: int, dump_dir: Path, classification: str | None = None) -> List[Dict[str, Any]]:
    """Return parsed track record rows from offline announcements dump."""
    dump = dump_dir / str(org)
    if not dump.exists():
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
                event_id_int = int(event_id)
            except Exception:
                continue
            event_names[event_id_int] = event.get("event_name") or (event.get("raw") or {}).get("name") or ""

    session_map = load_session_map(dump_dir, org)
    anns_path = dump / "announcements.ndjson.gz"
    if not anns_path.exists():
        anns_path = dump / "announcements.ndjson"
    if not anns_path.exists():
        return []

    desired_class = classification.upper() if classification else None
    rows: List[Dict[str, Any]] = []
    for obj in open_ndjson(anns_path):
        event_id = obj.get("event_id") or obj.get("eventId") or (obj.get("raw") or {}).get("event_id") or (obj.get("raw") or {}).get("eventId")
        event_name = None
        try:
            if event_id is not None:
                event_name = event_names.get(int(event_id))
        except Exception:
            event_name = None
        if not event_name:
            event_name = obj.get("event_name")

        session_id = obj.get("session_id") or obj.get("sessionId") or (obj.get("raw") or {}).get("id")
        session_name = None
        try:
            if session_id is not None:
                session_name = (session_map.get(str(int(session_id))) or {}).get("name")
        except Exception:
            session_name = None

        announcements = obj.get("announcements") or obj.get("rows") or obj.get("announcement") or []
        if isinstance(announcements, dict):
            if isinstance(announcements.get("announcements"), list):
                announcements = announcements["announcements"]
            elif isinstance(announcements.get("rows"), list):
                announcements = announcements["rows"]
            else:
                announcements = []
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
            class_name = parsed.get("classification")
            if desired_class and str(class_name or "").upper() != desired_class:
                continue
            rows.append(
                {
                    "event_id": event_id,
                    "event_name": event_name,
                    "session_id": session_id,
                    "session_name": session_name,
                    "classification": class_name,
                    "lap_time": parsed.get("lap_time"),
                    "lap_time_seconds": parsed.get("lap_time_seconds"),
                    "driver": parsed.get("driver"),
                    "marque": parsed.get("marque"),
                    "timestamp": timestamp,
                    "text": text,
                }
            )

    rows.sort(key=lambda row: ((row.get("classification") or ""), row.get("lap_time_seconds") or float("inf")))
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extract track records from offline announcements dump to JSON")
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
