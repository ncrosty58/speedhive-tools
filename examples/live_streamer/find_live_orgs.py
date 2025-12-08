#!/usr/bin/env python3
"""Helper: list recent events for an organization (REST-only).

This script intentionally avoids the broad discovery/scanning behavior that
previous examples attempted. The REST wrapper no longer exposes the
`events/updatedFrom` discovery helper and there is no public, documented
realtime discovery endpoint available without authentication.

Use this helper to list recent events for a given organization using the
REST API. If you need realtime detection of live sessions, implement a
`LiveTimingClient` (see `mylaps_live_client.py`) or provide a specific
list of organization IDs / event IDs to check.

Usage:
  python examples/live_streamer/find_live_orgs.py --org 30476 --token $MYTOKEN --limit 20

This will fetch up to `--limit` events for the organization and print
basic metadata and session counts. It is a safe, REST-only helper.
"""
from __future__ import annotations

import argparse
from typing import Any

from mylaps_client_wrapper import SpeedhiveClient


def main() -> int:
    p = argparse.ArgumentParser(description="List recent events for an organization (REST-only)")
    p.add_argument("--org", type=int, required=True, help="Organization id to query")
    p.add_argument("--token", default=None, help="API token (optional)")
    p.add_argument("--limit", type=int, default=20, help="Maximum number of events to return")
    args = p.parse_args()

    client = SpeedhiveClient(token=args.token)

    print(f"Fetching up to {args.limit} events for org {args.org}...")
    events = client.get_events(org_id=args.org, limit=args.limit)
    if not events:
        print("No events returned. If you expected results, provide a valid API token or verify the org id.")
        return 1

    for ev in events:
        event_id = ev.get("id")
        name = ev.get("name") or ev.get("title")
        date = ev.get("date") or ev.get("startDate")
        # try to get session count if sessions are present
        sessions = ev.get("sessions") or []
        print(f"- Event {event_id}: {name} date={date} sessions={len(sessions)}")

    print("\nNotes:")
    print(" - For realtime/live detection, implement a `LiveTimingClient` (see mylaps_live_client.py).")
    print(" - To stream lap updates, use examples/live_streamer/stream_laps.py with a known session id.")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
