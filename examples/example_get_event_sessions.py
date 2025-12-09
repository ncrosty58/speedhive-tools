"""Example: show sessions for an event."""
from __future__ import annotations

import argparse
from mylaps_client_wrapper import SpeedhiveClient


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example: sessions for an event")
    parser.add_argument("--event", type=int, required=True, help="Event id")
    parser.add_argument("--token", help="API token (optional)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    sessions = client.get_sessions(event_id=args.event)
    for s in sessions:
        print(f"{s.get('id')}: {s.get('name')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
