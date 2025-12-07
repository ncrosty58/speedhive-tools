"""Fetch classification/results for a given session and write JSON output.

Usage:
  python examples/get_session_results.py <session_id> [--token TOKEN] [--output OUTFILE] [--verbose]

This script prefers the v2 endpoint (`/v2/sessions/{id}/classification`) and falls
back to the non-v2 endpoint if needed. Output contains a small `summary` list
and the full `raw` payload under the JSON root.
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
from event_results_client.api.session_controller.get_classification import asyncio_detailed as get_classification_v2
from event_results_client.api.session_controller.get_classification_1 import asyncio_detailed as get_classification_v1


def build_client(token: Optional[str] = None) -> Client:
    if token:
        return AuthenticatedClient(base_url="https://api2.mylaps.com", token=token)
    return Client(base_url="https://api2.mylaps.com")


def safe_load_json(raw: bytes) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        return None


def summarize_rows(rows: List[dict]) -> List[dict]:
    out: List[dict] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        # heuristics to find position and competitor name
        pos = r.get("position") or r.get("pos") or r.get("rank") or r.get("place")
        name = (
            r.get("name")
            or r.get("driver")
            or r.get("participantName")
            or (r.get("competitor") or {}).get("name")
            or (r.get("participant") or {}).get("name")
        )
        competitor_id = r.get("competitorId") or r.get("participantId") or r.get("id")
        out.append({"position": pos, "name": name, "competitor_id": competitor_id})
    return out


async def main_async(session_id: int, token: Optional[str], outpath: Path, verbose: bool) -> int:
    client = build_client(token=token)
    async with client:
        # Try v2 endpoint first
        resp = await get_classification_v2(session_id, client=client)
        if verbose:
            print(f"[DEBUG] v2 classification status={getattr(resp,'status_code',None)} size={len(resp.content) if resp.content else 0}")
        if not getattr(resp, "content", None) or resp.status_code >= 400:
            # fallback to non-v2 path
            resp = await get_classification_v1(session_id, client=client)
            if verbose:
                print(f"[DEBUG] v1 classification status={getattr(resp,'status_code',None)} size={len(resp.content) if resp.content else 0}")

        if not getattr(resp, "content", None):
            print(f"No classification returned for session {session_id}")
            return 1

        payload = safe_load_json(resp.content)

        # Normalize rows
        rows: List[dict] = []
        if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
            rows = payload.get("rows", [])
        elif isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict) and any(isinstance(v, list) for v in payload.values()):
            # try to pick a list value if shape is unexpected
            for v in payload.values():
                if isinstance(v, list):
                    rows = v
                    break

        summary = summarize_rows(rows)

        out = {"session_id": session_id, "summary": summary, "raw": payload}

        outpath.parent.mkdir(parents=True, exist_ok=True)
        with open(outpath, "w", encoding="utf8") as fh:
            json.dump(out, fh, indent=2, ensure_ascii=False)

        print(f"Wrote session results for {session_id} to {outpath}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch classification/results for a session")
    parser.add_argument("session_id", type=int)
    parser.add_argument("--token", help="API token", default=None)
    parser.add_argument("--output", help="Output file", default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    out_default = f"session_{args.session_id}_results.json"
    outpath = Path(args.output or out_default)

    import asyncio

    return asyncio.run(main_async(args.session_id, args.token, outpath, args.verbose))


if __name__ == "__main__":
    raise SystemExit(main())
