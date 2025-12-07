
from speedhive_tools import Speedhive

EVENT_ID = 3095986

def main():
    sh = Speedhive()  # defaults to http://api2.mylaps.com and 20s timeout

    data = sh.event_sessions(EVENT_ID)
    print("event_sessions type:", type(data))
    if isinstance(data, dict):
        print("Keys:", list(data.keys()))
        # Common shapes: {'sessions': [...], 'groups': [...]}
        groups = data.get("groups", [])
        sessions_flat = []
        for g in groups:
            # Each group may contain a 'sessions' list
            for s in g.get("sessions", []):
                sessions_flat.append(s)
        # Also check top-level sessions if present
        top_sessions = data.get("sessions", [])
        sessions_flat.extend(top_sessions)

        print(f"Total sessions found: {len(sessions_flat)}")
        for s in sessions_flat[:10]:
            print(f" - id={s.get('id')} name={s.get('name')} type={s.get('type')} start={s.get('startTime')}")
    else:
        print("Unexpected payload shape:", data)

if __name__ == "__main__":
    main()
