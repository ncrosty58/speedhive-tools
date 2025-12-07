"""Export a large, incremental dump of data for one or more organizations.

This script is conservative with memory: it streams results to disk (NDJSON),
optionally gzipped, and limits concurrency with a semaphore. It does NOT load
the whole dataset into memory.

Usage examples:
  # Single org, default output dir `output/full_dump` (gzipped ndjson)
  python examples/export_full_dump.py --org 30476 --output ./output/full_dump --verbose

  # Multiple orgs, custom concurrency
  python examples/export_full_dump.py --org 30476 --org 12345 --concurrency 3

Notes:
- You MUST supply one or more organization ids (the script will fetch events for
  each org, then sessions, laps, and announcements).
- This is intended for incremental, offline archival and respects low-RAM
  environments by writing each record to disk as it arrives.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Any, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "mylaps_client"))

from event_results_client import Client, AuthenticatedClient

# Some generated client versions may not expose every endpoint path we try to use.
# Import endpoint callables in try/except blocks so the module can be imported
# even if a particular generated function is missing. At runtime we check and
# provide a clear error message if a required endpoint is not available.
try:
    from event_results_client.api.organization_controller.get_event_list import asyncio_detailed as get_events_for_org_async
except Exception:
    get_events_for_org_async = None

try:
    from event_results_client.api.event_controller.get_session_list import asyncio_detailed as get_sessions_for_event_async
except Exception:
    get_sessions_for_event_async = None

try:
    from event_results_client.api.session_controller.get_announcements import asyncio_detailed as get_announcements_for_session_async
except Exception:
    get_announcements_for_session_async = None

try:
    from event_results_client.api.session_controller.get_lap_rows import asyncio_detailed as get_lap_rows_async
except Exception:
    get_lap_rows_async = None


def build_client(token: Optional[str] = None) -> Client:
    if token:
        return AuthenticatedClient(base_url="https://api2.mylaps.com", token=token)
    return Client(base_url="https://api2.mylaps.com")


def safe_load_json(raw: Optional[bytes]) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def ndjson_writer(path: Path, compress: bool = True):
    """Return a context manager that yields a write() function for NDJSON lines.

    The `write(obj)` will write a single JSON object as a line.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if compress:
        fh = gzip.open(path.with_suffix(path.suffix + ".gz"), "wt", encoding="utf8")
    else:
        fh = open(path, "w", encoding="utf8")

    def write(obj: Any) -> None:
        fh.write(json.dumps(obj, ensure_ascii=False))
        fh.write("\n")

    return fh, write


async def export_org(org_id: int, out_dir: Path, client: Client, verbose: bool = False, concurrency: int = 3, compress: bool = True) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Check availability of endpoint helper callables and decide what we can do.
    HAVE_EVENTS = callable(get_events_for_org_async)
    HAVE_SESSIONS = callable(get_sessions_for_event_async)
    HAVE_ANNOUNCEMENTS = callable(get_announcements_for_session_async)
    HAVE_LAP_ROWS = callable(get_lap_rows_async)

    if not HAVE_EVENTS:
        raise RuntimeError("Required endpoint function `get_events_for_org_async` is not available in the generated client. Regenerate the client or add the missing endpoint.")
    if not HAVE_SESSIONS:
        raise RuntimeError("Required endpoint function `get_sessions_for_event_async` is not available in the generated client. Regenerate the client or add the missing endpoint.")

    if not HAVE_ANNOUNCEMENTS and verbose:
        print("[WARN] announcements endpoint missing in generated client; exporter will skip announcements")
    if not HAVE_LAP_ROWS and verbose:
        print("[WARN] lap rows endpoint missing in generated client; exporter will skip lap rows")

    events_resp = await get_events_for_org_async(org_id, client=client)
    if verbose:
        print(f"[DEBUG] events request status={getattr(events_resp,'status_code',None)} size={len(events_resp.content) if getattr(events_resp,'content',None) else 0}")
    events_payload = safe_load_json(getattr(events_resp, "content", None)) or []

    # Writers for streaming NDJSON output
    events_fh, events_write = ndjson_writer(out_dir / "events.ndjson", compress)
    sessions_fh, sessions_write = ndjson_writer(out_dir / "sessions.ndjson", compress)
    laps_fh, laps_write = ndjson_writer(out_dir / "laps.ndjson", compress)
    anns_fh, anns_write = ndjson_writer(out_dir / "announcements.ndjson", compress)

    import asyncio

    sem = asyncio.Semaphore(concurrency)

    async def fetch_and_write_for_event(ev: dict) -> None:
        ev_id = ev.get("id")
        ev_name = ev.get("name")
        base_event = {"org_id": org_id, "event_id": ev_id, "event_name": ev_name}
        # write event record
        events_write({**base_event, "raw": ev})

        async with sem:
            sresp = await get_sessions_for_event_async(ev_id, client=client)
        sess_payload = safe_load_json(getattr(sresp, "content", None)) or []
        raw_sessions: List[dict] = []
        if isinstance(sess_payload, list):
            raw_sessions = list(sess_payload)
        elif isinstance(sess_payload, dict):
            if isinstance(sess_payload.get("sessions"), list):
                raw_sessions.extend(sess_payload.get("sessions", []))
            for g in sess_payload.get("groups", []):
                for s_item in g.get("sessions", []) if isinstance(g.get("sessions"), list) else []:
                    raw_sessions.append(s_item)

        for s in raw_sessions:
            sid = s.get("id")
            sessions_write({**base_event, "session_id": sid, "raw": s})

        async def fetch_session_details(sdict: dict) -> None:
            sid = sdict.get("id")
            if not sid:
                return
            # announcements (optional)
            if HAVE_ANNOUNCEMENTS:
                async with sem:
                    aresp = await get_announcements_for_session_async(sid, client=client)
                a_payload = safe_load_json(getattr(aresp, "content", None))
                if a_payload:
                    anns_write({**base_event, "session_id": sid, "announcements": a_payload})
            else:
                if verbose:
                    print(f"[DEBUG] skipping announcements for session {sid} (endpoint missing)")

            # lap rows
            # lap rows (optional)
            if HAVE_LAP_ROWS:
                async with sem:
                    lresp = await get_lap_rows_async(sid, client=client)
                l_payload = safe_load_json(getattr(lresp, "content", None))
                if l_payload:
                    # normalize rows if wrapped
                    rows = []
                    if isinstance(l_payload, dict) and isinstance(l_payload.get("rows"), list):
                        rows = l_payload.get("rows", [])
                    elif isinstance(l_payload, list):
                        rows = l_payload
                    laps_write({**base_event, "session_id": sid, "rows_count": len(rows), "rows": rows})
            else:
                if verbose:
                    print(f"[DEBUG] skipping lap rows for session {sid} (endpoint missing)")

        # Fetch session details sequentially to limit memory/parallel in low-RAM systems
        for s in raw_sessions:
            await fetch_session_details(s)

    # Process events sequentially to keep memory low; you can increase concurrency if you have more RAM
    for ev in events_payload:
        await fetch_and_write_for_event(ev)

    # Close file handles
    events_fh.close()
    sessions_fh.close()
    laps_fh.close()
    anns_fh.close()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export a full dump for provided organization ids")
    parser.add_argument("--org", type=int, action="append", help="Organization id (can be repeated)")
    parser.add_argument("--org-file", type=Path, help="Path to newline-separated file containing org ids")
    parser.add_argument("--output", type=Path, default=Path("output/full_dump"), help="Output directory")
    parser.add_argument("--token", help="API token", default=None)
    parser.add_argument("--concurrency", "-c", type=int, default=2, help="Max concurrent requests (small default for low RAM)")
    parser.add_argument("--no-compress", dest="compress", action="store_false", help="Do not gzip output files")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    orgs: List[int] = []
    if args.org:
        orgs.extend(args.org)
    if args.org_file:
        if args.org_file.exists():
            for line in args.org_file.read_text(encoding="utf8").splitlines():
                line = line.strip()
                if line:
                    try:
                        orgs.append(int(line))
                    except Exception:
                        pass

    if not orgs:
        print("Provide at least one --org or --org-file with organization ids")
        return 2

    client = build_client(token=args.token)

    import asyncio

    async def _run():
        async with client:
            for org_id in orgs:
                out_dir = args.output / str(org_id)
                if args.verbose:
                    print(f"Starting export for org {org_id} -> {out_dir}")
                await export_org(org_id, out_dir, client=client, verbose=args.verbose, concurrency=args.concurrency, compress=args.compress)

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
