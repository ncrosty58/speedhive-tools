
# examples/get_records_example.py
# Single-pass example:
# - Walk events/sessions ONCE to collect announcements.
# - Print sessionId + full announcement text while iterating.
# - Parse inline (client handles parsing/cleaning; attaches event date/track).
# - Export camelCase JSON at the end.
# - Log malformed entries (including "looks like record but missing prefix")
#   to 'malformed_announcements.txt' with sessionId + reason.

import time
import json
from datetime import datetime
from pathlib import Path

from speedhive_tools.client import SpeedHiveClient, SpeedHiveAPIError

def ts() -> str:
    """Timestamp for logs."""
    return datetime.now().strftime("%H:%M:%S")

def log_malformed(note_file: Path, session_id, text, reason):
    note = {
        "sessionId": session_id,
        "reason": reason,
        "announcementText": text,
        "timestamp": ts(),
    }
    with note_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(note, ensure_ascii=False))
        f.write("\n")

def main():
    client = SpeedHiveClient(timeout=30, retries=2, rate_delay=0.25)

    ORGANIZATION_ID = 30476  # Waterford Hills (example)
    malformed_path = Path("malformed_announcements.txt")
    if malformed_path.exists():
        malformed_path.unlink()  # start clean

    print(f"[{ts()}] Starting… base_url={client.base_url} org_id={ORGANIZATION_ID}")

    # ---- SINGLE PASS over events/sessions → announcements ----
    t_collect = time.monotonic()
    try:
        ann_rows = client.get_all_session_announcements_for_org(ORGANIZATION_ID)
    except SpeedHiveAPIError as e:
        print(f"[{ts()}] ERROR collecting announcements: {e}")
        return
    print(f"[{ts()}] Collection done in {time.monotonic() - t_collect:.2f}s (rows={len(ann_rows)})")

    parsed_records = []
    printed = 0

    for row in ann_rows:
        session_id = row.get("sessionId")
        text = client.get_announcement_text(row)

        # Always print the full text with sessionId
        print(f"[{ts()}] Session {session_id} ANNOUNCEMENT: {text}")

        # If the line looks like a record but lacks the prefix, log it as malformed and continue
        if not client.find_track_record_announcements(text) and client.looks_like_record_without_prefix(text):
            log_malformed(malformed_path, session_id, text, 'Missing "New Track/Class Record" prefix')
            continue

        # Only parse bona fide track/class record announcements
        if client.find_track_record_announcements(text):
            tr = client.parse_track_record_announcement(row)
            ok, reason = client.is_record_valid(tr)
            if not ok:
                log_malformed(malformed_path, session_id, text, f"Invalid record: {reason}")
                continue

            # Ensure date/track populated (parser uses row metadata, but double-check)
            if not getattr(tr, "date", None):
                setattr(tr, "date", row.get("eventDate"))
            if not getattr(tr, "track_name", None):
                setattr(tr, "track_name", row.get("trackName") or row.get("circuitName"))

            # Print a compact summary line including sessionId
            print(
                f"[{ts()}] Session {session_id} → "
                f"class: {tr.class_name} | time: {tr.lap_time} | "
                f"driver: {tr.driver_name} | marque: {tr.vehicle} | "
                f"date: {tr.date} | track: {tr.track_name}"
            )

            printed += 1
            parsed_records.append(tr)

    print(f"[{ts()}] Valid track/class records: {len(parsed_records)}.")
    if malformed_path.exists():
        print(f"[{ts()}] Malformed entries noted in {malformed_path.resolve()}")

    # ---- Export once (NO re-fetch / NO re-walk) ----
    t_out = time.monotonic()
    client.export_records_to_json_camel(parsed_records, "records.json")
    client.export_records_to_csv(parsed_records, "records.csv")
    print(f"[{ts()}] Wrote records.json & records.csv in {time.monotonic() - t_out:.2f}s")

    print(f"[{ts()}] Finished.")

if __name__ == "__main__":
    main()
