"""Example: fetch announcements for a session."""
from __future__ import annotations

import argparse
from mylaps_client_wrapper import SpeedhiveClient


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example: session announcements")
    parser.add_argument("--session", type=int, required=True, help="Session id")
    parser.add_argument("--token", help="API token (optional)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    anns = client.get_announcements(session_id=args.session)
    for a in anns[:50]:
        print(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
