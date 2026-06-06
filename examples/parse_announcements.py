import json
import re
import csv
from datetime import datetime, timezone
import zoneinfo

def to_est(ts_str):
    try:
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        dt_est = dt.astimezone(zoneinfo.ZoneInfo('America/New_York'))
        return dt_est.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        return ts_str

def parse_text(text):
    text = text.strip()
    
    # Exclude non-records or generic statements
    if "under class record" in text.lower() or "not counted as new class record" in text.lower() or "qualifying time is under class record" in text.lower() or "no transponder" in text.lower() or "transponder" in text.lower():
        return None, None, None

    # New Track Record(1:11.923)for T1 by Danny Kellermeyer
    # New Track Record (1:19.448) for GTL by Mike Patterson.
    # New Class Record (1:15.013) for T4 by Matt Spicuzzi.
    m = re.search(r'New (?:Track|Class) Record\s*\(([\d:.]+)\)\s*for ([\w\-]+) by (.*)', text, re.IGNORECASE)
    if m:
        return m.group(2).strip(), m.group(3).strip('. '), m.group(1).strip()

    # Under Existing Track Record (1:14.446) for T1 by Vern Roberts.
    m = re.search(r'Under Existing Track Record \(([\d:.]+)\) for ([\w\-]+) by (.*)', text, re.IGNORECASE)
    if m:
        return m.group(2).strip(), m.group(3).strip('. '), m.group(1).strip()

    # New Track record for DSR  Jon Staudacher 1:08.093  old record was 1:09.332
    m = re.search(r'New Track record for ([\w\-]+)\s+(.*?)\s+([\d:.]+)\s+old', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()

    # New Lap Record For DSR John Staudacher 1:08.529
    m = re.search(r'New Lap Record For ([\w\-]+) (.*?)\s+([\d:.]+)$', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()

    # New Overall Track Record  Car #60 FA  J' Lewis Cooper,Jr.  1:02.423  81.692mph
    m = re.search(r'New Overall Track Record.*?\s+([\w\-]+)\s+(.*?)\s+([\d:.]+)\s+\d+\.\d+mph', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()

    # New Class Record  ITS  Car #27  Rob Huffmaster  1:15.067    68.16 mph
    m = re.search(r'New Class Record\s+([\w\-]+).*?Car #\d+\s+(.*?)\s+([\d:.]+)\s+\d+\.\d+\s*mph', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()

    # ITC Track Record by Tom O'Gorman  1:19.690
    m = re.search(r'^([\w\-]+)\s+Track Record by\s+(.*?)\s+([\d:.]+)$', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()

    # FS  Track Record  1:05.603 by Lew Cooper, Jr
    m = re.search(r'^([\w\-]+)\s+Track Record\s+([\d:.]+)\s+by\s+(.*?)$', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(3).strip(), m.group(2).strip()

    # New Lap Record: Spec Neon Car#55 Jonathan Rogers  1:19.434
    m = re.search(r'New Lap Record:\s+([\w\s]+?)\s+Car#\d+\s+(.*?)\s+([\d:.]+)$', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()

    # New Lap Record GT2:  1:10.935 by Gordon Leslie Car#12 Pontiac FIERO
    m = re.search(r'New Lap Record\s+([\w\-]+):\s+([\d:.]+)\s+by\s+(.*?)\s+Car#', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(3).strip(), m.group(2).strip()

    # Car#17 T4  establishes class record  11:17.513
    m = re.search(r'Car#\d+\s+([\w\-]+)\s+establishes class record\s+([\d:.]+)$', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), "", m.group(2).strip()
        
    # STU Lap Record  Car #2  Rob Huffmaster (no time)
    m = re.search(r'^([\w\-]+) Lap Record\s+Car #\d+\s+(.*)$', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip(), ""

    # 81 Seth Rowley new track record for SM 1:17:917 (or 1:17.917)
    m = re.search(r'^(?:\d+\s+)?(.*?) new track record for ([\w\-]+) ([\d:.]+)$', text, re.IGNORECASE)
    if m:
        time = m.group(3).strip()
        time = time.replace(':', '.', 1) if time.count(':') > 1 else time
        return m.group(2).strip(), m.group(1).strip(), time

    return None, None, None

unparsed = []
records = []

input_files = ["26970_announcements_03102026.ndjson", "30476_announcements_03102026.ndjson"]

for file_path in input_files:
    try:
        with open(file_path, "r") as f:
            for line in f:
                if not line.strip(): continue
                data = json.loads(line)
                text = data.get("text", "")
                if "record" in text.lower() and "no transponder signal" not in text.lower():
                    c_class, name, time = parse_text(text)
                    if c_class is not None:
                        # Basic cleaning
                        c_class = c_class.strip()
                        name = name.strip() if name else ""
                        time = time.strip() if time else ""
                        
                        records.append({
                            "date and time (EST)": to_est(data.get("timestamp", "")),
                            "lap time": time,
                            "competitor name": name,
                            "class": c_class,
                            "event name": data.get("event_name", ""),
                            "session name": data.get("session_name", "")
                        })
                    else:
                        if "under class record" not in text.lower() and "not counted as new class record" not in text.lower() and "qualifying time is under class record" not in text.lower():
                            unparsed.append(text)
    except FileNotFoundError:
        print(f"Warning: {file_path} not found.")

with open("track_records_announcements.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["date and time (EST)", "lap time", "competitor name", "class", "event name", "session name"])
    writer.writeheader()
    for r in records:
        writer.writerow(r)

print(f"Extracted {len(records)} records.")
if unparsed:
    print(f"Failed to parse {len(unparsed)} records:")
    for u in unparsed[:10]:
        print("  " + u)
