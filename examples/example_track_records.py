"""Example: find track records for an organization."""
from __future__ import annotations

import argparse
from mylaps_client_wrapper import SpeedhiveClient


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example: track records for an org")
    parser.add_argument("--org", type=int, required=True, help="Organization id")
    parser.add_argument("--class", dest="classification", help="Classification filter (optional)")
    parser.add_argument("--limit-events", type=int, default=None)
    parser.add_argument("--token", help="API token (optional)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    records = client.get_track_records(org_id=args.org, classification=args.classification, limit_events=args.limit_events)
    for r in records[:50]:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
