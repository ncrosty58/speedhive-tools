#!/usr/bin/env python3
"""Extract track records from exported announcements and write CSV.

Scans `output/<org>/announcements.ndjson[.gz]` and extracts announcements
that match "New Track Record" or "New Class Record" patterns and writes
results to `out_dir/track_records_<org>.csv`.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Any

from speedhive_tools.utils.common import open_ndjson, load_session_map
from speedhive_tools.utils.track_records import parse_track_record_text


def _parse_ann_text(text: str):
    return parse_track_record_text(text)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Extract track records from exported announcements into CSV")
    p.add_argument("--org", type=int, required=True)
    p.add_argument("--dump-dir", type=Path, default=Path("./output"), help="Directory containing exported dumps")
    p.add_argument("--out-dir", type=Path, default=Path("./output"), help="Where to write CSV output")
    args = p.parse_args(argv)

    dump = Path(args.dump_dir) / str(args.org)
    if not dump.exists():
        print(f"Dump directory {dump} not found")
        return 2

    # load events for names
    events_path = dump / "events.ndjson.gz"
    if not events_path.exists():
        events_path = dump / "events.ndjson"
    event_names: dict[int, str] = {}
    if events_path.exists():
        for ev in open_ndjson(events_path):
            eid = ev.get("event_id") or ev.get("eventId") or (ev.get("raw") or {}).get("id")
            if eid is None:
                continue
            try:
                eid_i = int(eid)
            except Exception:
                continue
            event_names[eid_i] = ev.get("event_name") or (ev.get("raw") or {}).get("name") or ""

    session_map = load_session_map(Path(args.dump_dir), args.org)

    anns_path = dump / "announcements.ndjson.gz"
    if not anns_path.exists():
        anns_path = dump / "announcements.ndjson"

    if not anns_path.exists():
        print(f"No announcements file found under {dump}")
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"track_records_{args.org}.csv"

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

    with open(out_file, "w", encoding="utf8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()

        for obj in open_ndjson(anns_path):
            eid = obj.get("event_id") or obj.get("eventId") or (obj.get("raw") or {}).get("event_id") or (obj.get("raw") or {}).get("eventId")
            try:
                eid_i = int(eid) if eid is not None else None
            except Exception:
                eid_i = None

            ev_name = event_names.get(eid_i) if eid_i is not None else obj.get("event_name") or None

            # announcements may be string, list, or object containing announcements
            anns = obj.get("announcements") or obj.get("rows") or obj.get("announcement") or []
            # some exporters put announcements under a mapping like {"rows": [...]}
            if isinstance(anns, dict):
                if "announcements" in anns:
                    anns = anns.get("announcements")
                elif "rows" in anns:
                    anns = anns.get("rows")
            if isinstance(anns, str):
                anns = [anns]
            if not isinstance(anns, list):
                continue

            session_id = obj.get("session_id") or obj.get("sessionId") or (obj.get("raw") or {}).get("id")
            sid_str = str(int(session_id)) if session_id is not None else None
            session_name = None
            if sid_str and sid_str in session_map:
                session_name = session_map[sid_str].get("name") if isinstance(session_map[sid_str], dict) else None

            for ann in anns:
                if isinstance(ann, dict):
                    text = ann.get("text") or ann.get("message") or ""
                    timestamp = ann.get("timestamp") or ann.get("time")
                else:
                    text = str(ann)
                    timestamp = None

                parsed = _parse_ann_text(text)
                if not parsed:
                    continue

                row: dict[str, Any] = {
                    "event_id": eid_i,
                    "event_name": ev_name,
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
                writer.writerow(row)

    print(f"Wrote {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
