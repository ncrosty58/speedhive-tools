
from event_results_client import Client
from event_results_client.api.event_controller import get_event_list_1

def main():
    # Use the server from the spec (http); we can test https after we see headers.
    client = Client(base_url="http://api2.mylaps.com", timeout=20.0)

    resp = get_event_list_1.sync_detailed(client=client, count=5, offset=0)

    print("Status:", resp.status_code)
    print("Content-Type header:", resp.headers.get("Content-Type"))
    print("Raw bytes length:", len(resp.content or b""))
    print("First 500 bytes:\n", (resp.content or b"")[:500].decode("utf-8", errors="replace"))
    print("Parsed object:", type(resp.parsed), resp.parsed)

if __name__ == "__main__":
    main()
