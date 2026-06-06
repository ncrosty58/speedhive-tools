"""Stream `announcements.ndjson.gz` and write a flattened CSV of announcements.

The announcements payloads vary (sometimes a list, sometimes `rows` inside).
This script normalizes common shapes and writes a CSV for simple analysis.

Usage:
  python examples/processing/extract_announcements_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/announcements_flat.csv
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List
from collections import defaultdict


def _iter_announcements(rec: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    # rec often contains event_id/session_id and either `rows` or a list of announcements
    if not rec:
        return []
    if isinstance(rec, list):
        return rec
    # some exporters wrap announcements under an `announcements` key
    if rec.get("announcements"):
        a = rec.get("announcements")
        if isinstance(a, list):
            return a
        if isinstance(a, dict) and isinstance(a.get("rows"), list):
            return a.get("rows")
    if rec.get("rows"):
        return rec.get("rows")
    # fallback: maybe the announcements are the record itself
    if rec.get("announcement"):
        return [rec.get("announcement")]
    return []


def normalize_announcement(a: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": a.get("text") or a.get("message") or a.get("body"),
        "ts": a.get("time") or a.get("timestamp") or a.get("ts"),
        "raw": a,
    }


def extract(in_path: Path, out_path: Path) -> int:
    in_path = in_path.expanduser()
    out_path = out_path.expanduser()
    with gzip.open(in_path, "rt", encoding="utf8") as inf, out_path.open("w", encoding="utf8", newline="") as outf:
        fieldnames = ["event_id", "session_id", "ts", "text"]
        writer = csv.DictWriter(outf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        count = 0
        by_event: Dict[str, int] = defaultdict(int)
        by_session: Dict[str, int] = defaultdict(int)
        for line in inf:
            if not line.strip():
                continue
            rec: Dict[str, Any] = json.loads(line)
            for a in _iter_announcements(rec):
                n = normalize_announcement(a)
                writer.writerow({
                    "event_id": rec.get("event_id") or rec.get("eventId"),
                    "session_id": rec.get("session_id") or rec.get("sessionId"),
                    "ts": n.get("ts"),
                    "text": n.get("text"),
                })
                count += 1
                # update summary counters
                ev = rec.get("event_id") or rec.get("eventId")
                sid = rec.get("session_id") or rec.get("sessionId")
                if ev is not None:
                    by_event[str(ev)] += 1
                if sid is not None:
                    by_session[str(sid)] += 1
    # write a small JSON summary next to the CSV output
    try:
        summary = {
            "total": count,
            "by_event": dict(by_event),
            "by_session": dict(by_session),
        }
        summary_path = out_path.parent / "announcements_summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf8")
        print(f"Wrote summary to {summary_path}")
    except Exception as exc:
        print("Failed to write summary:", exc)

    return count


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Extract announcements NDJSON -> CSV")
    p.add_argument("--input", type=Path, default=Path("output/30476"), help="Input directory containing announcements.ndjson.gz")
    p.add_argument("--in-file", type=Path, default=Path("announcements.ndjson.gz"), help="Input NDJSON filename (gzipped)")
    p.add_argument("--out", type=Path, default=Path("output/30476/announcements_flat.csv"), help="Output CSV file")
    args = p.parse_args(argv)

    in_path = args.input / args.in_file
    if not in_path.exists():
        print("Input file not found:", in_path)
        return 2

    out_path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = extract(in_path, out_path)
    print(f"Wrote {count} announcements to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
