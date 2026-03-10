"""Example: stream specific lap data for an organization to a file."""
from __future__ import annotations

import argparse
import json
import sys

from mylaps_client_wrapper import SpeedhiveClient

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Example: stream custom laps for an org")
    parser.add_argument("--org", type=int, required=True, help="Organization id")
    parser.add_argument("--output-file", required=True, help="File to stream laps to (NDJSON format)")
    parser.add_argument("--token", help="API token (optional)")
    args = parser.parse_args(argv)

    client = SpeedhiveClient(token=args.token)
    
    event_iterator = client.iter_events(org_id=args.org)

    print(f"Starting lap extraction for Organization ID: {args.org}")
    print(f"Output will be streamed to: {args.output_file}")

    with open(args.output_file, "w") as f:
        lap_count = 0
        event_count = 0
        session_count = 0
        for event in event_iterator:
            event_count += 1
            event_id = event.get("id")
            event_date = event.get("startDate")
            if not event_id:
                continue
            
            try:
                sessions = client.get_sessions(event_id=event_id)
            except Exception:
                continue

            for session in sessions:
                if session.get("type", "").lower() != "race":
                    continue

                session_count += 1
                session_id = session.get("id")
                session_date = session.get("startTime") or event_date
                if not session_id:
                    continue

                # Fetch classification to map positions to competitor name & class
                try:
                    results = client.get_results(session_id=session_id)
                    pos_to_competitor = {
                        r.get("position"): {
                            "name": r.get("name"),
                            "class": r.get("resultClass")
                        } for r in results if r.get("position") is not None
                    }
                except Exception:
                    pos_to_competitor = {}

                # Fetch laps
                try:
                    laps = client.get_laps(session_id=session_id, flatten=True)
                except Exception:
                    continue
                
                for lap in laps:
                    if not isinstance(lap, dict):
                        continue
                        
                    pos = lap.get("position")
                    comp_info = pos_to_competitor.get(pos, {})
                    
                    # Extract raw lap time (handle both string and dict formats just in case)
                    lap_time_raw = lap.get("lapTime")
                    if isinstance(lap_time_raw, dict):
                        lap_time_str = lap_time_raw.get("displayValue") or lap_time_raw.get("seconds")
                    else:
                        lap_time_str = lap_time_raw

                    custom_lap = {
                        "event_id": event_id,
                        "event_name": event.get("name"),
                        "session_id": session_id,
                        "session_name": session.get("name"),
                        "session_type": session.get("type"),
                        "date": session_date,
                        "competitor_name": comp_info.get("name"),
                        "lap_time": lap_time_str,
                        "speed": lap.get("speed"),
                        "class": comp_info.get("class")
                    }

                    f.write(json.dumps(custom_lap) + "\n")
                    lap_count += 1
            
            # Print progress without spamming newlines
            print(f"Events: {event_count} | Sessions: {session_count} | Laps: {lap_count}", end="\r", flush=True)

    print(f"\nFinished. Found {lap_count} laps in {session_count} sessions across {event_count} events.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
