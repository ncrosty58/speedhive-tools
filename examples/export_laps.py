"""Export lap times for a session.

Usage:
    python examples/export_laps.py 789012
    python examples/export_laps.py 789012 --output laps.json
    python examples/export_laps.py 789012 --format csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add parent to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "mylaps_client"))

from mylaps_client_wrapper import SpeedhiveClient


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export lap times for a session")
    parser.add_argument("session_id", type=int, help="Session ID")
    parser.add_argument("--token", help="API token for authenticated endpoints")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)

    if args.verbose:
        print(f"Fetching laps for session {args.session_id}...", file=sys.stderr)

    laps = client.get_laps(session_id=args.session_id)

    if args.verbose:
        print(f"Found {len(laps)} lap records", file=sys.stderr)

    if not laps:
        print(f"No laps found for session {args.session_id}", file=sys.stderr)
        return 0

    # Output
    if args.format == "json":
        output = json.dumps({"session_id": args.session_id, "laps": laps}, indent=2, default=str)
        if args.output:
            Path(args.output).write_text(output)
            print(f"Wrote {len(laps)} laps to {args.output}", file=sys.stderr)
        else:
            print(output)
    else:  # csv
        fieldnames = ["competitor_id", "lap_number", "lap_time", "position", "session_id"]
        rows = []
        for lap in laps:
            rows.append({
                "competitor_id": lap.get("competitorId") or lap.get("competitor_id"),
                "lap_number": lap.get("lapNumber") or lap.get("lap_number"),
                "lap_time": lap.get("lapTime") or lap.get("lap_time"),
                "position": lap.get("position"),
                "session_id": args.session_id,
            })

        if args.output:
            with open(args.output, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"Wrote {len(rows)} laps to {args.output}", file=sys.stderr)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
