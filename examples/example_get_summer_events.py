"""Example: list events for an organization that took place in the summer (Jun-Aug).

Usage:
    python examples/example_get_summer_events.py --org 30476
    python examples/example_get_summer_events.py --org 30476 --year 2024 --token YOURTOKEN

The script uses `SpeedhiveClient.iter_events` to stream events, extracts their
start date (best-effort using common keys), and prints events whose start
month is June, July or August.
"""
from __future__ import annotations

import argparse
from datetime import date
from typing import Optional

from dateutil import parser as date_parser

from mylaps_client_wrapper import SpeedhiveClient


SUMMER_MONTHS = {6, 7, 8}


def _extract_event_date(event: dict) -> Optional[date]:
    """Return a date object for an event if a parseable date is found.

    Tries several common keys used by the API; returns None if none parse.
    """
    candidates = (
        "date",
        "startDate",
        "start",
        "start_time",
        "startDateTime",
        "startDateTimeUTC",
        "dateTime",
    )
    for key in candidates:
        val = event.get(key)
        if not val:
            continue
        try:
            dt = date_parser.parse(str(val))
            return dt.date()
        except Exception:
            continue
    # As a last attempt, check nested sessions for a session date
    sessions = event.get("sessions") or []
    if isinstance(sessions, list):
        for s in sessions:
            for key in ("date", "start", "startDate", "dateTime"):
                val = s.get(key) if isinstance(s, dict) else None
                if not val:
                    continue
                try:
                    dt = date_parser.parse(str(val))
                    return dt.date()
                except Exception:
                    continue
    return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="List summer events (Jun-Aug) for an org")
    parser.add_argument("--org", type=int, required=True, help="Organization id")
    parser.add_argument("--token", help="API token (optional)")
    parser.add_argument("--year", type=int, help="Optional year to filter (e.g., 2024)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)

    found = 0
    for event in client.iter_events(org_id=args.org):
        edate = _extract_event_date(event)
        if not edate:
            # skip events without a parseable date
            continue
        if edate.month not in SUMMER_MONTHS:
            continue
        if args.year and edate.year != args.year:
            continue

        print(f"{event.get('id')}: {event.get('name')} — {edate.isoformat()}")
        found += 1

    if found == 0:
        print("No summer events found for the given organization and filters.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
