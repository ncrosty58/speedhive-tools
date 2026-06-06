"""Extract sessions NDJSON to flat CSV."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


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


def extract(in_path: Path, out_path: Path) -> int:
    """Write flat sessions CSV from sessions NDJSON(.gz)."""
    fieldnames = ["event_id", "session_id", "name", "start_time", "end_time"]
    count = 0
    opener = gzip.open if (in_path.suffix == ".gz" or in_path.name.endswith(".gz")) else open
    with opener(in_path, "rt", encoding="utf8") as in_fh, out_path.open("w", encoding="utf8", newline="") as out_fh:
        writer = csv.DictWriter(out_fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for line in in_fh:
            if not line.strip():
                continue
            record = json.loads(line)
            for session in _iter_sessions(record):
                normalized = normalize_session(session)
                writer.writerow(
                    {
                        "event_id": record.get("event_id") or record.get("eventId") or normalized.get("event_id"),
                        "session_id": normalized.get("session_id"),
                        "name": normalized.get("name"),
                        "start_time": normalized.get("start_time"),
                        "end_time": normalized.get("end_time"),
                    }
                )
                count += 1
    return count


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extract sessions NDJSON -> CSV")
    parser.add_argument("--input", type=Path, default=Path("output/30476"))
    parser.add_argument("--in-file", type=Path, default=Path("sessions.ndjson.gz"))
    parser.add_argument("--out", type=Path, default=Path("output/30476/sessions_flat.csv"))
    args = parser.parse_args(argv)

    in_path = args.input / args.in_file
    if not in_path.exists():
        print("Input file not found:", in_path)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    count = extract(in_path, args.out)
    print(f"Wrote {count} sessions to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
