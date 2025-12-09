"""Example: fetch organization details."""
from __future__ import annotations

import argparse
from mylaps_client_wrapper import SpeedhiveClient


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example: get organization details")
    parser.add_argument("--org", type=int, required=True, help="Organization id")
    parser.add_argument("--token", help="API token (optional)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    org = client.get_organization(org_id=args.org)
    print(org)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
