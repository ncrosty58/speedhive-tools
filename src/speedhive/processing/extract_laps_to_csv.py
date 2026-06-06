"""Stream laps.ndjson(.gz) from an offline dump and write a flattened CSV of lap rows."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict

from speedhive.processing.ndjson import open_ndjson


def normalize_row(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "competitor_id": r.get("competitorId") or r.get("competitor_id") or r.get("id") or r.get("competitor"),
        "lap_number": r.get("lapNumber") or r.get("lap_number") or r.get("lap"),
        "lap_time": r.get("lapTime") or r.get("lap_time") or r.get("time") or r.get("laptime"),
        "position": r.get("position") or r.get("pos"),
    }


_FIELDS = ["event_id", "session_id", "competitor_id", "lap_number", "lap_time", "position"]


def extract(in_path: Path, out_path: Path) -> int:
    """Extract lap rows from NDJSON(.gz) to CSV. Returns row count."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf8", newline="") as outf:
        writer = csv.DictWriter(outf, fieldnames=_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for rec in open_ndjson(in_path):
            event_id = rec.get("event_id") or rec.get("eventId")
            session_id = rec.get("session_id") or rec.get("sessionId")
            rows = rec.get("rows") or rec.get("lapRows") or rec.get("laps") or []
            for r in rows:
                n = normalize_row(r)
                writer.writerow({
                    "event_id": event_id,
                    "session_id": session_id,
                    "competitor_id": n["competitor_id"],
                    "lap_number": n["lap_number"],
                    "lap_time": n["lap_time"],
                    "position": n["position"],
                })
                count += 1
    return count


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Extract lap rows NDJSON -> flat CSV")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--dump-dir", type=Path, default=Path("./output"), help="Root dump directory")
    p.add_argument("--out-dir", type=Path, default=None, help="Output directory (defaults to dump-dir/<org>/)")
    args = p.parse_args(argv)

    dump = args.dump_dir / str(args.org)
    in_path = dump / "laps.ndjson.gz"
    if not in_path.exists():
        in_path = dump / "laps.ndjson"
    if not in_path.exists():
        print("Input file not found:", in_path)
        return 2

    out_dir = args.out_dir or dump
    out_path = out_dir / "laps_flat.csv"
    count = extract(in_path, out_path)
    print(f"Wrote {count} lap rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
