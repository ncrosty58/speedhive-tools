#!/usr/bin/env python3
"""Live lap streamer example.

Simple example that polls a session's lap data and prints new lap rows as
they arrive. This example uses the REST API via `SpeedhiveClient` and is a
safe polling-based reference until an official realtime API is available.

Usage:
  python examples/live_streamer/stream_laps.py --session 12345 --token $MYTOKEN
"""
from __future__ import annotations

import argparse
import json
import time
from typing import Any, Dict, Iterable, Set, Tuple

try:
    from mylaps_live_client import LiveTimingClient
except Exception:
    LiveTimingClient = None  # type: ignore


def make_key(row: Dict[str, Any]) -> Tuple[Any, Any]:
    """Return a stable key for a lap row to detect new rows.

    Uses competitor id and lap number when available; falls back to a
    tuple of available identifying fields.
    """
    comp = row.get("competitorId") or row.get("id") or row.get("memberId")
    lapnum = row.get("lapNumber") or row.get("lap") or row.get("lap_num")
    if comp is not None and lapnum is not None:
        return (comp, lapnum)
    ts = row.get("time") or row.get("timestamp") or row.get("lapTime")
    return (comp, ts)


def poll_session_laps(client, session_id: int, interval: float = 2.0) -> Iterable[Dict[str, Any]]:
    """Generator that polls the session and yields new lap rows.

    This keeps a set of seen keys and yields rows whose key was not previously
    observed. It's intentionally simple and suitable as an example fallback
    until a realtime API is adopted.
    """
    seen: Set[Tuple[Any, Any]] = set()
    while True:
        try:
            laps = client.get_laps(session_id=session_id)
            if not laps:
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
    parser.add_argument("--use-live-client", action="store_true", help="Use `LiveTimingClient` polling fallback (if available)")
    parser.add_argument("--real", action="store_true", help="Run real polling behavior (default: demo/stub mode)")
    parser.add_argument("--demo-duration", type=float, default=None, help="When in demo mode, run for this many seconds and exit")
    parser.add_argument("--json", dest="jsonl", action="store_true", help="Print rows as JSON lines (default)")
    args = parser.parse_args()

    # Lazily import the REST wrapper if running in real mode
    try:
        from mylaps_client_wrapper import SpeedhiveClient  # type: ignore
    except Exception:
        print("Error: SpeedhiveClient is not available in this environment.")
        return 1

    client = SpeedhiveClient(token=args.token)

    # If not in "real" mode, run a demo/stub that shows how to use the
    # LiveTimingClient without making network calls. This keeps the examples
    # safe to run and suitable for documentation/reference purposes.
    if not args.real:
        print("Demo mode: using `LiveTimingClient` as a stubbed reference.")
        if LiveTimingClient is None:
            print("  (mylaps_live_client.LiveTimingClient not available in this environment)")
            print("  Example usage (pseudo-code):")
            print("    live = LiveTimingClient(token='MYTOKEN')")
            print("    live.connect()  # establish websocket/SSE connection")
            print("    live.subscribe_session(session_key, callback)")
            print("    # on shutdown: live.close()")
            return 0

        live = LiveTimingClient(token=args.token)
        print("  Created LiveTimingClient (stub)")
        print("  Methods available (stub): connect(), subscribe_session(), subscribe_announcements(), start_polling_fallback(), close()")
        print("  The realtime methods are intentionally unimplemented; call `start_polling_fallback()` to run a safe polling demo.")

        def demo_cb(row: dict) -> None:
            print("[demo callback] row:", json.dumps(row, ensure_ascii=False))

        print("  Starting guarded polling fallback demo (no network unless REST client is configured)...")
        try:
            live.start_polling_fallback(session_id=args.session, callback=demo_cb, interval=args.interval)
            print("  Polling fallback started (press Ctrl-C to stop).")
            start = time.monotonic()
            if args.demo_duration is None:
                # block until interrupted
                while True:
                    time.sleep(1.0)
            else:
                # run demo for a bounded duration then exit
                while time.monotonic() - start < float(args.demo_duration):
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopped demo by user")
        finally:
            live.close()

        return 0

    print(f"Starting lap streamer for session {args.session} (interval {args.interval}s)")
    try:
        for row in poll_session_laps(client, args.session, interval=args.interval):
            if args.jsonl:
                print(json.dumps(row, ensure_ascii=False))
            else:
                comp = row.get("competitorId") or row.get("id")
                lapnum = row.get("lapNumber") or row.get("lap")
                laptime = row.get("lapTime") or row.get("lap_time")
                print(f"Competitor={comp} lap={lapnum} time={laptime}")

    except KeyboardInterrupt:
        print("\nStopped by user")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
