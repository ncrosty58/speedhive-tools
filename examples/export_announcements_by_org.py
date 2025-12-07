"""Export track announcements for all sessions in all events for an organization.

Writes one combined JSON file per event containing only sessions that have announcements.

Usage:
    python examples/export_announcements_by_org.py 30476 --output ./announcements --verbose
"""
from __future__ import annotations

import argparse
import json
import sys
import asyncio
from pathlib import Path
from typing import Any, Iterable, List, Optional

# Make generated client importable when running from any cwd
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "mylaps_client"))

from event_results_client import Client, AuthenticatedClient
from event_results_client.api.organization_controller.get_event_list import asyncio_detailed as get_events_for_org_async
from event_results_client.api.event_controller.get_session_list import asyncio_detailed as get_sessions_for_event_async
from event_results_client.api.session_controller.get_announcements import asyncio_detailed as get_announcements_for_session_async
from event_results_client.models.session import Session
from event_results_client.models.run_announcements import RunAnnouncements


def build_client(token: Optional[str] = None) -> Client:
    if token:
        return AuthenticatedClient(base_url="https://api2.mylaps.com", token=token)
    return Client(base_url="https://api2.mylaps.com")


def safe_load_json(raw: bytes) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        return None


def sanitize_for_model(d: dict) -> dict:
    # Fix a few known API quirks: nested `sessions` or similar fields set to null
    if d.get("sessions") is None:
        d = dict(d)
        d["sessions"] = {}
    return d


def _has_announcements(payload: Any) -> bool:
    if payload is None:
        return False
    if isinstance(payload, list):
        return len(payload) > 0
    if isinstance(payload, dict):
        rows = payload.get("rows")
        if rows is None:
            # dict payload but no rows; treat empty dict as no announcements
            return bool(payload)
        return bool(rows)
    return False


async def export_announcements_for_org_async(org_id: int, out_dir: Path, client: Client, verbose: bool = False, concurrency: int = 20) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Get events for the organization (async)
    resp = await get_events_for_org_async(org_id, client=client)
    if verbose:
        print(f"[DEBUG] events request status={getattr(resp,'status_code',None)} size={len(resp.content) if resp.content else 0}")

    if not getattr(resp, "content", None):
        print("No events returned for org id", org_id)
        return

    events_payload = safe_load_json(resp.content)
    if not isinstance(events_payload, Iterable):
        print("Unexpected events payload format")
        return

    events = list(events_payload)

    sem = asyncio.Semaphore(concurrency)

    async def fetch_announcements_for_session(session_dict: dict) -> Optional[dict]:
        sid = session_dict.get("id")
        sname = session_dict.get("name")
        if sid is None:
            return None
        async with sem:
            aresp = await get_announcements_for_session_async(sid, client=client)
        if not getattr(aresp, "content", None):
            return None
        payload = safe_load_json(aresp.content)
        if not _has_announcements(payload):
            return None
        # Normalize payload using generated model when possible
        if isinstance(payload, dict) and "rows" in payload:
            try:
                run_ann = RunAnnouncements.from_dict(payload)
                result = run_ann.to_dict()
            except Exception:
                result = payload
        else:
            result = payload
        return {"id": sid, "name": sname, "announcements": result}

    for ev in events:
        ev_id = ev.get("id")
        ev_name = ev.get("name") or f"event_{ev_id}"
        if verbose:
            print(f"Processing event {ev_id}: {ev_name}")

        # Get sessions for event (async)
        sresp = await get_sessions_for_event_async(ev_id, client=client)
        if verbose:
            print(f"[DEBUG] sessions request status={getattr(sresp,'status_code',None)} size={len(sresp.content) if sresp.content else 0}")
        if not getattr(sresp, "content", None):
            if verbose:
                print(f" No sessions for event {ev_id}")
            continue

        sess_payload = safe_load_json(sresp.content)
        if not isinstance(sess_payload, (dict, list)):
            if verbose:
                print(f" Unexpected sessions payload for event {ev_id}")
            continue

        raw_sessions: List[dict] = []
        if isinstance(sess_payload, list):
            raw_sessions = list(sess_payload)
        elif isinstance(sess_payload, dict):
            if isinstance(sess_payload.get("sessions"), list):
                raw_sessions.extend(sess_payload.get("sessions", []))
            for g in sess_payload.get("groups", []):
                for s_item in g.get("sessions", []) if isinstance(g.get("sessions"), list) else []:
                    raw_sessions.append(s_item)

        # Launch concurrent fetches for announcements
        tasks = [asyncio.create_task(fetch_announcements_for_session(s)) for s in raw_sessions if isinstance(s, dict) and s.get("id")]
        results = await asyncio.gather(*tasks)
        # Filter out sessions with no announcements
        sessions_with_ann = [r for r in results if r]

        if not sessions_with_ann:
            if verbose:
                print(f" No announcements found for any sessions in event {ev_id}")
            continue

        ev_out = {"id": ev_id, "name": ev_name, "sessions": sessions_with_ann}
        out_file = out_dir / f"event_{ev_id}_announcements.json"
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(ev_out, f, ensure_ascii=False, indent=2)
        if verbose:
            print(f" Wrote event announcements to {out_file}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export announcements for all sessions in events for an org")
    parser.add_argument("org_id", type=int, help="Organization id")
    parser.add_argument("--output", "-o", default="./output/announcements", help="Output directory")
    parser.add_argument("--token", help="API token for authenticated endpoints", default=None)
    parser.add_argument("--verbose", action="store_true", help="Verbose debug output")
    parser.add_argument("--concurrency", "-c", type=int, default=20, help="Maximum concurrent requests")
    args = parser.parse_args(argv)

    client = build_client(token=args.token)
    out_dir = Path(args.output)

    async def _run():
        async with client:
            await export_announcements_for_org_async(
                args.org_id,
                out_dir,
                client=client,
                verbose=args.verbose,
                concurrency=args.concurrency,
            )

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
