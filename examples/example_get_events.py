"""Example: list events for an organization."""
from __future__ import annotations

import argparse
from mylaps_client_wrapper import SpeedhiveClient


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example: list events for an org")
    parser.add_argument("--org", type=int, required=True, help="Organization id")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--token", help="API token (optional)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    events = client.get_events(org_id=args.org, limit=args.limit)
    for e in events:
        print(f"{e.get('id')}: {e.get('name')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
