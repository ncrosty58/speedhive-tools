"""Stream events.ndjson(.gz) from an offline dump and write a flattened CSV."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict

from speedhive.processing.ndjson import open_ndjson


def normalize_event(e: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize event field names from various API response formats."""
    org = e.get("organization", {}) or {}
    raw = e.get("raw") or {}
    return {
        "event_id": e.get("id") or e.get("eventId") or e.get("event_id") or raw.get("id"),
        "name": e.get("name") or e.get("eventName") or e.get("title") or raw.get("name"),
        "date": e.get("date") or e.get("startDate") or e.get("start_date") or raw.get("startDate"),
        "end_date": e.get("endDate") or e.get("end_date") or raw.get("endDate"),
        "organization_id": org.get("id") or e.get("organizationId") or e.get("organization_id"),
        "organization_name": org.get("name") or e.get("organizationName"),
        "location": e.get("location") or e.get("venue") or raw.get("location"),
        "country": e.get("country") or org.get("country"),
    }


_FIELDS = ["event_id", "name", "date", "end_date", "organization_id", "organization_name", "location", "country"]


def extract(in_path: Path, out_path: Path) -> int:
    """Extract events from NDJSON(.gz) to CSV. Returns row count."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf8", newline="") as outf:
        writer = csv.DictWriter(outf, fieldnames=_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for rec in open_ndjson(in_path):
            writer.writerow(normalize_event(rec))
            count += 1
    return count


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Extract events NDJSON -> flat CSV")
    p.add_argument("--org", type=int, required=True, help="Organization ID")
    p.add_argument("--dump-dir", type=Path, default=Path("./output"), help="Root dump directory")
    p.add_argument("--out-dir", type=Path, default=None, help="Output directory (defaults to dump-dir/<org>/)")
    args = p.parse_args(argv)

    dump = args.dump_dir / str(args.org)
    in_path = dump / "events.ndjson.gz"
    if not in_path.exists():
        in_path = dump / "events.ndjson"
    if not in_path.exists():
        print("Input file not found:", in_path)
        return 2

    out_dir = args.out_dir or dump
    out_path = out_dir / "events_flat.csv"
    count = extract(in_path, out_path)
    print(f"Wrote {count} events to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
