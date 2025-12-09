#!/usr/bin/env python3
"""Get the fastest track record for each classification.

This script shows how to query track records and identify the current
(fastest) record for each classification in an organization.

Usage:
  python examples/get_fastest_records.py --org 30476
  python examples/get_fastest_records.py --org 30476 --classification IT7
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from collections import defaultdict

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mylaps_client_wrapper import SpeedhiveClient


def main(argv=None):
    parser = argparse.ArgumentParser(description="Get fastest track records")
    parser.add_argument("--org", type=int, required=True, help="Organization ID")
    parser.add_argument("--classification", help="Get fastest record for specific classification")
    parser.add_argument("--limit-events", type=int, help="Limit number of events to scan")
    parser.add_argument("--token", help="API token (if required)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    
    if args.classification:
        # Get fastest record for a single classification
        record = client.get_fastest_track_record(
            org_id=args.org,
            classification=args.classification,
            limit_events=args.limit_events,
        )
        
        if record:
            print(f"Fastest {record['classification']} Track Record:")
            print(f"  Time: {record['lap_time']}")
            print(f"  Driver: {record['driver']}")
            if record.get("marque"):
                print(f"  Marque: {record.get('marque')}")
            print(f"  Event: {record['event_name']}")
            print(f"  Session: {record['session_name']}")
            print(f"  Date: {record['timestamp']}")
        else:
            print(f"No track records found for {args.classification}")
            return 1
    else:
        # Get all records and group by classification to find fastest
        print(f"Scanning organization {args.org} for track records...")
        records = client.get_track_records(
            org_id=args.org,
            limit_events=args.limit_events,
        )
        
        if not records:
            print("No track records found")
            return 1
        
        # Group by classification and keep only the fastest
        fastest_by_class = {}
        for record in records:
            class_name = record["classification"]
            if class_name not in fastest_by_class:
                fastest_by_class[class_name] = record
            elif record["lap_time_seconds"] < fastest_by_class[class_name]["lap_time_seconds"]:
                fastest_by_class[class_name] = record
        
        print(f"\nFastest Track Records ({len(fastest_by_class)} classifications):")
        print("-" * 80)
        
        for class_name in sorted(fastest_by_class.keys()):
            record = fastest_by_class[class_name]
            marque = record.get("marque") or ""
            print(f"{class_name:10s} {record['lap_time']:>10s}  {record['driver']:30s}  {marque:15s}  {record['event_name'][:40]}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
