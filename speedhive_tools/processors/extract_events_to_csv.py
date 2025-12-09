"""Stream `events.ndjson.gz` and write a flattened CSV of events.

This is a memory-friendly extractor intended to run on the export output
directory produced by `examples/export_full_dump.py`.

Usage:
  python examples/processing/extract_events_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/events_flat.csv
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import Any, Dict


def normalize_event(e: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize event field names from various API response formats."""
    org = e.get("organization", {}) or {}
    return {
        "event_id": e.get("id") or e.get("eventId") or e.get("event_id"),
        "name": e.get("name") or e.get("eventName") or e.get("title"),
        "date": e.get("date") or e.get("startDate") or e.get("start_date"),
        "end_date": e.get("endDate") or e.get("end_date"),
        "organization_id": org.get("id") or e.get("organizationId") or e.get("organization_id"),
        "organization_name": org.get("name") or e.get("organizationName"),
        "location": e.get("location") or e.get("venue"),
        "country": e.get("country") or org.get("country"),
    }


def extract(in_path: Path, out_path: Path) -> int:
    """Extract events from NDJSON to CSV."""
    in_path = in_path.expanduser()
    out_path = out_path.expanduser()

    fieldnames = ["event_id", "name", "date", "end_date", "organization_id", "organization_name", "location", "country"]

    with gzip.open(in_path, "rt", encoding="utf8") as inf, out_path.open("w", encoding="utf8", newline="") as outf:
        writer = csv.DictWriter(outf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        count = 0

        for line in inf:
            if not line.strip():
                continue

            rec = json.loads(line)
            normalized = normalize_event(rec)
            writer.writerow(normalized)
            count += 1

    return count


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Extract events NDJSON -> CSV")
    p.add_argument("--input", type=Path, default=Path("output/30476"), help="Input directory containing events.ndjson.gz")
    p.add_argument("--in-file", type=Path, default=Path("events.ndjson.gz"), help="Input NDJSON filename (gzipped)")
    p.add_argument("--out", type=Path, default=Path("output/30476/events_flat.csv"), help="Output CSV file")
    args = p.parse_args(argv)

    in_path = args.input / args.in_file
    if not in_path.exists():
        print("Input file not found:", in_path)
        return 2

    out_path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = extract(in_path, out_path)
    print(f"Wrote {count} events to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
