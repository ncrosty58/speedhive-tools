"""Stream sessions.ndjson(.gz) from an offline dump and write a flattened CSV."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List

from speedhive.processing.ndjson import open_ndjson


def _iter_sessions(record: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    if not record:
        return []
    if isinstance(record.get("sessions"), list):
        return record["sessions"]
    if isinstance(record.get("groups"), list):
        rows: List[Dict[str, Any]] = []
        for group in record["groups"]:
            if isinstance(group, dict) and isinstance(group.get("sessions"), list):
                rows.extend(group["sessions"])
        return rows
    return []


def normalize_session(session: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "event_id": session.get("event_id") or session.get("eventId") or session.get("event"),
        "session_id": session.get("id") or session.get("sessionId") or session.get("session_id"),
        "name": session.get("name") or session.get("sessionName") or session.get("title"),
        "start_time": session.get("startTime") or session.get("start_time") or session.get("begin"),
        "end_time": session.get("endTime") or session.get("end_time"),
    }


_FIELDS = ["event_id", "session_id", "name", "start_time", "end_time"]


def extract(in_path: Path, out_path: Path) -> int:
    """Write flat sessions CSV from sessions NDJSON(.gz). Returns row count."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf8", newline="") as out_fh:
        writer = csv.DictWriter(out_fh, fieldnames=_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for record in open_ndjson(in_path):
            for session in _iter_sessions(record):
                normalized = normalize_session(session)
                writer.writerow({
                    "event_id": record.get("event_id") or record.get("eventId") or normalized.get("event_id"),
                    "session_id": normalized.get("session_id"),
                    "name": normalized.get("name"),
                    "start_time": normalized.get("start_time"),
                    "end_time": normalized.get("end_time"),
                })
                count += 1
    return count


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extract sessions NDJSON -> flat CSV")
    parser.add_argument("--org", type=int, required=True, help="Organization ID")
    parser.add_argument("--dump-dir", type=Path, default=Path("./output"), help="Root dump directory")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory (defaults to dump-dir/<org>/)")
    args = parser.parse_args(argv)

    dump = args.dump_dir / str(args.org)
    in_path = dump / "sessions.ndjson.gz"
    if not in_path.exists():
        in_path = dump / "sessions.ndjson"
    if not in_path.exists():
        print("Input file not found:", in_path)
        return 2

    out_dir = args.out_dir or dump
    out_path = out_dir / "sessions_flat.csv"
    count = extract(in_path, out_path)
    print(f"Wrote {count} sessions to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
