"""Export sessions for an event.

Usage:
    python examples/export_sessions.py 123456
    python examples/export_sessions.py 123456 --output sessions.json
    python examples/export_sessions.py 123456 --format csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add parent to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "mylaps_client"))

from mylaps_client_wrapper import SpeedhiveClient


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export sessions for an event")
    parser.add_argument("event_id", type=int, help="Event ID")
    parser.add_argument("--token", help="API token for authenticated endpoints")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)

    if args.verbose:
        print(f"Fetching sessions for event {args.event_id}...", file=sys.stderr)

    sessions = client.get_sessions(event_id=args.event_id)

    if args.verbose:
        print(f"Found {len(sessions)} sessions", file=sys.stderr)

    if not sessions:
        print(f"No sessions found for event {args.event_id}", file=sys.stderr)
        return 0

    # Output
    if args.format == "json":
        output = json.dumps({"event_id": args.event_id, "sessions": sessions}, indent=2, default=str)
        if args.output:
            Path(args.output).write_text(output)
            print(f"Wrote {len(sessions)} sessions to {args.output}", file=sys.stderr)
        else:
            print(output)
    else:  # csv
        fieldnames = ["id", "name", "type", "start_time", "end_time", "event_id"]
        rows = []
        for s in sessions:
            rows.append({
                "id": s.get("id"),
                "name": s.get("name"),
                "type": s.get("type") or s.get("sessionType"),
                "start_time": s.get("startTime") or s.get("start_time"),
                "end_time": s.get("endTime") or s.get("end_time"),
                "event_id": args.event_id,
            })

        if args.output:
            with open(args.output, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"Wrote {len(rows)} sessions to {args.output}", file=sys.stderr)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return 0


def fetch_sessions_for_event(client: SpeedhiveClient, event_id: int):
    """Return list of sessions for an event (used by export_full_dump orchestration)."""
    return client.get_sessions(event_id=event_id)


if __name__ == "__main__":
    raise SystemExit(main())
