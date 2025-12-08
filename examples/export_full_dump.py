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
from typing import Any, Iterable, List, Optional, Callable, Awaitable, Dict, Set, cast
import time
import os
import inspect

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "mylaps_client"))

from event_results_client import Client, AuthenticatedClient

# Some generated client versions may not expose every endpoint path we try to use.
# Import endpoint callables in try/except blocks so the module can be imported
# even if a particular generated function is missing. At runtime we check and
# provide a clear error message if a required endpoint is not available.
get_events_for_org_async: Optional[Callable[..., Awaitable[Any]]] = None
try:
    from event_results_client.api.organization_controller.get_event_list import asyncio_detailed as get_events_for_org_async
except Exception:
    get_events_for_org_async = None

get_sessions_for_event_async: Optional[Callable[..., Awaitable[Any]]] = None
try:
    from event_results_client.api.event_controller.get_session_list import asyncio_detailed as get_sessions_for_event_async
except Exception:
    get_sessions_for_event_async = None

get_announcements_for_session_async: Optional[Callable[..., Awaitable[Any]]] = None
try:
    from event_results_client.api.session_controller.get_announcements import asyncio_detailed as get_announcements_for_session_async
except Exception:
    get_announcements_for_session_async = None

# The generated client may expose lap data under multiple endpoint names.
# Try a few common variants and pick the first one that exists.
get_lap_rows_async: Optional[Callable[..., Awaitable[Any]]] = None
for candidate in (
    "get_all_lap_times",
    "get_lap_times",
    "get_lap_csv",
    "get_lap_chart",
):
    try:
        mod = __import__(f"event_results_client.api.session_controller.{candidate}", fromlist=["*"])
        candidate_callable = getattr(mod, "asyncio_detailed", None)
        if callable(candidate_callable):
            # Wrap the chosen callable so callers can always use (session_id, client)
            sig = inspect.signature(candidate_callable)

            # Capture candidate_callable and sig into defaults to avoid late-binding
            async def _wrapped(session_id: int, *, client: Client, _call=candidate_callable, _sig=sig):
                kwargs = {"id": session_id, "client": client}
                # If the signature expects additional named params, provide safe defaults
                for p in _sig.parameters.values():
                    if p.name in ("id", "client"):
                        continue
                    if p.default is not inspect._empty:
                        # parameter has default, skip
                        continue
                    # provide a conservative default for common numeric params
                    kwargs[p.name] = 0

                return await _call(**kwargs)

            get_lap_rows_async = _wrapped
            break
    except Exception:
        get_lap_rows_async = None


def build_client(token: Optional[str] = None) -> Client | AuthenticatedClient:
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


async def export_org(org_id: int, out_dir: Path, client: Client, verbose: bool = False, concurrency: int = 3, compress: bool = True, max_events: Optional[int] = None, max_sessions_per_event: Optional[int] = None, dry_run: bool = False, show_progress: bool = True, resume: bool = True, checkpoint_arg: Optional[Path] = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Check availability of endpoint helper callables and decide what we can do.
    HAVE_EVENTS = callable(get_events_for_org_async)
    HAVE_SESSIONS = callable(get_sessions_for_event_async)
    HAVE_ANNOUNCEMENTS = callable(get_announcements_for_session_async)
    HAVE_LAP_ROWS = callable(get_lap_rows_async)

    # After checking availability, cast to callables for type-checkers
    get_events = cast(Callable[..., Awaitable[Any]], get_events_for_org_async) if HAVE_EVENTS else None
    get_sessions = cast(Callable[..., Awaitable[Any]], get_sessions_for_event_async) if HAVE_SESSIONS else None
    get_announcements = cast(Optional[Callable[..., Awaitable[Any]]], get_announcements_for_session_async) if HAVE_ANNOUNCEMENTS else None
    get_lap_rows = cast(Optional[Callable[..., Awaitable[Any]]], get_lap_rows_async) if HAVE_LAP_ROWS else None

    if not HAVE_EVENTS:
        raise RuntimeError("Required endpoint function `get_events_for_org_async` is not available in the generated client. Regenerate the client or add the missing endpoint.")
    if not HAVE_SESSIONS:
        raise RuntimeError("Required endpoint function `get_sessions_for_event_async` is not available in the generated client. Regenerate the client or add the missing endpoint.")

    if not HAVE_ANNOUNCEMENTS and verbose:
        print("[WARN] announcements endpoint missing in generated client; exporter will skip announcements")
    if not HAVE_LAP_ROWS and verbose:
        print("[WARN] lap rows endpoint missing in generated client; exporter will skip lap rows")

    events_resp = await get_events(org_id, client=client)
    if verbose:
        print(f"[DEBUG] events request status={getattr(events_resp,'status_code',None)} size={len(events_resp.content) if getattr(events_resp,'content',None) else 0}")
    events_payload = safe_load_json(getattr(events_resp, "content", None)) or []
    if max_events is not None:
        events_payload = events_payload[:max_events]

    total_events = len(events_payload)
    events_start = time.monotonic()

    # checkpoint / resume support
    def _checkpoint_path(checkpoint_arg: Optional[Path]) -> Path:
        if checkpoint_arg:
            return checkpoint_arg
        return out_dir / ".checkpoint.json"

    def _load_checkpoint(path: Path) -> dict:
        if not path.exists():
            return {"events_processed": [], "sessions_processed": {}}
        try:
            return json.loads(path.read_text(encoding="utf8"))
        except Exception:
            return {"events_processed": [], "sessions_processed": {}}

    def _save_checkpoint(path: Path, data: dict) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf8")
        os.replace(tmp, path)

    ckpt_path = _checkpoint_path(checkpoint_arg)
    checkpoint: dict = {"events_processed": [], "sessions_processed": {}}
    if ckpt_path.exists():
        checkpoint = _load_checkpoint(ckpt_path)

    events_processed = set(checkpoint.get("events_processed", []))
    sessions_processed = {int(k): set(v) for k, v in checkpoint.get("sessions_processed", {}).items()}

    # simple logging to a file for long runs
    log_path = out_dir / "export.log"
    def _log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} {msg}\n"
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf8") as fh:
                fh.write(line)
        except Exception:
            pass
        if verbose:
            print(msg)

    # Writers for streaming NDJSON output
    events_fh, events_write = ndjson_writer(out_dir / "events.ndjson", compress)
    sessions_fh, sessions_write = ndjson_writer(out_dir / "sessions.ndjson", compress)
    laps_fh, laps_write = ndjson_writer(out_dir / "laps.ndjson", compress)
    anns_fh, anns_write = ndjson_writer(out_dir / "announcements.ndjson", compress)

    import asyncio

    sem = asyncio.Semaphore(concurrency)

    async def fetch_and_write_for_event(ev: dict, event_index: int) -> None:
        ev_id = ev.get("id")
        if ev_id is None:
            _log(f"[WARN] skipping event with missing id: {ev}")
            return
        ev_id = int(ev_id)
        ev_name = ev.get("name")
        base_event = {"org_id": org_id, "event_id": ev_id, "event_name": ev_name}
        # skip if already completed in checkpoint
        if ev_id in events_processed:
            _log(f"[SKIP] event {ev_id} already processed in checkpoint")
            if show_progress:
                print(f"[PROGRESS] Skipping event {event_index}/{total_events}: id={ev_id} (already done)")
            return
        # write event record
        events_write({**base_event, "raw": ev})

        if show_progress:
            print(f"[PROGRESS] Event {event_index}/{total_events}: id={ev_id} name={ev_name}")

        async with sem:
            sresp = await get_sessions(ev_id, client=client)
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

        # optionally limit sessions per event for low-RAM / testing
        if max_sessions_per_event is not None:
            raw_sessions = raw_sessions[:max_sessions_per_event]

        # optionally limit sessions per event for low-RAM / testing
        if max_sessions_per_event is not None:
            raw_sessions = raw_sessions[:max_sessions_per_event]

        for s in raw_sessions:
            sid = s.get("id")
            if sid is None:
                continue
            sid = int(sid)
            sessions_write({**base_event, "session_id": sid, "raw": s})

        # Prepare per-event session progress tracking
        session_count = len(raw_sessions)
        session_done = 0
        session_start_time = None

        async def fetch_session_details(sdict: dict) -> None:
            sid = sdict.get("id")
            if sid is None:
                return
            sid = int(sid)
            nonlocal session_done, session_start_time
            # skip session if already processed in checkpoint
            if sid in sessions_processed.get(ev_id, set()):
                _log(f"[SKIP] session {sid} for event {ev_id} already processed in checkpoint")
                session_done += 1
                return
            # start timer when first session begins
            if session_start_time is None:
                session_start_time = time.monotonic()
            t0 = time.monotonic()
            # announcements (optional)
            if HAVE_ANNOUNCEMENTS and get_announcements is not None:
                async with sem:
                    aresp = await get_announcements(sid, client=client)
                a_payload = safe_load_json(getattr(aresp, "content", None))
                if a_payload:
                    anns_write({**base_event, "session_id": sid, "announcements": a_payload})
            else:
                if verbose:
                    print(f"[DEBUG] skipping announcements for session {sid} (endpoint missing)")

            # lap rows
            # lap rows (optional)
            if HAVE_LAP_ROWS and get_lap_rows is not None:
                async with sem:
                    lresp = await get_lap_rows(sid, client=client)
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

            # update progress counters and ETA for current event
            session_done += 1
            elapsed = time.monotonic() - session_start_time if session_start_time else 0
            avg = (elapsed / session_done) if session_done else 0
            remaining = session_count - session_done
            eta = avg * remaining
            if show_progress:
                print(f"[PROGRESS] event {ev_id} sessions {session_done}/{session_count} — ETA {eta:.1f}s")
            # update checkpoint after successful session processing (unless dry-run)
            if not dry_run:
                sessions_processed.setdefault(ev_id, set()).add(sid)
                out_ckpt = {"events_processed": list(events_processed), "sessions_processed": {str(k): list(v) for k, v in sessions_processed.items()}}
                try:
                    _save_checkpoint(ckpt_path, out_ckpt)
                except Exception:
                    _log(f"[WARN] failed to write checkpoint to {ckpt_path}")

        # If dry-run, don't fetch announcements or laps — just report counts
        if dry_run:
            if verbose:
                print(f"[DRY-RUN] event {ev_id} has {len(raw_sessions)} sessions (skipping details)")
        else:
            # Fetch session details sequentially to limit memory/parallel in low-RAM systems
            for s in raw_sessions:
                await fetch_session_details(s)
        # mark event complete in checkpoint and persist
        events_processed.add(ev_id)
        if not dry_run:
            out_ckpt = {"events_processed": list(events_processed), "sessions_processed": {str(k): list(v) for k, v in sessions_processed.items()}}
            try:
                _save_checkpoint(ckpt_path, out_ckpt)
            except Exception:
                _log(f"[WARN] failed to write checkpoint to {ckpt_path}")

        if show_progress:
            evt_elapsed = time.monotonic() - (events_start if events_start else time.monotonic())
            print(f"[PROGRESS] finished event {event_index}/{total_events} id={ev_id} (event time {evt_elapsed:.1f}s)")
        _log(f"[INFO] finished event {ev_id}")

    # Process events sequentially to keep memory low; you can increase concurrency if you have more RAM
    for idx, ev in enumerate(events_payload, start=1):
        await fetch_and_write_for_event(ev, idx)

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
    parser.add_argument("--max-events", type=int, default=None, help="Limit to N events (for testing)")
    parser.add_argument("--max-sessions-per-event", type=int, default=None, help="Limit sessions per event (for testing)")
    parser.add_argument("--dry-run", action="store_true", help="Don't fetch announcements/laps; just list counts and exit")
    parser.add_argument("--no-progress", action="store_true", help="Disable progress printing")
    parser.add_argument("--checkpoint", type=Path, default=None, help="Path to checkpoint file (default: outdir/.checkpoint.json)")
    parser.add_argument("--no-resume", action="store_true", help="Do not resume from existing checkpoint; start fresh")
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
            for idx, org_id in enumerate(orgs, start=1):
                out_dir = args.output / str(org_id)
                if args.verbose:
                    print(f"Starting export for org {org_id} -> {out_dir}")
                await export_org(
                    org_id,
                    out_dir,
                    client=client,
                    verbose=args.verbose,
                    concurrency=args.concurrency,
                    compress=args.compress,
                    max_events=args.max_events,
                    max_sessions_per_event=args.max_sessions_per_event,
                    dry_run=args.dry_run,
                    show_progress=not getattr(args, "no_progress", False),
                    resume=not args.no_resume,
                    checkpoint_arg=args.checkpoint,
                )

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
