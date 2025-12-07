"""Example: list events for a given organization name or ID.

Features:
- Accepts either an organization name (partial match by default) or a numeric
  organization ID.
- Supports `--token` to provide an API token for authenticated endpoints.
- Uses an absolute path to the generated `mylaps_client` folder so the script
  can be run from any working directory.

Usage examples:
  python examples/list_events_by_org.py "Waterford Hills Road Racing Inc"
  python examples/list_events_by_org.py 30476
  python examples/list_events_by_org.py "Waterford" --partial
  python examples/list_events_by_org.py 30476 --token YOUR_TOKEN
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Optional

# Add generated client package (absolute path) so script works from any cwd
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "mylaps_client"))

from event_results_client import Client, AuthenticatedClient
from event_results_client.models.event import Event
from event_results_client.api.event_controller.get_event_list_1 import sync_detailed as get_events_v2
from event_results_client.api.organization_controller.get_event_list import sync_detailed as get_events_for_org
from event_results_client.api.organization_controller.get_event_list_3 import sync_detailed as get_events_for_org_no_v2


def list_events_for_organization(
    organization_name: str,
    client: Optional[Client] = None,
    page_size: int = 100,
    partial: bool = True,
    verbose: bool = False,
) -> List[Event]:
    """Return events belonging to `organization_name` by scanning `/v2/events`.

    By default `partial=True` performs a case-insensitive substring match on
    `event.organization.name`.
    """
    client = client or Client(base_url="https://api2.mylaps.com")

    matched: List[Event] = []
    offset = 0

    def _normalize(text: str) -> str:
        import re

        return re.sub(r"[^0-9a-zA-Z]+", " ", text or "").strip().lower()

    needle = _normalize(organization_name)

    while True:
        resp = get_events_v2(client=client, count=page_size, offset=offset)
        if verbose:
            print(f"[DEBUG] paged request offset={offset} status={getattr(resp,'status_code',None)} size={len(resp.content) if resp.content else 0}")
            try:
                snippet = resp.content.decode('utf-8', errors='replace')[:500]
            except Exception:
                snippet = str(resp.content)[:500]
            print("[DEBUG] snippet:", snippet)
        if not resp.content:
            break

        try:
            payload = json.loads(resp.content)
        except Exception:
            break

        if not isinstance(payload, Iterable):
            break

        items = list(payload)
        if not items:
            break

        for item in items:
            try:
                # Some nested fields can be null in the API response (for example
                # `sessions: null`). The generated `from_dict` helpers expect a
                # mapping and will raise if passed None — normalize those here.
                if item.get("sessions") is None:
                    item = dict(item)
                    item["sessions"] = {}
                ev = Event.from_dict(item)
            except Exception:
                continue

            org = ev.organization
            if not getattr(org, "name", None):
                continue

            if not getattr(org, "name", None):
                continue

            hay = _normalize(org.name)
            if partial:
                if needle in hay:
                    matched.append(ev)
            else:
                if hay == needle:
                    matched.append(ev)

        if len(items) < page_size:
            break

        offset += page_size

    return matched


def list_events_for_org_id(org_id: int, client: Client) -> List[Event]:
    """Return events for organization id by calling `/v2/organizations/{id}/events`."""
    # Try v2 endpoint first
    resp = get_events_for_org(org_id, client=client)
    # If no content, try the non-v2 endpoint
    if not resp.content:
        resp = get_events_for_org_no_v2(org_id, client=client)
    return resp

    try:
        payload = json.loads(resp.content)
    except Exception:
        return []

    items = list(payload) if isinstance(payload, Iterable) else []
    events: List[Event] = []
    for item in items:
        try:
            events.append(Event.from_dict(item))
        except Exception:
            continue

    return events


def build_client(base_url: str = "https://api2.mylaps.com", token: Optional[str] = None) -> Client:
    if token:
        return AuthenticatedClient(base_url=base_url, token=token)
    return Client(base_url=base_url)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="List events for an organization (name or id)")
    parser.add_argument("query", help="Organization name (string) or organization id (integer)")
    parser.add_argument("--token", help="API token for authenticated endpoints", default=None)
    parser.add_argument("--partial", help="Use partial (substring) matching for organization name", action="store_true")
    parser.add_argument("--no-partial", help="Use exact match for organization name", dest="partial", action="store_false")
    parser.add_argument("--verbose", help="Print debug information about HTTP responses", action="store_true")
    parser.set_defaults(partial=True)
    args = parser.parse_args(argv)

    client = build_client(token=args.token)

    if args.query.isdigit():
        org_id = int(args.query)
        resp = list_events_for_org_id(org_id, client=client)
        # resp is a generated Response object; parse similar to other code paths
        if not getattr(resp, 'content', None):
            if args.token or args.verbose:
                print(f"[DEBUG] org-id request status={getattr(resp,'status_code',None)} size=0")
            events = []
        else:
            if args.verbose:
                print(f"[DEBUG] org-id request status={getattr(resp,'status_code',None)} size={len(resp.content)}")
                try:
                    print("[DEBUG] snippet:", resp.content.decode('utf-8', errors='replace')[:500])
                except Exception:
                    print("[DEBUG] content (raw):", resp.content[:200])
            try:
                payload = json.loads(resp.content)
            except Exception:
                payload = []
            items = list(payload) if isinstance(payload, Iterable) else []
            events = []
            for item in items:
                try:
                    if item.get("sessions") is None:
                        item = dict(item)
                        item["sessions"] = {}
                    events.append(Event.from_dict(item))
                except Exception:
                    continue
    else:
        events = list_events_for_organization(args.query, client=client, partial=args.partial, verbose=args.verbose)

    if not events:
        print("No events found for:", args.query)
        return 0

    for ev in events:
        start = getattr(ev.start_date, "isoformat", lambda: ev.start_date)()
        print(f"{ev.id}: {ev.name} ({start})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
