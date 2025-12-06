
#!/usr/bin/env python3
"""
api_usage_demo.py
Demonstrates how to use SpeedhiveClient with typed models for real API calls.
"""

# --- path bootstrap: make the repo root importable when running from examples/
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
# --- end bootstrap

from speedhive_tools.client import SpeedHiveClient
from speedhive_tools.models import EventsPage, Event, AnnouncementsPage, Announcement

def main():
    client = SpeedHiveClient()

    # 1) List events across sport filters
    data = client._get("events", params={"sport": "All", "sportCategory": "Motorized", "count": 25, "offset": 0})
    page = EventsPage.model_validate(data)
    events: list[Event] = page.items
    print(f"Fetched {len(events)} events")
    for e in events[:5]:
        print(f"- {e.display_name} ({e.start_date} to {e.end_date})")

    # 2) List events for an organization
    org_id = 30476
    data = client._get(f"organizations/{org_id}/events", params={"count": 25, "offset": 0, "sportCategory": "Motorized"})
    org_page = EventsPage.model_validate(data)
    org_events = org_page.items
    print(f"Organization {org_id} has {len(org_events)} events")
    if org_events:
        print(f"  Example: {org_events[0].display_name}")

    # 3) Event with sessions
    if org_events:
        event_id = org_events[0].resolved_id
        data = client._get(f"events/{event_id}", params={"sessions": "true"})
        event = Event.model_validate(data)
        sessions = event.sessions or []
        print(f"Event {event.display_name} has {len(sessions)} sessions")

        # 4) Session announcements (track records)
        if sessions:
            session_id = sessions[0].resolved_id
            ann_data = client._get(f"sessions/{session_id}/announcements")
            ann_page = AnnouncementsPage.model_validate(ann_data)
            announcements: list[Announcement] = ann_page.items
            print(f"Session {session_id} has {len(announcements)} announcements")
            for a in announcements[:3]:
                print(f"  - {a.driver_name} | {a.class_abbreviation} | {a.lap_time_seconds}s")

if __name__ == "__main__":
    main()
