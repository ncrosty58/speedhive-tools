"""Export events for an organization.

Usage:
    python examples/export_events.py 30476
    python examples/export_events.py 30476 --limit 10 --output events.json
    python examples/export_events.py 30476 --format csv --output events.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add parent to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "mylaps_client"))

from mylaps_client_wrapper import SpeedhiveClient


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export events for an organization")
    parser.add_argument("org_id", type=int, help="Organization ID")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of events")
    parser.add_argument("--token", help="API token for authenticated endpoints")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)

    if args.verbose:
        print(f"Fetching events for org {args.org_id}...", file=sys.stderr)

    if args.limit:
        events = client.get_events(org_id=args.org_id, limit=args.limit)
    else:
        # Get all events via pagination
        events = list(client.iter_events(org_id=args.org_id))

    if args.verbose:
        print(f"Found {len(events)} events", file=sys.stderr)

    if not events:
        print(f"No events found for org {args.org_id}", file=sys.stderr)
        return 0

    # Output
    if args.format == "json":
        output = json.dumps(events, indent=2, default=str)
        if args.output:
            Path(args.output).write_text(output)
            print(f"Wrote {len(events)} events to {args.output}", file=sys.stderr)
        else:
            print(output)
    else:  # csv
        if not events:
            return 0
        # Flatten for CSV - use common fields
        fieldnames = ["id", "name", "date", "organization_id", "organization_name"]
        rows = []
        for e in events:
            org = e.get("organization", {}) or {}
            rows.append({
                "id": e.get("id"),
                "name": e.get("name"),
                "date": e.get("date") or e.get("startDate"),
                "organization_id": org.get("id"),
                "organization_name": org.get("name"),
            })

        if args.output:
            with open(args.output, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"Wrote {len(rows)} events to {args.output}", file=sys.stderr)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return 0


def fetch_events_for_org(client: SpeedhiveClient, org_id: int, limit: Optional[int] = None):
    """Return list of events for org (used by export_full_dump orchestration)."""
    if limit:
        return client.get_events(org_id=org_id, limit=limit)
    return list(client.iter_events(org_id=org_id))


if __name__ == "__main__":
    raise SystemExit(main())
