"""Fetch all sessions for a given event and print details.

Usage:
  python examples/get_event_sessions.py <event_id> [--token TOKEN] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "mylaps_client"))

from event_results_client import Client, AuthenticatedClient
from event_results_client.api.event_controller.get_session_list import asyncio_detailed as get_sessions_for_event_async


def build_client(token: Optional[str] = None) -> Client:
    if token:
        return AuthenticatedClient(base_url="https://api2.mylaps.com", token=token)
    return Client(base_url="https://api2.mylaps.com")


def safe_load_json(raw: bytes) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        return None


async def main_async(event_id: int, token: Optional[str], verbose: bool) -> int:
    client = build_client(token=token)
    async with client:
        resp = await get_sessions_for_event_async(event_id, client=client)
        if verbose:
            print(f"[DEBUG] sessions request status={getattr(resp,'status_code',None)} size={len(resp.content) if resp.content else 0}")
        if not getattr(resp, "content", None):
            print(f"No sessions returned for event {event_id}")
            return 1
        payload = safe_load_json(resp.content)
        sessions: List[dict] = []
        if isinstance(payload, list):
            sessions = payload
        elif isinstance(payload, dict):
            if isinstance(payload.get("sessions"), list):
                sessions.extend(payload.get("sessions", []))
            for g in payload.get("groups", []):
                for s in g.get("sessions", []) if isinstance(g.get("sessions"), list) else []:
                    sessions.append(s)

        print(json.dumps({"event_id": event_id, "session_count": len(sessions), "sessions": sessions}, indent=2))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch sessions for an event")
    parser.add_argument("event_id", type=int)
    parser.add_argument("--token", help="API token", default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    import asyncio

    return asyncio.run(main_async(args.event_id, args.token, args.verbose))


if __name__ == "__main__":
    raise SystemExit(main())
