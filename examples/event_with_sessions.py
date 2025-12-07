
# examples/event_with_sessions.py
from event_results_client import Client
from event_results_client.api.event_controller import get_event

EVENT_ID = 3095986

def main():
    client = Client(base_url="http://api2.mylaps.com", timeout=20.0)
    # Ask the event endpoint to include sessions
    resp = get_event.sync_detailed(client=client, id=EVENT_ID, sessions=True)
    print("Status:", resp.status_code)

    # Fallback to raw JSON if parsed is None
    import json
    data = (resp.parsed.model_dump() if getattr(resp.parsed, "model_dump", None)
            else json.loads(resp.content.decode("utf-8")))

    # Inspect shape
    print("Keys:", list(data.keys())[:20])
    # Sessions may be nested differently here; adjust flattening if needed
    sessions = []
    # Common patterns: data["sessions"] or data["sessionsAndGroups"] etc.
    if isinstance(data, dict):
        if "sessions" in data and isinstance(data["sessions"], list):
            sessions.extend(data["sessions"])
        # Sometimes nested under groups
        for g in data.get("groups", []) or []:
            sessions.extend(g.get("sessions", []) or [])

    print(f"Total sessions found via event?sessions=true: {len(sessions)}")
    for s in sessions[:10]:
        print(f" - id={s.get('id')} name={s.get('name')} type={s.get('type')} start={s.get('startTime')}")

if __name__ == "__main__":
    main()
