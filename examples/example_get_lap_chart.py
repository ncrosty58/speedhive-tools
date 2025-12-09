"""Example: fetch lap chart (position per lap) for a session."""
from __future__ import annotations

import argparse
from mylaps_client_wrapper import SpeedhiveClient


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example: lap chart for a session")
    parser.add_argument("--session", type=int, required=True, help="Session id")
    parser.add_argument("--token", help="API token (optional)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    chart = client.get_lap_chart(session_id=args.session)
    for row in chart[:50]:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
