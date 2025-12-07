
from speedhive_tools import Speedhive

def main():
    sh = Speedhive()
    events = sh.events(count=5, offset=0)
    if not events:
        print("No events")
        return

    event_id = events[0]["id"]  # your earlier print shows 'id' exists
    print("Using event_id:", event_id)

    data = sh.event_sessions(event_id)
    print("event_sessions type:", type(data))

    # Depending on shape, print some session IDs
    if isinstance(data, dict):
        # some specs return {"sessions": [...]} or grouped structure
        sessions = data.get("sessions") or data.get("groups") or data
        print("Keys:", list(data.keys())[:10])
        if isinstance(sessions, list) and sessions:
            print("Sample session:", sessions[0])
            print("Sample session id:", sessions[0].get("id"))

if __name__ == "__main__":
    main()
