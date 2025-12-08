#!/usr/bin/env python3
"""Export track records for an organization.

This script efficiently scans events and sessions to find track record
announcements and exports them to a CSV or JSON file.

Usage:
  python examples/export_track_records.py --org 30476 --out track_records.csv
  python examples/export_track_records.py --org 30476 --classification IT7 --format json --out it7_records.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from mylaps_client_wrapper import SpeedhiveClient


def export_csv(records, output_path: Path):
    """Export track records to CSV."""
    if not records:
        print("No track records found", file=sys.stderr)
        return
    
    fieldnames = [
        "classification",
        "lap_time",
        "lap_time_seconds",
        "driver",
        "event_id",
        "event_name",
        "session_id",
        "session_name",
        "timestamp",
    ]
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    
    print(f"Wrote {len(records)} track records to {output_path}")


def export_json(records, output_path: Path):
    """Export track records to JSON."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    print(f"Wrote {len(records)} track records to {output_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export track records for an organization")
    parser.add_argument("--org", type=int, required=True, help="Organization ID")
    parser.add_argument("--classification", help="Filter by classification (e.g., IT7, T4, P2)")
    parser.add_argument("--limit-events", type=int, help="Limit number of events to scan (for testing)")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Output format")
    parser.add_argument("--out", type=Path, default=Path("track_records.csv"), help="Output file path")
    parser.add_argument("--token", help="API token (if required)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show progress")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    
    if args.verbose:
        print(f"Scanning organization {args.org} for track records...", file=sys.stderr)
        if args.classification:
            print(f"  Filtering for classification: {args.classification}", file=sys.stderr)
    
    records = client.get_track_records(
        org_id=args.org,
        classification=args.classification,
        limit_events=args.limit_events,
    )
    
    if args.verbose:
        print(f"Found {len(records)} track records", file=sys.stderr)
        if records:
            classes = sorted(set(r["classification"] for r in records))
            print(f"  Classifications: {', '.join(classes)}", file=sys.stderr)
    
    if args.format == "csv":
        export_csv(records, args.out)
    else:
        export_json(records, args.out)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
