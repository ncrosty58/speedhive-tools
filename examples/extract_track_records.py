"""Extract track records from a streaming NDJSON lap file."""
import argparse
import csv
import json
import sys

def parse_lap_time(lap_time):
    """Convert lap time string or number to seconds."""
    if not lap_time:
        return None
    try:
        # If it's already a number
        if isinstance(lap_time, (int, float)):
            return float(lap_time)
            
        # If it's a string like "1:17.870"
        lap_time_str = str(lap_time).strip()
        parts = lap_time_str.split(":")
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        elif len(parts) == 3:
            # Handles "HH:MM:SS" just in case
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        else:
            return float(lap_time_str)
    except (ValueError, TypeError, IndexError):
        return None

def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract track records from NDJSON lap stream")
    parser.add_argument("--input-file", default="race-laps.ndjson", help="Input NDJSON file with laps")
    parser.add_argument("--output-csv", default="track_records_all_racelaps.csv", help="Output CSV file for track records")
    args = parser.parse_args(argv)

    laps = []
    print(f"Reading laps from {args.input_file}...")
    try:
        with open(args.input_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    lap = json.loads(line)
                    laps.append(lap)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print(f"Error: Could not find input file '{args.input_file}'")
        return 1

    print(f"Found {len(laps)} laps. Sorting chronologically...")
    
    # Sort laps chronologically
    # Date looks like '2025-09-27T10:00:00' or '2025-09-27'
    # Fallback to an empty string if date is missing to avoid TypeError
    laps.sort(key=lambda x: str(x.get("date") or ""))

    track_records = []
    class_best_times = {}

    print("Extracting track records...")
    for lap in laps:
        c_class = lap.get("class")
        # Ignore laps without a class
        if not c_class:
            continue
            
        c_class = str(c_class).strip()
        lap_time_raw = lap.get("lap_time")
        
        lap_time_seconds = parse_lap_time(lap_time_raw)
        
        # Ignore invalid lap times or a lap time of 0
        if lap_time_seconds is None or lap_time_seconds <= 0:
            continue

        current_best = class_best_times.get(c_class)
        
        # If this is the first valid lap for the class, or it's strictly faster than the current best
        if current_best is None or lap_time_seconds < current_best:
            class_best_times[c_class] = lap_time_seconds
            
            track_records.append({
                "date": lap.get("date"),
                "event_name": lap.get("event_name"),
                "laptime": lap_time_raw,
                "name": lap.get("competitor_name"),
                "class": c_class
            })

    print(f"Writing {len(track_records)} track records to {args.output_csv}...")
    with open(args.output_csv, "w", newline="") as f:
        # Standardize CSV column order as requested
        writer = csv.DictWriter(f, fieldnames=["date", "event_name", "laptime", "name", "class"])
        writer.writeheader()
        for record in track_records:
            writer.writerow(record)
            
    print("Done!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
