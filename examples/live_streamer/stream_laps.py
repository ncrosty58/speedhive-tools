#!/usr/bin/env python3
"""Live lap streamer example.

Simple example that polls a live session's lap data and prints new lap rows
as they arrive. Useful as a reference for building a backend poller that
pushes updates to a UI (WebSocket/SSE) or for quick local testing.

Usage:
  python examples/live_streamer/stream_laps.py --session 12345 --token $MYTOKEN

This script uses the `SpeedhiveClient` wrapper from the project to fetch
lap rows (which the wrapper flattens into a list of dicts). By default it
polls every 2.0 seconds and prints new rows as JSON lines.
"""
from __future__ import annotations

import argparse
import json
import time
from typing import Any, Dict, Iterable, Set, Tuple

from mylaps_client_wrapper import SpeedhiveClient


def make_key(row: Dict[str, Any]) -> Tuple[Any, Any]:
    """Return a stable key for a lap row to detect new rows.

    Uses competitor id and lap number when available; falls back to a
    tuple of available identifying fields.
    """
    comp = row.get("competitorId") or row.get("id") or row.get("memberId")
    lapnum = row.get("lapNumber") or row.get("lap") or row.get("lap_num")
    if comp is not None and lapnum is not None:
        return (comp, lapnum)
    # fallback: use timestamp + stringified row hash
    ts = row.get("time") or row.get("timestamp") or row.get("lapTime")
    return (comp, ts)


def poll_session_laps(client: SpeedhiveClient, session_id: int, interval: float = 2.0) -> Iterable[Dict[str, Any]]:
    """Generator that polls the session and yields new lap rows.

    This is a simple polling implementation: it keeps a set of seen keys
    and yields rows whose key was not previously observed.
    """
    seen: Set[Tuple[Any, Any]] = set()
    while True:
        try:
            laps = client.get_laps(session_id=session_id)
            if not laps:
                # no rows yet
                time.sleep(interval)
                continue

            new_rows = []
            for row in laps:
                key = make_key(row)
                if key not in seen:
                    seen.add(key)
                    new_rows.append(row)

            for r in new_rows:
                yield r

        except Exception as exc:  # pragma: no cover - example error handling
            print(f"[ERROR] polling session {session_id}: {exc}")

        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stream new lap rows for a session")
    parser.add_argument("--session", "-s", type=int, required=True, help="Session id to stream")
    parser.add_argument("--token", "-t", default=None, help="API token (optional)")
    parser.add_argument("--interval", "-i", type=float, default=2.0, help="Poll interval in seconds")
    parser.add_argument("--json", dest="jsonl", action="store_true", help="Print rows as JSON lines (default)")
    args = parser.parse_args()

    client = SpeedhiveClient(token=args.token)

    print(f"Starting lap streamer for session {args.session} (interval {args.interval}s)")
    try:
        for row in poll_session_laps(client, args.session, interval=args.interval):
            if args.jsonl:
                print(json.dumps(row, ensure_ascii=False))
            else:
                # human-friendly summary
                comp = row.get("competitorId") or row.get("id")
                lapnum = row.get("lapNumber") or row.get("lap")
                laptime = row.get("lapTime") or row.get("lap_time")
                print(f"Competitor={comp} lap={lapnum} time={laptime}")

    except KeyboardInterrupt:
        print("\nStopped by user")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
