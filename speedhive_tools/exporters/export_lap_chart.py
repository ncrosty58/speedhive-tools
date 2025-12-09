"""Export lap chart data for a session (position changes per lap).

This is useful for creating position progression visualizations.

Usage:
    python examples/export_lap_chart.py 789012
    python examples/export_lap_chart.py 789012 --format csv --output lap_chart.csv
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
    parser = argparse.ArgumentParser(description="Export lap chart data for position progression visualization")
    parser.add_argument("session_id", type=int, help="Session ID")
    parser.add_argument("--token", help="API token for authenticated endpoints")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)

    if args.verbose:
        print(f"Fetching lap chart for session {args.session_id}...", file=sys.stderr)

    lap_chart = client.get_lap_chart(session_id=args.session_id)

    if args.verbose:
        print(f"Found {len(lap_chart)} entries", file=sys.stderr)

    if not lap_chart:
        print(f"No lap chart data found for session {args.session_id}", file=sys.stderr)
        return 0

    if args.format == "json":
        output = json.dumps({"session_id": args.session_id, "lap_chart": lap_chart}, indent=2, default=str)
        if args.output:
            Path(args.output).write_text(output)
            print(f"Wrote lap chart to {args.output}", file=sys.stderr)
        else:
            print(output)
    else:  # csv - flatten the lap chart data
        # Lap chart typically has competitors with position per lap
        # Flatten to: competitor_id, lap_number, position
        fieldnames = ["competitor_id", "name", "lap_number", "position", "session_id"]
        rows = []

        for entry in lap_chart:
            comp_id = entry.get("competitorId") or entry.get("id")
            name = entry.get("name") or entry.get("competitorName")
            positions = entry.get("positions", entry.get("laps", []))

            if isinstance(positions, list):
                for i, pos in enumerate(positions, start=1):
                    if isinstance(pos, dict):
                        rows.append({
                            "competitor_id": comp_id,
                            "name": name,
                            "lap_number": pos.get("lap", i),
                            "position": pos.get("position", pos.get("pos")),
                            "session_id": args.session_id,
                        })
                    else:
                        # Simple list of positions
                        rows.append({
                            "competitor_id": comp_id,
                            "name": name,
                            "lap_number": i,
                            "position": pos,
                            "session_id": args.session_id,
                        })

        if args.output:
            with open(args.output, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"Wrote {len(rows)} lap chart entries to {args.output}", file=sys.stderr)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return 0


def fetch_lap_chart_for_session(client: SpeedhiveClient, session_id: int):
    """Return lap chart data for a session (used by orchestrator)."""
    return client.get_lap_chart(session_id=session_id)


if __name__ == "__main__":
    raise SystemExit(main())
