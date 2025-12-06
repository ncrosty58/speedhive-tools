
# get_records_example.py
# Simple example: show full "New Track Record" announcements, let the client
# do all parsing/cleaning, and export normalized records.
#
# No CLI args: just `python get_records_example.py`

from pathlib import Path
from speedhive_tools.client import SpeedHiveClient

def main():
    client = SpeedHiveClient()

    # Default org (your README uses Waterford Hills: 30476).
    # Change this constant if you want to test other orgs.
    ORGANIZATION_ID = 30476

    # --- Show all announcements text (full message) for visibility ---
    # rely on client to gather events/sessions, and normalize text
    print("Collecting announcements...")
    ann_rows = client.get_all_session_announcements_for_org(ORGANIZATION_ID)

    printed = 0
    for row in ann_rows:
        # Ensure text is extracted by the client—see recommended `get_announcement_text()` below.
        text = getattr(client, "get_announcement_text", lambda r: r.get("text", ""))(row)
        if client.find_track_record_announcements(text):
            print("ANNOUNCEMENT:", text)  # <-- full text as requested
            printed += 1
    print(f"Printed {printed} track-record announcement(s).")

    # --- Parse & export records (all logic lives inside the client) ---
    # See recommended `get_track_records_from_org_announcements()` below.
    print("Parsing records via client...")
    if hasattr(client, "get_track_records_from_org_announcements"):
        records = client.get_track_records_from_org_announcements(ORGANIZATION_ID)
        # Export using existing helpers
        client.export_records_to_json(records, "records.json")
        client.export_records_to_csv(records, "records.csv")
        print(f"Wrote {len(records)} record(s) to records.json and records.csv")
    else:
        # If you haven't added the method yet, make it clear.
        Path("records.json").write_text('{"records": []}', encoding="utf-8")
        print("Client method `get_track_records_from_org_announcements()` not found. "
              "Please add it (see recommendations). Wrote empty records.json.")

if __name__ == "__main__":
    main()
