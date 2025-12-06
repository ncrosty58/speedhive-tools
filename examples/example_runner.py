
#!/usr/bin/env python3
"""
example_runner.py
Quick-start runner for Speedhive tools.

Run examples:

    # Fetch organization details
    python example_runner.py org 30476

    # List organization events (top 5 shown)
    python example_runner.py events 30476 --per-page 50 --top 5 --out out/events.json

    # Fetch event results
    python example_runner.py event-results 123456 --out out/event_123456.json

    # Fetch track records by organization and export
    python example_runner.py records 30476 --json out/wh_records.json --csv out/wh_records.csv --show-seconds

    # Parse a single "New Track Record" announcement string
    python example_runner.py parse-announcement --text "New Track Record – FA – 1:01.861 – J. Lewis Cooper, Jr – Swift 01 4A – 2009-05-10" --json out/parsed.json

    # Parse announcements from a file (one per line)
    python example_runner.py parse-announcement --file announcements.txt --csv out/parsed.csv

Environment overrides (optional):
    SPEEDHIVE_BASE_URL
    SPEEDHIVE_USER_AGENT
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import List, Optional

# Import from your package
from speedhive_tools.client import SpeedHiveClient, SpeedHiveAPIError
from speedhive_tools.models import TrackRecord, EventResult, Organization
from speedhive_tools.utils import (
    write_json,
    write_csv,
    try_parse_track_record_announcement,
    parse_lap_time_to_seconds,
)

# ------------------------------------------------------------------------------
# Pretty printers
# ------------------------------------------------------------------------------

def print_organization(org: Organization) -> None:
    print(f"Organization #{org.org_id} – {org.name}")
    if org.country:
        print(f"  Country: {org.country}")
    if org.website:
        print(f"  Website: {org.website}")


def print_event_result(event: EventResult) -> None:
    print(f"Event #{event.event_id} – {event.event_name}")
    print(f"  Track: {event.track_name}")
    print(f"  Start: {event.start_date}")
    print(f"  End:   {event.end_date}")
    if event.records:
        print(f"  Records: {len(event.records)}")
        for r in event.records[:5]:
            cls = getattr(r, "class_name", None) or "n/a"
            print(f"    - {r.driver_name} {r.lap_time} ({cls}) on {r.date}")


def print_records(records: List[TrackRecord], *, show_seconds: bool = False) -> None:
    if not records:
        print("No records found.")
        return

    print(f"Records ({len(records)}):")
    for r in records:
        cls = getattr(r, "class_name", None) or "n/a"
        base = f"  - {r.driver_name} | {r.lap_time} | {cls} | {r.date}"
        if show_seconds:
            try:
                seconds = parse_lap_time_to_seconds(str(r.lap_time))
                base += f"  ({seconds:.3f}s)"
            except Exception:
                base += "  (seconds: n/a)"
        print(base)

# ------------------------------------------------------------------------------
# Handlers
# ------------------------------------------------------------------------------

def handle_org(args: argparse.Namespace, client: SpeedHiveClient) -> None:
    org_id = int(args.org_id)
    org = client.get_organization(org_id)
    print_organization(org)
    if args.out:
        write_json(org.model_dump(), args.out)
        print(f"Saved organization JSON -> {args.out}")


def handle_events(args: argparse.Namespace, client: SpeedHiveClient) -> None:
    org_id = int(args.org_id)
    events = client.list_organization_events(org_id, per_page=args.per_page, max_pages=args.max_pages)
    print(f"Found {len(events)} events for org {org_id}")
    for e in events[: args.top]:
        print_event_result(e)
    if args.out:
        write_json([e.model_dump() for e in events], args.out)
        print(f"Saved events JSON -> {args.out}")


def handle_event_results(args: argparse.Namespace, client: SpeedHiveClient) -> None:
    event_id = int(args.event_id)
    result = client.get_event_results(event_id)
    print_event_result(result)
    if args.out:
        write_json(result.model_dump(), args.out)
        print(f"Saved event results JSON -> {args.out}")


def handle_records(args: argparse.Namespace, client: SpeedHiveClient) -> None:
    org_id = int(args.org_id)
    records = client.get_track_records_by_org(org_id)
    print_records(records, show_seconds=args.show_seconds)

    if args.json:
        write_json({"records": [r.model_dump() for r in records]}, args.json)
        print(f"Saved records JSON -> {args.json}")

    if args.csv:
        write_csv([r.model_dump() for r in records], args.csv)
        print(f"Saved records CSV -> {args.csv}")


def handle_parse_announcement(args: argparse.Namespace) -> None:
    texts: List[str] = []

    if args.text:
        texts.append(args.text)

    if args.file:
        if not os.path.exists(args.file):
            print(f"File not found: {args.file}")
            sys.exit(2)
        with open(args.file, "r", encoding="utf-8") as f:
            texts.extend([line.strip() for line in f if line.strip()])

    if not texts:
        print("No input provided. Use --text or --file.")
        sys.exit(2)

    parsed = []
    for t in texts:
        result = try_parse_track_record_announcement(t)
        if result:
            parsed.append(result)
            try:
                seconds = parse_lap_time_to_seconds(result["lapTime"])
                print(
                    f"OK: {result['driverName']} | {result['classAbbreviation']} | "
                    f"{result['lapTime']} ({seconds:.3f}s) | {result['date']} | {result['marque']}"
                )
            except Exception:
                print(
                    f"OK: {result['driverName']} | {result['classAbbreviation']} | "
                    f"{result['lapTime']} | {result['date']} | {result['marque']}"
                )
        else:
            print(f"SKIP: Could not parse -> {t}")

    if args.json:
        write_json({"records": parsed}, args.json)
        print(f"Saved parsed announcements JSON -> {args.json}")

    if args.csv:
        write_csv(parsed, args.csv)
        print(f"Saved parsed announcements CSV -> {args.csv}")

# ------------------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="example_runner.py",
        description="Quick runner for Speedhive tools",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    sub = p.add_subparsers(dest="command", required=True)

    # org
    p_org = sub.add_parser("org", help="Fetch organization details")
    p_org.add_argument("org_id", help="Organization ID (e.g., 30476)")
    p_org.add_argument("--out", type=str, default=None, help="Optional JSON output path")
    p_org.set_defaults(func=handle_org)

    # events
    p_events = sub.add_parser("events", help="List events for an organization")
    p_events.add_argument("org_id", help="Organization ID")
    p_events.add_argument("--per-page", type=int, default=50, help="Page size")
    p_events.add_argument("--max-pages", type=int, default=None, help="Max pages to fetch")
    p_events.add_argument("--top", type=int, default=5, help="Show top N events")
    p_events.add_argument("--out", type=str, default=None, help="Optional JSON output path")
    p_events.set_defaults(func=handle_events)

    # event-results
    p_ev = sub.add_parser("event-results", help="Fetch results for a specific event")
    p_ev.add_argument("event_id", help="Event ID")
    p_ev.add_argument("--out", type=str, default=None, help="Optional JSON output path")
    p_ev.set_defaults(func=handle_event_results)

    # records
    p_rec = sub.add_parser("records", help="Fetch track records for an organization")
    p_rec.add_argument("org_id", help="Organization ID")
    p_rec.add_argument("--json", type=str, default=None, help="Save records JSON to path")
    p_rec.add_argument("--csv", type=str, default=None, help="Save records CSV to path")
    p_rec.add_argument("--show-seconds", action="store_true", help="Show numeric seconds next to lap time")
    p_rec.set_defaults(func=handle_records)

    # parse-announcement
    p_pa = sub.add_parser("parse-announcement", help="Parse 'New Track Record' announcements")
    p_pa.add_argument("--text", type=str, help="Single announcement text")
    p_pa.add_argument("--file", type=str, help="Text file with one announcement per line")
    p_pa.add_argument("--json", type=str, default=None, help="Save parsed JSON to path")
    p_pa.add_argument("--csv", type=str, default=None, help="Save parsed CSV to path")
    p_pa.set_defaults(func=handle_parse_announcement)

    return p


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Initialize client (no auth required)
    client = SpeedHiveClient()

    try:
        # Handlers that don't need the client still receive it; they can ignore.
        args.func(args, client)  # type: ignore[arg-type]
    except SpeedHiveAPIError as e:
        logging.error("API error: %s", e)
        sys.exit(1)
    except KeyboardInterrupt:
        print("Cancelled.")
        sys.exit(130)


if __name__ == "__main__":
    main()
