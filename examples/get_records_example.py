
#!/usr/bin/env python3
"""
Verbose exporter for Waterford Hills (org 30476).
Shows live progress, limits traversal scope, and writes incremental results.

Usage examples:
  # Small, fast dev run
  python examples/get_records_example.py --org-id 30476 --max-events 5 --max-sessions-per-event 20 --rate-delay 0 --timeout 10

  # Show raw announcement rows for debugging
  python examples/get_records_example.py --show_raw

  # Try health check against an explicit root (optional)
  python examples/get_records_example.py --health-check --health-root https://eventresultsapi-eu-prd-app01.azurewebsites.net
"""

from __future__ import annotations
from pathlib import Path
import json
import sys
import time
import argparse

from speedhive_tools.client import SpeedHiveClient, SpeedHiveAPIError


def parse_record_from_text(text: str) -> dict | None:
    """
    Very simple parser – adapt to your existing regexes if you already
    have them in speedhive-tools. Expected tokens often look like:
      "New Track Record - Class: SRF3, Driver: Larry Winkelman, Car: SCCA Enterprises SRF3, Lap: 1:11.816, Date: 2025-05-25"
    """
    import re
    def _m(p):
        m = re.search(p, text or "", flags=re.IGNORECASE)
        return m.group(1).strip() if m else None

    if not text:
        return None

    if re.search(r"\bNew\b.*\bTrack\b.*\bRecord\b", text, re.IGNORECASE):
        return {
            "classAbbreviation": _m(r"Class:\s*([A-Za-z0-9\-]+)"),
            "lapTime": _m(r"Lap:\s*([0-9:\.]+)"),
            "driverName": _m(r"Driver:\s*([A-Za-z\.\s,'-]+)"),
            "marque": _m(r"Car:\s*([A-Za-z0-9\.\s,'\-]+)"),
            "date": _m(r"Date:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})")
        }
    return None


def log(msg: str) -> None:
    print(msg, flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List and export Waterford Hills track-record announcements.")
    parser.add_argument("--org-id", type=int, default=30476, help="Organization ID (default: 30476 Waterford Hills)")
    parser.add_argument("--api-key", type=str, default=None, help="Speedhive API key if your environment requires it")
    parser.add_argument("--base-url", type=str, default=None,
                        help="Override base URL, e.g. https://eventresults-api.speedhive.com/api/v0.2.3/eventresults")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout in seconds (default: 20)")
    parser.add_argument("--retries", type=int, default=1, help="Retries for 5xx/network errors (default: 1)")
    parser.add_argument("--rate-delay", type=float, default=0.05, help="Delay between requests (seconds, default: 0.05)")
    parser.add_argument("--max-events", type=int, default=20, help="Limit number of events traversed (default: 20)")
    parser.add_argument("--max-sessions-per-event", type=int, default=200, help="Limit sessions per event (default: 200)")
    parser.add_argument("--out-json", type=Path, default=Path("waterford_hills_records.json"),
                        help="Output JSON path")
    parser.add_argument("--print-every", type=int, default=1, help="Emit a status line every N sessions (default: 1)")
    parser.add_argument("--show_raw", action="store_true", help="Print raw announcements for debugging")  # <-- underscore!
    parser.add_argument("--health-check", action="store_true", help="Perform a health check against --health-root")
    parser.add_argument("--health-root", type=str, default=None,
                        help="Root URL where /api/health exists (e.g. https://eventresultsapi-eu-prd-app01.azurewebsites.net)")
    args = parser.parse_args(argv)

    # Construct client (use default base unless overridden)
    client_kwargs = dict(api_key=args.api_key, timeout=args.timeout, retries=args.retries, rate_delay=args.rate_delay)
    if args.base_url:
        client_kwargs["base_url"] = args.base_url
    client = SpeedHiveClient(**client_kwargs)

    # Optional: health check (only works if you target the host root that exposes /api/health)
    if args.health_check and args.health_root:
        try:
            url = args.health_root.rstrip("/") + "/api/health"
            log(f"Performing API health check at {url} ...")
            # Bypass _build_url by calling session directly with a fully-qualified URL
            resp = client.session.request("GET", url, headers=client._headers(), timeout=args.timeout)
            if resp.status_code == 200:
                log("Health check OK.")
            else:
                log(f"Health check returned {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log(f"Health check failed: {e}")

    org_id = args.org_id
    log(f"Fetching events for org {org_id} ... (limit: {args.max_events})")
    try:
        events = client.get_events_for_org(org_id, count=args.max_events, offset=0)
    except SpeedHiveAPIError as e:
        log(f"Error fetching events for org {org_id}: {e}")
        return 2

    if not events:
        log("No events returned for the organization (try increasing --max-events or check network/API).")
        # Still write an empty JSON so callers don't error.
        args.out_json.write_text(json.dumps({"records": []}, indent=2), encoding="utf-8")
        log(f"Saved -> {args.out_json.resolve()}")
        return 0

    log(f"Found {len(events)} event(s). Traversing sessions and announcements ...")
    all_rows: list[dict] = []
    event_counter = 0

    try:
        for ev in events:
            event_counter += 1
            ev_id = ev.get("id") or ev.get("event_id")
            ev_name = ev.get("name") or ev.get("event_name") or f"event-{ev_id}"
            if not ev_id:
                log(f"  [{event_counter}/{len(events)}] Skipping event with no id: {ev}")
                continue

            log(f"  [{event_counter}/{len(events)}] Sessions for event {ev_id} ({ev_name}) ...")
            try:
                sessions = client.get_sessions_for_event(int(ev_id))
            except SpeedHiveAPIError as e:
                log(f"    Error fetching sessions for event {ev_id}: {e}")
                continue

            if not sessions:
                log("    No sessions.")
                continue

            log(f"    {len(sessions)} session(s) (capped at {args.max_sessions_per_event})")
            sessions = sessions[: args.max_sessions_per_event]

            for i, s in enumerate(sessions, start=1):
                sid = s.get("id")
                sname = s.get("name") or f"session-{sid}"
                if i % args.print_every == 0:
                    log(f"      [{i}/{len(sessions)}] Announcements for session {sid} ({sname}) ...")
                if not sid:
                    log("      Skipping session with no id.")
                    continue
                try:
                    dto_rows = client.get_session_announcements(int(sid))
                except SpeedHiveAPIError as e:
                    log(f"      Error fetching announcements for session {sid}: {e}")
                    continue

                if args.show_raw and dto_rows:  # <-- underscore attribute
                    for r in dto_rows:
                        log(f"        RAW: {r}")

                # Tag rows with event/session names to make output readable
                for r in dto_rows or []:
                    r["eventName"] = ev_name
                    r["eventId"] = ev_id
                    r["sessionName"] = sname

                all_rows.extend(dto_rows or [])
    except KeyboardInterrupt:
        log("\nInterrupted by user; writing partial results ...")

    log(f"Collected {len(all_rows)} announcement row(s). Filtering for 'Track Record' ...")
    track_rows = [r for r in all_rows if client.find_track_record_announcements(r.get("text"))]
    log(f"Matched {len(track_rows)} 'Track Record' announcement(s).")

    # Print human-friendly lines
    for r in track_rows:
        ts = r.get("timestamp")
        evn = r.get("eventName")
        sn = r.get("sessionName")
        txt = r.get("text")
        log(f"[{ts}] {evn} / {sn}: {txt}")

    # Normalize to your README-style structure
    normalized: list[dict] = []
    for r in track_rows:
        parsed = parse_record_from_text(r.get("text", ""))
        if parsed:
            normalized.append(parsed)

    out_payload = {"records": normalized}
    args.out_json.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")
    log(f"\nSaved -> {args.out_json.resolve()}")

    # If nothing matched, still exit 0 (script succeeded, just no records found)
    if not normalized:
        log("Note: no parsable 'New Track Record' lines were found. You may need to tweak the regex parser.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
