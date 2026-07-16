"""Extract track-record announcements from the Speedhive API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from speedhive.utils.lap_analysis import parse_track_record_text


def extract_records_from_api(
    client: Any,
    org_id: int,
    classification: Optional[str] = None,
    limit_events: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Recursively fetch events, sessions, and announcements from the Speedhive API,
    parsing track-record announcements programmatically.
    """
    records = []
    event_iter = client.iter_events(org_id=org_id)
    if limit_events is not None:
        from itertools import islice
        event_iter = islice(event_iter, limit_events)
    for event in event_iter:
        eid = event.get("id")
        ename = event.get("name")
        if not eid:
            continue
        try:
            sessions = client.get_sessions(event_id=eid)
        except Exception:
            continue
        for session in sessions:
            sid = session.get("id")
            sname = session.get("name")
            if not sid:
                continue
            try:
                announcements = client.get_announcements(session_id=sid)
            except Exception:
                continue
            for ann in announcements:
                text = ann.get("text") or ann.get("message") or ""
                ts = ann.get("timestamp") or ann.get("time")
                parsed = parse_track_record_text(text)
                if not parsed:
                    continue
                class_name = parsed.get("classification")
                if classification and class_name.upper() != classification.upper():
                    continue
                lap_seconds = parsed.get("lap_time_seconds")
                records.append({
                    "event_id": eid,
                    "event_name": ename,
                    "session_id": sid,
                    "session_name": sname,
                    "classification": class_name,
                    "lap_time": parsed.get("lap_time"),
                    "lap_time_seconds": lap_seconds,
                    "driver": parsed.get("driver"),
                    "marque": parsed.get("marque"),
                    "timestamp": ts,
                    "text": text,
                })
    records.sort(key=lambda r: ((r.get("classification") or "").upper(), r.get("lap_time_seconds") or float("inf")))
    return records


def extract_fastest_record_from_api(
    client: Any,
    org_id: int,
    classification: str,
    limit_events: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve the single fastest track record for a classification from the Speedhive API."""
    records = extract_records_from_api(client, org_id, classification, limit_events)
    return records[0] if records else None

