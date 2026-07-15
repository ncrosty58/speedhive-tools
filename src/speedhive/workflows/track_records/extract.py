"""Extract track-record announcements from SQLite database."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from speedhive.utils.lap_analysis import extract_iso_date, parse_track_record_text
from speedhive.storage import SpeedhiveStorage

def extract_records_from_storage(org: int, db_path: Path, classification: str | None = None) -> List[Dict[str, Any]]:
    storage = SpeedhiveStorage(db_path)
    if not storage.org_has_sessions(org):
        return []

    session_map = storage.load_session_payloads(org)
    event_map = storage.load_event_payloads(org)
    announcements_map = storage.load_announcements_payloads(org)

    records: List[Dict[str, Any]] = []
    wanted_class = classification.upper() if classification else None

    for session_id, announcements in announcements_map.items():
        session_raw = session_map.get(session_id, {})
        event_id = (
            session_raw.get("event_id")
            or session_raw.get("eventId")
            or (session_raw.get("event") or {}).get("id")
        )
        event_key = str(int(event_id)) if event_id not in (None, "") else None
        event_raw = event_map.get(event_key or "", {})
        event_name = (
            (event_raw or {}).get("name")
            or (session_raw.get("event") or {}).get("name")
            or session_raw.get("event_name")
            or session_raw.get("eventName")
        )
        session_name = session_raw.get("name") or session_raw.get("sessionName")

        for announcement in announcements:
            if not isinstance(announcement, dict):
                continue
            text = announcement.get("text") or announcement.get("message") or ""
            parsed = parse_track_record_text(text)
            if not parsed:
                continue
            class_name = (parsed.get("classification") or "Unknown").upper()
            if wanted_class and class_name != wanted_class:
                continue
            timestamp = (
                announcement.get("timestamp")
                or announcement.get("time")
                or extract_iso_date(session_raw)
                or extract_iso_date(event_raw)
            )
            records.append(
                {
                    "event_id": int(event_id) if event_id not in (None, "") else None,
                    "event_name": event_name,
                    "session_id": int(session_id),
                    "session_name": session_name,
                    "classification": parsed.get("classification"),
                    "lap_time": parsed.get("lap_time"),
                    "lap_time_seconds": parsed.get("lap_time_seconds"),
                    "driver": parsed.get("driver"),
                    "marque": parsed.get("marque"),
                    "timestamp": timestamp,
                    "text": text,
                }
            )

    records.sort(key=lambda row: ((row.get("classification") or "").upper(), row.get("lap_time_seconds") or float("inf")))
    return records


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

