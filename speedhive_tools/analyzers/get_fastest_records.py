#!/usr/bin/env python3
"""Get the fastest track record for each classification.

This script shows how to query track records and identify the current
(fastest) record for each classification in an organization.

Usage:
  python examples/get_fastest_records.py --org 30476
  python examples/get_fastest_records.py --org 30476 --classification IT7
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from collections import defaultdict

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from speedhive_tools.utils.common import open_ndjson, load_session_map, parse_time_value


def _parse_lap_time(lap_time_str: str):
    # reuse common parser semantics
    return parse_time_value(lap_time_str)


def _find_records_in_announcements(obj, event_name, session_map):
    """Yield record dicts found in a single announcements NDJSON object."""
    anns = obj.get("announcements") or obj.get("rows") or obj.get("announcement") or []
    # some exporters put announcements as a mapping under a top-level key
    if isinstance(anns, dict) and "announcements" in anns:
        anns = anns.get("announcements")
    if not isinstance(anns, list):
        return

    session_id = obj.get("session_id") or obj.get("sessionId") or (obj.get("raw") or {}).get("id")
    sid_str = str(int(session_id)) if session_id is not None else None
    session_name = None
    if sid_str and sid_str in session_map:
        session_name = session_map[sid_str].get("name") if isinstance(session_map[sid_str], dict) else None

    import re
    pattern = re.compile(r"New (?:Track|Class) Record\s*\(([0-9:.]+)\)\s*for\s+([^\s]+)\s+by\s+(.+?)\.?$", re.IGNORECASE)

    for ann in anns:
        # announcement may be string or object
        if isinstance(ann, str):
            text = ann
            timestamp = None
        elif isinstance(ann, dict):
            text = ann.get("text") or ann.get("message") or ann.get("announcement") or ""
            timestamp = ann.get("timestamp") or ann.get("time")
        else:
            text = str(ann)
            timestamp = None

        if not text:
            continue

        m = pattern.search(text)
        if not m:
            continue

        lap_time_str = m.group(1)
        class_name = m.group(2)
        driver_block = m.group(3).strip()

        # skip provisional/ambiguous announcements
        low = text.lower()
        if "to be confirmed" in low or "not a track record" in low or "not a class record" in low:
            continue

        marque = None
        mm = re.search(r"^(.+?)\s+in\s+(.+)$", driver_block, flags=re.IGNORECASE)
        if mm:
            driver_name = mm.group(1).strip()
            marque = mm.group(2).strip().rstrip('.')
        else:
            driver_name = driver_block

        # strip competitor index like [25]
        driver_name = re.sub(r"^\s*\[\s*\d+\s*\]\s*", "", driver_name)

        lap_seconds = _parse_lap_time(lap_time_str)

        yield {
            "event_id": obj.get("event_id") or obj.get("eventId") or obj.get("raw", {}).get("event_id") or obj.get("raw", {}).get("eventId"),
            "event_name": event_name,
            "session_id": session_id,
            "session_name": session_name,
            "classification": class_name,
            "lap_time": lap_time_str,
            "lap_time_seconds": lap_seconds,
            "driver": driver_name,
            "marque": marque,
            "timestamp": timestamp,
            "text": text,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Get fastest track records from exported data")
    parser.add_argument("--org", type=int, required=True, help="Organization ID")
    parser.add_argument("--classification", help="Get fastest record for specific classification")
    parser.add_argument("--limit-events", type=int, help="Limit number of events to scan")
    parser.add_argument("--dump-dir", type=Path, default=Path("./output"), help="Output dump directory (default ./output)")
    args = parser.parse_args(argv)

    dump = Path(args.dump_dir) / str(args.org)
    if not dump.exists():
        print(f"Dump directory {dump} not found")
        return 2

    # load events in order so limit-events is meaningful
    events_path = dump / "events.ndjson.gz"
    if not events_path.exists():
        events_path = dump / "events.ndjson"
    event_order = []
    event_names = {}
    if events_path.exists():
        for ev in open_ndjson(events_path):
            eid = ev.get("event_id") or ev.get("eventId") or (ev.get("raw") or {}).get("id")
            if eid is None:
                continue
            eid = int(eid)
            event_order.append(eid)
            event_names[eid] = ev.get("event_name") or (ev.get("raw") or {}).get("name")

    if args.limit_events:
        allowed_events = set(event_order[: args.limit_events])
    else:
        allowed_events = set(event_order) if event_order else None

    # load session map for friendly names
    session_map = load_session_map(Path(args.dump_dir), args.org)

    # find announcements file
    anns_path = dump / "announcements.ndjson.gz"
    if not anns_path.exists():
        anns_path = dump / "announcements.ndjson"

    if not anns_path.exists():
        print(f"No announcements file found under {dump}")
        return 1

    records = []
    for obj in open_ndjson(anns_path):
        # determine event id for this object
        eid = obj.get("event_id") or obj.get("eventId") or (obj.get("raw") or {}).get("event_id") or (obj.get("raw") or {}).get("eventId")
        if eid is None:
            # try to infer from base_event keys used by exporter
            eid = obj.get("event", {}).get("id") if isinstance(obj.get("event"), dict) else None
        try:
            eid_int = int(eid) if eid is not None else None
        except Exception:
            eid_int = None

        if allowed_events is not None and eid_int is not None and eid_int not in allowed_events:
            continue

        ev_name = None
        if eid_int is not None and eid_int in event_names:
            ev_name = event_names[eid_int]
        elif obj.get("event_name"):
            ev_name = obj.get("event_name")

        for rec in _find_records_in_announcements(obj, ev_name, session_map):
            cls = (rec.get("classification") or "")
            if args.classification and cls.upper() != args.classification.upper():
                continue
            records.append(rec)

    if not records:
        print("No track records found in exported data")
        return 1

    # group by classification and keep fastest
    fastest_by_class = {}
    for r in records:
        cls = r.get("classification")
        if not cls:
            continue
        prev = fastest_by_class.get(cls)
        if prev is None or (r.get("lap_time_seconds") is not None and (prev.get("lap_time_seconds") is None or r.get("lap_time_seconds") < prev.get("lap_time_seconds"))):
            fastest_by_class[cls] = r

    if args.classification:
        # match classification case-insensitively
        target = None
        for k, v in fastest_by_class.items():
            if k and k.upper() == args.classification.upper():
                target = v
                break
        if not target:
            print(f"No track records found for {args.classification}")
            return 1
        rec = target
        print(f"Fastest {rec['classification']} Track Record:")
        print(f"  Time: {rec['lap_time']}")
        print(f"  Driver: {rec['driver']}")
        if rec.get("marque"):
            print(f"  Marque: {rec.get('marque')}")
        print(f"  Event: {rec.get('event_name')}")
        print(f"  Session: {rec.get('session_name')}")
        print(f"  Date: {rec.get('timestamp')}")
        return 0

    print(f"\nFastest Track Records ({len(fastest_by_class)} classifications):")
    print("-" * 80)
    for class_name in sorted(fastest_by_class.keys()):
        record = fastest_by_class[class_name]
        marque = record.get("marque") or ""
        evn = (record.get("event_name") or "")
        print(f"{class_name:10s} {record['lap_time']:>10s}  {record['driver']:30s}  {marque:15s}  {evn[:40]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
