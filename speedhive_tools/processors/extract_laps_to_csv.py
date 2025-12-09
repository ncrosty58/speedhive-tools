"""Stream `laps.ndjson.gz` and write a flattened CSV of lap rows.

This is a memory-friendly extractor intended to run on the export output
directory produced by `examples/export_full_dump.py`.

Usage examples:
  python examples/processing/extract_laps_to_csv.py --input output/full_dump/30476 --out output/full_dump/30476/laps_flat.csv

The script attempts to handle common field name variants found in lap row objects.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import Any, Dict


def normalize_row(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "competitor_id": r.get("competitorId") or r.get("competitor_id") or r.get("id") or r.get("competitor"),
        "lap_number": r.get("lapNumber") or r.get("lap_number") or r.get("lap"),
        "lap_time": r.get("lapTime") or r.get("lap_time") or r.get("time") or r.get("laptime"),
        "position": r.get("position") or r.get("pos"),
        "raw": r,
    }


def extract(in_path: Path, out_path: Path) -> int:
    in_path = in_path.expanduser()
    out_path = out_path.expanduser()
    with gzip.open(in_path, "rt", encoding="utf8") as inf, out_path.open("w", encoding="utf8", newline="") as outf:
        fieldnames = ["event_id", "session_id", "competitor_id", "lap_number", "lap_time", "position"]
        writer = csv.DictWriter(outf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        count = 0
        for line in inf:
            if not line.strip():
                continue
            rec = json.loads(line)
            rows = rec.get("rows") or rec.get("lapRows") or rec.get("laps") or []
            for r in rows:
                n = normalize_row(r)
                writer.writerow({
                    "event_id": rec.get("event_id") or rec.get("eventId") or rec.get("eventId"),
                    "session_id": rec.get("session_id") or rec.get("sessionId") or rec.get("sessionId"),
                    "competitor_id": n["competitor_id"],
                    "lap_number": n["lap_number"],
                    "lap_time": n["lap_time"],
                    "position": n.get("position"),
                })
                count += 1
    return count


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Extract lap rows NDJSON -> CSV")
    p.add_argument("--input", type=Path, default=Path("output/30476"), help="Input directory containing laps.ndjson.gz")
    p.add_argument("--in-file", type=Path, default=Path("laps.ndjson.gz"), help="Input NDJSON filename (gzipped)")
    p.add_argument("--out", type=Path, default=Path("output/30476/laps_flat.csv"), help="Output CSV file")
    args = p.parse_args(argv)

    in_path = args.input / args.in_file
    if not in_path.exists():
        print("Input file not found:", in_path)
        return 2

    out_path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = extract(in_path, out_path)
    print(f"Wrote {count} lap rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
