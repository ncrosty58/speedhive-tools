"""Example: stream all announcements for an organization to a file."""
from __future__ import annotations

import argparse
import json
from mylaps_client_wrapper import SpeedhiveClient


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example: stream announcements for an org")
    parser.add_argument("--org", type=int, required=True, help="Organization id")
    parser.add_argument("--output-file", required=True, help="File to stream announcements to (NDJSON format)")
    parser.add_argument("--token", help="API token (optional)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    
    event_iterator = client.iter_events(org_id=args.org)

    with open(args.output_file, "w") as f:
        ann_count = 0
        event_count = 0
        session_count = 0
        for event in event_iterator:
            event_count += 1
            event_id = event.get("id")
            if not event_id:
                continue
            
            try:
                sessions = client.get_sessions(event_id=event_id)
            except Exception:
                continue

            for session in sessions:
                session_count += 1
                session_id = session.get("id")
                if not session_id:
                    continue

                try:
                    announcements = client.get_announcements(session_id=session_id)
                except Exception:
                    continue
                
                for ann in announcements:
                    ann["event_name"] = event.get("name")
                    ann["session_name"] = session.get("name")
                    f.write(json.dumps(ann) + "\n")
                    ann_count += 1
            
            print(f"Events: {event_count} | Sessions: {session_count} | Announcements: {ann_count}", end="\r")

    print(f"\nFinished. Found {ann_count} announcements in {session_count} sessions for {event_count} events.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
