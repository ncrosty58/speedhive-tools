
# examples/basic_events_raw.py
import json
from event_results_client import Client
from event_results_client.api.event_controller import get_event_list_1

def main():
    client = Client(base_url="http://api2.mylaps.com", timeout=20.0)

    resp = get_event_list_1.sync_detailed(client=client, count=5, offset=0)
    print("Status:", resp.status_code, "Content-Type:", resp.headers.get("Content-Type"))

    # Parse raw bytes → Python data
    data = json.loads(resp.content.decode("utf-8"))

    # Expect a list of events
    if isinstance(data, list):
        print(f"Events returned: {len(data)}")
        first = data[0] if data else None
        print("First event raw dict:", first)
    else:
        print("Unexpected payload shape:", type(data), data)

if __name__ == "__main__":
    main()
