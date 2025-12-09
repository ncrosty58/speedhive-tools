"""Example: list championships for an organization and fetch a championship."""
from __future__ import annotations

import argparse
from mylaps_client_wrapper import SpeedhiveClient


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example: championships for an org")
    parser.add_argument("--org", type=int, required=True, help="Organization id")
    parser.add_argument("--champ", type=int, help="Specific championship id (optional)")
    parser.add_argument("--token", help="API token (optional)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    champs = client.get_championships(org_id=args.org)
    for c in champs:
        print(f"{c.get('id')}: {c.get('name')}")

    if args.champ:
        detail = client.get_championship(championship_id=args.champ)
        print(detail)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
