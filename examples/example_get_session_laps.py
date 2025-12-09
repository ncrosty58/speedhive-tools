"""Example: fetch laps for a session."""
from __future__ import annotations

import argparse
from mylaps_client_wrapper import SpeedhiveClient


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example: laps for a session")
    parser.add_argument("--session", type=int, required=True, help="Session id")
    parser.add_argument("--token", help="API token (optional)")
    parser.add_argument("--no-flatten", dest="flatten", action="store_false")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    laps = client.get_laps(session_id=args.session, flatten=args.flatten)
    for lap in laps[:50]:
        print(lap)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
