"""Fetch lap rows for a given session and write a JSON file.

Usage:
  python examples/get_session_laps.py <session_id> [--token TOKEN] [--output OUTFILE] [--verbose]
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
from event_results_client.api.session_controller.get_lap_rows import asyncio_detailed as get_lap_rows_async


def build_client(token: Optional[str] = None) -> Client:
    if token:
        return AuthenticatedClient(base_url="https://api2.mylaps.com", token=token)
    return Client(base_url="https://api2.mylaps.com")


async def main_async(session_id: int, token: Optional[str], outpath: Path, verbose: bool) -> int:
    client = build_client(token=token)
    async with client:
        resp = await get_lap_rows_async(session_id, client=client)
        if verbose:
            print(f"[DEBUG] laps request status={getattr(resp,'status_code',None)} size={len(resp.content) if resp.content else 0}")
        if not getattr(resp, "content", None):
            print(f"No lap rows returned for session {session_id}")
            return 1
        try:
            payload = json.loads(resp.content)
        except Exception as exc:
            print(f"Failed parsing JSON: {exc}")
            return 2

        # Normalize payload: some endpoints return {'rows': [...]} or a raw list
        rows = []
        if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
            rows = payload["rows"]
        elif isinstance(payload, list):
            rows = payload

        outpath.parent.mkdir(parents=True, exist_ok=True)
        with open(outpath, "w", encoding="utf8") as fh:
            json.dump({"session_id": session_id, "rows": rows}, fh, indent=2)

        print(f"Wrote laps for session {session_id} to {outpath}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch lap rows for a session and write JSON")
    parser.add_argument("session_id", type=int)
    parser.add_argument("--token", help="API token", default=None)
    parser.add_argument("--output", help="Output file (default: output/session_<id>_laps.json)", default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    import asyncio

    out_default = f"output/session_{args.session_id}_laps.json"
    outpath = Path(args.output or out_default)
    return asyncio.run(main_async(args.session_id, args.token, outpath, args.verbose))


if __name__ == "__main__":
    raise SystemExit(main())
