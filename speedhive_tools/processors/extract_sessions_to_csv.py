"""Stream `sessions.ndjson.gz` and write a flattened CSV of sessions.

This handles common variants (sessions nested under `groups`, `sessions: null`,
and various field-name variants). It's memory-friendly and intended to run on
the export output directory produced by `examples/export_full_dump.py`.

Usage:
  python examples/processing/extract_sessions_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/sessions_flat.csv
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _iter_sessions(rec: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    # common places where sessions live
    if not rec:
        return []
    if rec.get("sessions"):
        return rec.get("sessions")
    if rec.get("groups"):
        # groups -> sessions inside each group
        out: List[Dict[str, Any]] = []
        for g in rec.get("groups") or []:
            for s in (g.get("sessions") or []):
                out.append(s)
        return out
    return []


def normalize_session(s: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "event_id": s.get("event_id") or s.get("eventId") or s.get("event"),
        "session_id": s.get("id") or s.get("sessionId") or s.get("session_id"),
        "name": s.get("name") or s.get("sessionName") or s.get("title"),
        "start_time": s.get("startTime") or s.get("start_time") or s.get("begin"),
        "end_time": s.get("endTime") or s.get("end_time"),
        "raw": s,
    }


def extract(in_path: Path, out_path: Path) -> int:
    in_path = in_path.expanduser()
    out_path = out_path.expanduser()
    with gzip.open(in_path, "rt", encoding="utf8") as inf, out_path.open("w", encoding="utf8", newline="") as outf:
        fieldnames = ["event_id", "session_id", "name", "start_time", "end_time"]
        writer = csv.DictWriter(outf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        count = 0
        for line in inf:
            if not line.strip():
                continue
            rec: Dict[str, Any] = json.loads(line)
            for s in _iter_sessions(rec):
                n = normalize_session(s)
                writer.writerow({
                    "event_id": rec.get("event_id") or rec.get("eventId") or n.get("event_id"),
                    "session_id": n.get("session_id"),
                    "name": n.get("name"),
                    "start_time": n.get("start_time"),
                    "end_time": n.get("end_time"),
                })
                count += 1
    return count


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Extract sessions NDJSON -> CSV")
    p.add_argument("--input", type=Path, default=Path("output/30476"), help="Input directory containing sessions.ndjson.gz")
    p.add_argument("--in-file", type=Path, default=Path("sessions.ndjson.gz"), help="Input NDJSON filename (gzipped)")
    p.add_argument("--out", type=Path, default=Path("output/30476/sessions_flat.csv"), help="Output CSV file")
    args = p.parse_args(argv)

    in_path = args.input / args.in_file
    if not in_path.exists():
        print("Input file not found:", in_path)
        return 2

    out_path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = extract(in_path, out_path)
    print(f"Wrote {count} sessions to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
