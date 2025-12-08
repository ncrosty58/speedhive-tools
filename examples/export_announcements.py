"""Export announcements for a session or all sessions in an organization.

Usage:
    # Single session
    python examples/export_announcements.py --session 789012

    # All sessions for an org (bulk export)
    python examples/export_announcements.py --org 30476 --output ./announcements
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add parent to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "mylaps_client"))

from mylaps_client_wrapper import SpeedhiveClient


def export_session_announcements(client: SpeedhiveClient, session_id: int, output: Optional[str], verbose: bool) -> int:
    """Export announcements for a single session."""
    if verbose:
        print(f"Fetching announcements for session {session_id}...", file=sys.stderr)

    announcements = client.get_announcements(session_id=session_id)

    if verbose:
        print(f"Found {len(announcements)} announcements", file=sys.stderr)

    if not announcements:
        print(f"No announcements found for session {session_id}", file=sys.stderr)
        return 0

    result = {"session_id": session_id, "announcements": announcements}
    output_str = json.dumps(result, indent=2, default=str)

    if output:
        Path(output).write_text(output_str)
        print(f"Wrote {len(announcements)} announcements to {output}", file=sys.stderr)
    else:
        print(output_str)

    return 0


def export_org_announcements(client: SpeedhiveClient, org_id: int, output_dir: Path, verbose: bool) -> int:
    """Export announcements for all sessions in all events for an organization."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"Fetching events for org {org_id}...", file=sys.stderr)

    total_announcements = 0
    events_with_announcements = 0

    for event in client.iter_events(org_id=org_id):
        event_id = event.get("id")
        event_name = event.get("name", "Unknown")

        if verbose:
            print(f"  Processing event {event_id}: {event_name}", file=sys.stderr)

        sessions = client.get_sessions(event_id=event_id)
        event_announcements = []

        for session in sessions:
            session_id = session.get("id")
            if not session_id:
                continue

            announcements = client.get_announcements(session_id=session_id)
            if announcements:
                event_announcements.append({
                    "session_id": session_id,
                    "session_name": session.get("name"),
                    "announcements": announcements,
                })
                total_announcements += len(announcements)

        if event_announcements:
            events_with_announcements += 1
            out_file = output_dir / f"event_{event_id}_announcements.json"
            result = {
                "event_id": event_id,
                "event_name": event_name,
                "sessions": event_announcements,
            }
            out_file.write_text(json.dumps(result, indent=2, default=str))
            if verbose:
                print(f"    Wrote {sum(len(s['announcements']) for s in event_announcements)} announcements", file=sys.stderr)

    print(f"Exported {total_announcements} announcements from {events_with_announcements} events to {output_dir}", file=sys.stderr)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export announcements")
    parser.add_argument("--session", type=int, help="Session ID (for single session export)")
    parser.add_argument("--org", type=int, help="Organization ID (for bulk export)")
    parser.add_argument("--token", help="API token for authenticated endpoints")
    parser.add_argument("--output", "-o", help="Output file/directory")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    if not args.session and not args.org:
        parser.error("Either --session or --org is required")

    client = SpeedhiveClient(token=args.token)

    if args.session:
        return export_session_announcements(client, args.session, args.output, args.verbose)
    else:
        output_dir = Path(args.output) if args.output else Path(f"output/announcements/{args.org}")
        return export_org_announcements(client, args.org, output_dir, args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
