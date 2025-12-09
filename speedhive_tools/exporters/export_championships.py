"""Export championships for an organization or standings for a specific championship.

Usage:
    # List championships for an org
    python examples/export_championships.py --org 30476

    # Get standings for a specific championship
    python examples/export_championships.py --championship 12345
    python examples/export_championships.py --championship 12345 --format csv
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


def export_championships_list(client: SpeedhiveClient, org_id: int, output: Optional[str], format: str, verbose: bool) -> int:
    """Export list of championships for an organization."""
    if verbose:
        print(f"Fetching championships for org {org_id}...", file=sys.stderr)

    championships = client.get_championships(org_id=org_id)

    if verbose:
        print(f"Found {len(championships)} championships", file=sys.stderr)

    if not championships:
        print(f"No championships found for org {org_id}", file=sys.stderr)
        return 0

    if format == "json":
        output_str = json.dumps(championships, indent=2, default=str)
        if output:
            Path(output).write_text(output_str)
            print(f"Wrote {len(championships)} championships to {output}", file=sys.stderr)
        else:
            print(output_str)
    else:  # csv
        fieldnames = ["id", "name", "year", "organization_id"]
        rows = []
        for c in championships:
            rows.append({
                "id": c.get("id"),
                "name": c.get("name"),
                "year": c.get("year"),
                "organization_id": org_id,
            })

        if output:
            with open(output, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"Wrote {len(rows)} championships to {output}", file=sys.stderr)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return 0


def export_championship_standings(client: SpeedhiveClient, championship_id: int, output: Optional[str], format: str, verbose: bool) -> int:
    """Export standings for a specific championship."""
    if verbose:
        print(f"Fetching standings for championship {championship_id}...", file=sys.stderr)

    standings = client.get_championship(championship_id=championship_id)

    if not standings:
        print(f"No standings found for championship {championship_id}", file=sys.stderr)
        return 0

    # Handle both dict response (with nested data) and list response
    rows = []
    if isinstance(standings, dict):
        rows = standings.get("standings", standings.get("rows", []))
        if not rows and "classes" in standings:
            # Some championships have class-based standings
            for cls in standings.get("classes", []):
                rows.extend(cls.get("standings", cls.get("rows", [])))
    elif isinstance(standings, list):
        rows = standings

    if verbose:
        print(f"Found {len(rows)} standings entries", file=sys.stderr)

    if format == "json":
        output_str = json.dumps(standings, indent=2, default=str)
        if output:
            Path(output).write_text(output_str)
            print(f"Wrote championship standings to {output}", file=sys.stderr)
        else:
            print(output_str)
    else:  # csv
        fieldnames = ["position", "competitor_id", "name", "points", "championship_id"]
        csv_rows = []
        for r in rows:
            competitor = r.get("competitor", {}) or {}
            csv_rows.append({
                "position": r.get("position") or r.get("rank"),
                "competitor_id": r.get("competitorId") or competitor.get("id"),
                "name": r.get("name") or competitor.get("name"),
                "points": r.get("points") or r.get("totalPoints"),
                "championship_id": championship_id,
            })

        if output:
            with open(output, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_rows)
            print(f"Wrote {len(csv_rows)} standings to {output}", file=sys.stderr)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export championships or championship standings")
    parser.add_argument("--org", type=int, help="Organization ID (list championships)")
    parser.add_argument("--championship", type=int, help="Championship ID (get standings)")
    parser.add_argument("--token", help="API token for authenticated endpoints")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    if not args.org and not args.championship:
        parser.error("Either --org or --championship is required")

    client = SpeedhiveClient(token=args.token)

    if args.championship:
        return export_championship_standings(client, args.championship, args.output, args.format, args.verbose)
    else:
        return export_championships_list(client, args.org, args.output, args.format, args.verbose)


def fetch_championships_for_org(client: SpeedhiveClient, org_id: int):
    """Return list of championships for an organization (used by orchestrator)."""
    return client.get_championships(org_id=org_id)


def fetch_championship_standings(client: SpeedhiveClient, championship_id: int):
    """Return standings for a championship (used by orchestrator)."""
    return client.get_championship(championship_id=championship_id)


if __name__ == "__main__":
    raise SystemExit(main())
