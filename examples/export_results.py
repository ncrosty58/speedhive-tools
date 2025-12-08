"""Export classification/results for a session.

Usage:
    python examples/export_results.py 789012
    python examples/export_results.py 789012 --output results.json
    python examples/export_results.py 789012 --format csv
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
    parser = argparse.ArgumentParser(description="Export results/classification for a session")
    parser.add_argument("session_id", type=int, help="Session ID")
    parser.add_argument("--token", help="API token for authenticated endpoints")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)

    if args.verbose:
        print(f"Fetching results for session {args.session_id}...", file=sys.stderr)

    results = client.get_results(session_id=args.session_id)

    if args.verbose:
        print(f"Found {len(results)} results", file=sys.stderr)

    if not results:
        print(f"No results found for session {args.session_id}", file=sys.stderr)
        return 0

    # Output
    if args.format == "json":
        output = json.dumps({"session_id": args.session_id, "results": results}, indent=2, default=str)
        if args.output:
            Path(args.output).write_text(output)
            print(f"Wrote {len(results)} results to {args.output}", file=sys.stderr)
        else:
            print(output)
    else:  # csv
        fieldnames = ["position", "competitor_id", "name", "total_time", "best_lap", "session_id"]
        rows = []
        for r in results:
            competitor = r.get("competitor", {}) or {}
            rows.append({
                "position": r.get("position") or r.get("pos"),
                "competitor_id": r.get("competitorId") or r.get("competitor_id") or competitor.get("id"),
                "name": r.get("name") or competitor.get("name") or r.get("participantName"),
                "total_time": r.get("totalTime") or r.get("total_time") or r.get("time"),
                "best_lap": r.get("bestLapTime") or r.get("best_lap"),
                "session_id": args.session_id,
            })

        if args.output:
            with open(args.output, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"Wrote {len(rows)} results to {args.output}", file=sys.stderr)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
