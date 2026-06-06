"""Stream announcements.ndjson(.gz) from an offline dump and write a flattened CSV."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

from speedhive.processing.ndjson import open_ndjson


def _iter_announcements(rec: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    if not rec:
        return []
    if isinstance(rec, list):
        return rec
    if rec.get("announcements"):
        a = rec.get("announcements")
        if isinstance(a, list):
            return a
        if isinstance(a, dict) and isinstance(a.get("rows"), list):
            return a.get("rows")
    if rec.get("rows"):
        return rec.get("rows")
    if rec.get("announcement"):
        return [rec.get("announcement")]
    return []


def normalize_announcement(a: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": a.get("text") or a.get("message") or a.get("body"),
        "ts": a.get("time") or a.get("timestamp") or a.get("ts"),
    }


_FIELDS = ["event_id", "session_id", "ts", "text"]


def extract(in_path: Path, out_path: Path) -> int:
    """Extract announcements from NDJSON(.gz) to CSV. Returns row count."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    by_event: Dict[str, int] = defaultdict(int)
    by_session: Dict[str, int] = defaultdict(int)
    with out_path.open("w", encoding="utf8", newline="") as outf:
        writer = csv.DictWriter(outf, fieldnames=_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for rec in open_ndjson(in_path):
            event_id = rec.get("event_id") or rec.get("eventId")
            session_id = rec.get("session_id") or rec.get("sessionId")
            for a in _iter_announcements(rec):
                n = normalize_announcement(a)
                writer.writerow({
                    "event_id": event_id,
                    "session_id": session_id,
                    "ts": n.get("ts"),
                    "text": n.get("text"),
                })
                count += 1
                if event_id is not None:
                    by_event[str(event_id)] += 1
                if session_id is not None:
                    by_session[str(session_id)] += 1

    summary_path = out_path.parent / "announcements_summary.json"
    try:
        summary_path.write_text(
            json.dumps({"total": count, "by_event": dict(by_event), "by_session": dict(by_session)},
                       ensure_ascii=False, indent=2),
            encoding="utf8",
        )
        print(f"Wrote summary to {summary_path}")
    except Exception as exc:
        print("Failed to write summary:", exc)

    return count


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Extract announcements NDJSON -> flat CSV")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--dump-dir", type=Path, default=Path("./output"), help="Root dump directory")
    p.add_argument("--out-dir", type=Path, default=None, help="Output directory (defaults to dump-dir/<org>/)")
    args = p.parse_args(argv)

    dump = args.dump_dir / str(args.org)
    in_path = dump / "announcements.ndjson.gz"
    if not in_path.exists():
        in_path = dump / "announcements.ndjson"
    if not in_path.exists():
        print("Input file not found:", in_path)
        return 2

    out_dir = args.out_dir or dump
    out_path = out_dir / "announcements_flat.csv"
    count = extract(in_path, out_path)
    print(f"Wrote {count} announcements to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
