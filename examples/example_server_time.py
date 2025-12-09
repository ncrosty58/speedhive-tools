"""Example: fetch server time using the SpeedhiveClient wrapper."""
from __future__ import annotations

import argparse
from mylaps_client_wrapper import SpeedhiveClient


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example: get server time")
    parser.add_argument("--token", help="API token (optional)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    t = client.get_server_time()
    print("Server time:", t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
